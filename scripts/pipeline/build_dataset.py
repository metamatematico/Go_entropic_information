"""
build_dataset.py
================
Dataset de features para los 19 patrones de apertura de Go.

Computa TODAS las métricas obtenidas en el análisis y las organiza en
7 categorías para entrenamiento de red neuronal.

Categorías
----------
  CAT1_BOARD       — geometría del tablero (modelo-independiente)
  CAT2_M1_ENERGY   — distribución de energías de bono bajo M1
  CAT3_M1_ENTROPY  — entropías: Shannon, Gibbs, Boltzmann (lnW), H_hist, T_eff
  CAT4_AL_ENERGY   — distribución de energías de bono bajo Alvarado
  CAT5_AL_ENTROPY  — entropías bajo Alvarado
  CAT6_MAP_M1      — estadísticas espaciales del mapa de energía M1
  CAT7_COMPARE     — comparativas y ratios entre modelos

Salidas
-------
  results/dataset_features.csv       — tabla principal (1 fila/patrón, todas las features)
  results/dataset_board_flat.csv     — tablero aplanado: 81 celdas B/W/vacío como ints
  results/dataset_metadata.json      — descripción, categoría y tipo de cada feature
  results/dataset_summary.txt        — estadísticas descriptivas y correlaciones clave
"""

import os, sys, json
from pathlib import Path
import numpy as np
import pandas as pd
from scipy import stats as scipy_stats
from math import lgamma

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from src.go_entropy       import GoEntropyAnalyzer, board_from_stones
from compare_per_bond     import (
    all_bond_energies_nuestro, all_bond_energies_alvarado,
    bond_shannon_entropy, bond_boltzmann_entropy,
    bond_boltzmann_lnW, bond_histogram_entropy, bond_T_eff,
)
from analysis_patterns    import PATTERNS, BOARD_SIZE

RESULTS = os.path.join(str(Path(__file__).resolve().parents[2]), 'results')
os.makedirs(RESULTS, exist_ok=True)

T_CAP    = 50.0   # cap para T_eff = inf → 50 (señal de "desorden total")
EPS      = 1e-12  # evitar divisiones por cero


# ═══════════════════════════════════════════════════════════════════════════════
# UTILIDADES
# ═══════════════════════════════════════════════════════════════════════════════

def safe_T(T):
    """T_eff infinita → T_CAP."""
    return T_CAP if (not np.isfinite(T) or T > T_CAP) else float(T)


def safe_ratio(a, b, fill=0.0):
    return float(a / b) if abs(b) > EPS else fill


def bond_hist_fracs(bond_energies, values):
    """Fracción de bonos con cada valor de energía (sobre total N)."""
    N = len(bond_energies)
    if N == 0:
        return {v: 0.0 for v in values}
    rounded = np.round(bond_energies.astype(float), 6)
    return {v: float(np.sum(np.abs(rounded - v) < 1e-5)) / N for v in values}


def connected_components(board, color):
    """Número de componentes conexas (grupos) de un color."""
    visited = np.zeros(board.shape, dtype=bool)
    rows, cols = board.shape
    n_comp = 0

    def dfs(r, c):
        stack = [(r, c)]
        while stack:
            rr, cc = stack.pop()
            for dr, dc in [(-1,0),(1,0),(0,-1),(0,1)]:
                nr, nc = rr+dr, cc+dc
                if 0 <= nr < rows and 0 <= nc < cols:
                    if not visited[nr, nc] and board[nr, nc] == color:
                        visited[nr, nc] = True
                        stack.append((nr, nc))

    for r in range(rows):
        for c in range(cols):
            if board[r, c] == color and not visited[r, c]:
                visited[r, c] = True
                dfs(r, c)
                n_comp += 1
    return n_comp


def largest_group(board, color):
    """Tamaño del grupo conectado más grande de un color."""
    visited = np.zeros(board.shape, dtype=bool)
    rows, cols = board.shape
    max_size = 0

    def dfs_size(r, c):
        stack, size = [(r, c)], 0
        while stack:
            rr, cc = stack.pop()
            size += 1
            for dr, dc in [(-1,0),(1,0),(0,-1),(0,1)]:
                nr, nc = rr+dr, cc+dc
                if 0 <= nr < rows and 0 <= nc < cols:
                    if not visited[nr, nc] and board[nr, nc] == color:
                        visited[nr, nc] = True
                        stack.append((nr, nc))
        return size

    for r in range(rows):
        for c in range(cols):
            if board[r, c] == color and not visited[r, c]:
                visited[r, c] = True
                max_size = max(max_size, dfs_size(r, c))
    return max_size


def min_dist_BW(board):
    """Distancia Manhattan mínima entre cualquier piedra B y cualquier piedra W."""
    B_pos = [(r, c) for r in range(board.shape[0])
             for c in range(board.shape[1]) if board[r, c] == 'B']
    W_pos = [(r, c) for r in range(board.shape[0])
             for c in range(board.shape[1]) if board[r, c] == 'W']
    if not B_pos or not W_pos:
        return -1.0   # no hay ambos colores
    return float(min(abs(br-wr) + abs(bc-wc)
                     for br, bc in B_pos for wr, wc in W_pos))


def spatial_spread(positions):
    """Std de posiciones (r,c) de un conjunto de piedras."""
    if len(positions) < 2:
        return 0.0
    pos = np.array(positions, dtype=float)
    return float(np.std(pos))


def center_of_mass(positions, board_size):
    """Centro de masa normalizado [0,1] de un conjunto de posiciones."""
    if not positions:
        return -1.0, -1.0   # sin piedras
    pos = np.array(positions, dtype=float)
    return (float(np.mean(pos[:, 0])) / board_size,
            float(np.mean(pos[:, 1])) / board_size)


# ═══════════════════════════════════════════════════════════════════════════════
# EXTRACCIÓN DE FEATURES POR PATRÓN
# ═══════════════════════════════════════════════════════════════════════════════

def extract_features(pid, desc, stones, board_size=BOARD_SIZE):
    """Extrae todas las features de un patrón. Retorna dict {nombre: valor}."""
    board   = board_from_stones(board_size, stones)
    N_cells = board_size * board_size
    feat    = {}

    # ──────────────────────────────────────────────────────────
    # METADATA (no son features numéricas, van al CSV como info)
    # ──────────────────────────────────────────────────────────
    feat['id']   = pid
    feat['desc'] = desc

    # ──────────────────────────────────────────────────────────
    # CAT1_BOARD  — geometría del tablero
    # ──────────────────────────────────────────────────────────
    B_pos = [(r, c) for r in range(board_size)
             for c in range(board_size) if board[r, c] == 'B']
    W_pos = [(r, c) for r in range(board_size)
             for c in range(board_size) if board[r, c] == 'W']
    n_B = len(B_pos)
    n_W = len(W_pos)
    n_S = n_B + n_W
    n_E = N_cells - n_S

    feat['board_n_stones']   = n_S
    feat['board_n_black']    = n_B
    feat['board_n_white']    = n_W
    feat['board_n_empty']    = n_E
    feat['board_density']    = n_S / N_cells
    feat['board_balance']    = safe_ratio(n_B - n_W, n_S)   # +1=solo B, -1=solo W

    # Posición espacial (líneas de tablero real)
    # En un 9x9 de análisis: filas 0-2 = líneas 1-3 (territorio); 3+ = influencia
    feat['board_n_territory_line'] = sum(1 for r, c in B_pos + W_pos if r <= 2 or c <= 2)
    feat['board_n_influence_line'] = sum(1 for r, c in B_pos + W_pos if r >= 3 and c >= 3)
    feat['board_n_corner_3x3']     = sum(1 for r, c in B_pos + W_pos if r <= 2 and c <= 2)

    feat['board_n_clusters_B']     = connected_components(board, 'B')
    feat['board_n_clusters_W']     = connected_components(board, 'W')
    feat['board_largest_group']    = max(largest_group(board, 'B'),
                                         largest_group(board, 'W'))
    feat['board_spread_B']         = spatial_spread(B_pos)
    feat['board_spread_W']         = spatial_spread(W_pos)
    feat['board_min_dist_BW']      = min_dist_BW(board)

    cm_B_r, cm_B_c = center_of_mass(B_pos, board_size)
    cm_W_r, cm_W_c = center_of_mass(W_pos, board_size)
    feat['board_cm_B_r'] = cm_B_r   # -1 si no hay piedras negras
    feat['board_cm_B_c'] = cm_B_c
    feat['board_cm_W_r'] = cm_W_r
    feat['board_cm_W_c'] = cm_W_c

    # ──────────────────────────────────────────────────────────
    # Bonds: base para todas las categorías 2-5
    # ──────────────────────────────────────────────────────────
    bM1 = all_bond_energies_nuestro(board)
    bAL = all_bond_energies_alvarado(board)
    N   = len(bM1)   # = board_size^2 * 4 = 324

    # ──────────────────────────────────────────────────────────
    # CAT2_M1_ENERGY  — distribución de bonos bajo M1
    # ──────────────────────────────────────────────────────────
    nz_M1 = bM1[np.abs(bM1) > EPS]
    feat['m1_E_total']          = float(bM1.sum())
    feat['m1_E_mean']           = float(bM1.mean())
    feat['m1_E_std']            = float(bM1.std())
    feat['m1_E_mean_active']    = float(nz_M1.mean()) if len(nz_M1) > 0 else 0.0
    feat['m1_E_std_active']     = float(nz_M1.std())  if len(nz_M1) > 1 else 0.0
    feat['m1_n_active_bonds']   = int(len(nz_M1))
    feat['m1_frac_active']      = len(nz_M1) / N

    fracs_M1 = bond_hist_fracs(bM1, [-2., -1., 0., 1., 2.])
    feat['m1_frac_En2'] = fracs_M1[-2.]
    feat['m1_frac_En1'] = fracs_M1[-1.]
    feat['m1_frac_E0']  = fracs_M1[ 0.]
    feat['m1_frac_Ep1'] = fracs_M1[ 1.]
    feat['m1_frac_Ep2'] = fracs_M1[ 2.]
    feat['m1_frac_Eneg']  = fracs_M1[-2.] + fracs_M1[-1.]   # total atracción
    feat['m1_frac_Epos']  = fracs_M1[ 1.] + fracs_M1[ 2.]   # total repulsión
    feat['m1_E_asym']     = feat['m1_frac_Epos'] - feat['m1_frac_Eneg']  # asimetría

    if len(nz_M1) >= 3:
        feat['m1_E_skewness'] = float(scipy_stats.skew(nz_M1))
        feat['m1_E_kurtosis'] = float(scipy_stats.kurtosis(nz_M1))
    else:
        feat['m1_E_skewness'] = 0.0
        feat['m1_E_kurtosis'] = 0.0

    # ──────────────────────────────────────────────────────────
    # CAT3_M1_ENTROPY  — entropías bajo M1
    # ──────────────────────────────────────────────────────────
    T_M1_raw = bond_T_eff(bM1)
    T_M1     = safe_T(T_M1_raw)
    lnW_M1   = bond_boltzmann_lnW(bM1)

    feat['m1_S_shannon']     = bond_shannon_entropy(bM1)
    feat['m1_S_gibbs']       = bond_boltzmann_entropy(bM1)
    feat['m1_S_boltzmann']   = lnW_M1
    feat['m1_H_hist']        = bond_histogram_entropy(bM1)
    feat['m1_T_eff']         = T_M1
    feat['m1_T_eff_is_inf']  = int(not np.isfinite(T_M1_raw))
    feat['m1_lnW_per_bond']  = lnW_M1 / N

    # ──────────────────────────────────────────────────────────
    # CAT4_AL_ENERGY  — distribución de bonos bajo Alvarado
    # ──────────────────────────────────────────────────────────
    nz_AL = bAL[np.abs(bAL) > EPS]
    feat['al_E_total']          = float(bAL.sum())
    feat['al_E_mean']           = float(bAL.mean())
    feat['al_E_std']            = float(bAL.std())
    feat['al_E_mean_active']    = float(nz_AL.mean()) if len(nz_AL) > 0 else 0.0
    feat['al_E_std_active']     = float(nz_AL.std())  if len(nz_AL) > 1 else 0.0
    feat['al_n_active_bonds']   = int(len(nz_AL))
    feat['al_frac_active']      = len(nz_AL) / N

    fracs_AL = bond_hist_fracs(bAL, [-1., 0., 1.])
    feat['al_frac_En1'] = fracs_AL[-1.]
    feat['al_frac_E0']  = fracs_AL[ 0.]
    feat['al_frac_Ep1'] = fracs_AL[ 1.]
    feat['al_frac_Eneg'] = fracs_AL[-1.]
    feat['al_frac_Epos'] = fracs_AL[ 1.]
    feat['al_E_asym']    = fracs_AL[1.] - fracs_AL[-1.]

    # ──────────────────────────────────────────────────────────
    # CAT5_AL_ENTROPY  — entropías bajo Alvarado
    # ──────────────────────────────────────────────────────────
    T_AL_raw = bond_T_eff(bAL)
    T_AL     = safe_T(T_AL_raw)
    lnW_AL   = bond_boltzmann_lnW(bAL)

    feat['al_S_shannon']    = bond_shannon_entropy(bAL)
    feat['al_S_gibbs']      = bond_boltzmann_entropy(bAL)
    feat['al_S_boltzmann']  = lnW_AL
    feat['al_H_hist']       = bond_histogram_entropy(bAL)
    feat['al_T_eff']        = T_AL
    feat['al_T_eff_is_inf'] = int(not np.isfinite(T_AL_raw))
    feat['al_lnW_per_bond'] = lnW_AL / N

    # ──────────────────────────────────────────────────────────
    # CAT6_MAP_M1  — mapa de energía espacial (GoEntropyAnalyzer)
    # ──────────────────────────────────────────────────────────
    analyzer = GoEntropyAnalyzer(manhattan_distance=1)
    result   = analyzer.analyze(board, T=1.0)
    emap     = result['energy_map'].astype(float)

    feat['map_E_total']      = float(result.get('total_energy', emap.sum()))
    feat['map_E_mean']       = float(emap.mean())
    feat['map_E_std']        = float(emap.std())
    feat['map_E_max']        = float(emap.max())
    feat['map_E_min']        = float(emap.min())
    feat['map_E_range']      = float(emap.max() - emap.min())
    feat['map_n_pos_cells']  = int((emap > EPS).sum())
    feat['map_n_neg_cells']  = int((emap < -EPS).sum())
    feat['map_n_zero_cells'] = int((np.abs(emap) <= EPS).sum())
    feat['map_frac_pos']     = feat['map_n_pos_cells'] / N_cells
    feat['map_frac_neg']     = feat['map_n_neg_cells'] / N_cells

    # Métricas del analyzer (S_shannon, S_boltzmann, T_eff del mapa)
    feat['map_S_shannon']   = float(result.get('S_shannon', 0.0))
    feat['map_S_boltzmann'] = float(result.get('S_boltzmann', 0.0))
    T_map_raw = result.get('T_eff', 0.0)
    feat['map_T_eff']       = safe_T(T_map_raw)
    feat['map_T_eff_is_inf']= int(not np.isfinite(T_map_raw) if T_map_raw is not None else True)

    # ──────────────────────────────────────────────────────────
    # CAT7_COMPARE  — ratios y diferencias entre modelos
    # ──────────────────────────────────────────────────────────
    feat['cmp_delta_S_shannon']   = feat['m1_S_shannon']   - feat['al_S_shannon']
    feat['cmp_delta_S_boltzmann'] = feat['m1_S_boltzmann'] - feat['al_S_boltzmann']
    feat['cmp_delta_S_gibbs']     = feat['m1_S_gibbs']     - feat['al_S_gibbs']
    feat['cmp_delta_H_hist']      = feat['m1_H_hist']      - feat['al_H_hist']
    feat['cmp_delta_E_total']     = feat['m1_E_total']      - feat['al_E_total']
    feat['cmp_delta_T_eff']       = feat['m1_T_eff']        - feat['al_T_eff']
    feat['cmp_delta_n_active']    = feat['m1_n_active_bonds'] - feat['al_n_active_bonds']

    feat['cmp_ratio_S_shannon']   = safe_ratio(feat['m1_S_shannon'],   feat['al_S_shannon'],   fill=9999.0)
    feat['cmp_ratio_S_boltzmann'] = safe_ratio(feat['m1_S_boltzmann'], feat['al_S_boltzmann'], fill=9999.0)
    feat['cmp_ratio_n_active']    = safe_ratio(feat['m1_n_active_bonds'], feat['al_n_active_bonds'], fill=9999.0)

    # Stirling accuracy: qué tan bien N·H_hist aproxima ln W
    feat['m1_stirling_residual'] = feat['m1_S_boltzmann'] - N * feat['m1_H_hist']
    feat['al_stirling_residual'] = feat['al_S_boltzmann'] - N * feat['al_H_hist']

    return feat


# ═══════════════════════════════════════════════════════════════════════════════
# TABLERO APLANADO (raw input para CNN / encoder)
# ═══════════════════════════════════════════════════════════════════════════════

def board_flat_row(pid, stones, board_size=BOARD_SIZE):
    """Tablero 9x9 aplanado: B=-1, vacío=0, W=+1. 81 valores + id."""
    board = board_from_stones(board_size, stones)
    enc   = {'B': -1, '.': 0, 'W': 1}
    flat  = [enc.get(board[r, c], 0)
             for r in range(board_size) for c in range(board_size)]
    cols  = {f'cell_{r}_{c}': enc.get(board[r, c], 0)
             for r in range(board_size) for c in range(board_size)}
    cols['id'] = pid
    return cols


# ═══════════════════════════════════════════════════════════════════════════════
# METADATA  —  descripción de cada feature para el JSON
# ═══════════════════════════════════════════════════════════════════════════════

FEATURE_META = {
    # CAT1_BOARD
    'board_n_stones':        ('CAT1_BOARD', 'int',   'Total de piedras en el tablero'),
    'board_n_black':         ('CAT1_BOARD', 'int',   'Piedras negras'),
    'board_n_white':         ('CAT1_BOARD', 'int',   'Piedras blancas'),
    'board_n_empty':         ('CAT1_BOARD', 'int',   'Celdas vacías'),
    'board_density':         ('CAT1_BOARD', 'float', 'Densidad de piedras n_stones/(9×9)'),
    'board_balance':         ('CAT1_BOARD', 'float', '(nB-nW)/n_stones: +1=solo B, -1=solo W, 0=equilibrado'),
    'board_n_territory_line':('CAT1_BOARD', 'int',   'Piedras en líneas 1-3 (territorio)'),
    'board_n_influence_line':('CAT1_BOARD', 'int',   'Piedras en líneas 4+ (influencia/moyo)'),
    'board_n_corner_3x3':    ('CAT1_BOARD', 'int',   'Piedras en cuadrado 3×3 de la esquina'),
    'board_n_clusters_B':    ('CAT1_BOARD', 'int',   'Grupos conectados de negras'),
    'board_n_clusters_W':    ('CAT1_BOARD', 'int',   'Grupos conectados de blancas'),
    'board_largest_group':   ('CAT1_BOARD', 'int',   'Tamaño del grupo conectado más grande'),
    'board_spread_B':        ('CAT1_BOARD', 'float', 'Dispersión espacial de negras (std de posiciones)'),
    'board_spread_W':        ('CAT1_BOARD', 'float', 'Dispersión espacial de blancas'),
    'board_min_dist_BW':     ('CAT1_BOARD', 'float', 'Distancia Manhattan mínima B↔W (-1 si un color falta)'),
    'board_cm_B_r':          ('CAT1_BOARD', 'float', 'Centro de masa de negras — fila normalizada [0,1]'),
    'board_cm_B_c':          ('CAT1_BOARD', 'float', 'Centro de masa de negras — columna normalizada [0,1]'),
    'board_cm_W_r':          ('CAT1_BOARD', 'float', 'Centro de masa de blancas — fila normalizada [0,1]'),
    'board_cm_W_c':          ('CAT1_BOARD', 'float', 'Centro de masa de blancas — columna normalizada [0,1]'),
    # CAT2_M1_ENERGY
    'm1_E_total':            ('CAT2_M1_ENERGY', 'float', 'Suma de todas las energías de bono bajo M1'),
    'm1_E_mean':             ('CAT2_M1_ENERGY', 'float', 'Energía media de todos los bonos bajo M1'),
    'm1_E_std':              ('CAT2_M1_ENERGY', 'float', 'Desviación estándar de energías de bono M1'),
    'm1_E_mean_active':      ('CAT2_M1_ENERGY', 'float', 'Energía media de bonos activos (E≠0) bajo M1'),
    'm1_E_std_active':       ('CAT2_M1_ENERGY', 'float', 'Std de bonos activos bajo M1'),
    'm1_n_active_bonds':     ('CAT2_M1_ENERGY', 'int',   'Número de bonos con E≠0 bajo M1'),
    'm1_frac_active':        ('CAT2_M1_ENERGY', 'float', 'Fracción de bonos activos bajo M1'),
    'm1_frac_En2':           ('CAT2_M1_ENERGY', 'float', 'Fracción de bonos con E=−2 (M1: ○●, ●○)'),
    'm1_frac_En1':           ('CAT2_M1_ENERGY', 'float', 'Fracción de bonos con E=−1 (M1: vacío→piedra)'),
    'm1_frac_E0':            ('CAT2_M1_ENERGY', 'float', 'Fracción de bonos con E=0 (M1: vacío-vacío, etc.)'),
    'm1_frac_Ep1':           ('CAT2_M1_ENERGY', 'float', 'Fracción de bonos con E=+1 (M1)'),
    'm1_frac_Ep2':           ('CAT2_M1_ENERGY', 'float', 'Fracción de bonos con E=+2 (M1: ●●, ○○)'),
    'm1_frac_Eneg':          ('CAT2_M1_ENERGY', 'float', 'Fracción de bonos negativos M1 (atracción)'),
    'm1_frac_Epos':          ('CAT2_M1_ENERGY', 'float', 'Fracción de bonos positivos M1 (repulsión)'),
    'm1_E_asym':             ('CAT2_M1_ENERGY', 'float', 'Asimetría repulsión−atracción (frac_pos − frac_neg)'),
    'm1_E_skewness':         ('CAT2_M1_ENERGY', 'float', 'Sesgo de la distribución de energías activas M1'),
    'm1_E_kurtosis':         ('CAT2_M1_ENERGY', 'float', 'Curtosis de la distribución de energías activas M1'),
    # CAT3_M1_ENTROPY
    'm1_S_shannon':          ('CAT3_M1_ENTROPY', 'float', 'S_Shannon ponderada por |E|  (bono-nivel, intensiva)'),
    'm1_S_gibbs':            ('CAT3_M1_ENTROPY', 'float', 'S_Gibbs = −Σ p_b ln p_b  con  p_b=e^{−E/T_eff}/Z'),
    'm1_S_boltzmann':        ('CAT3_M1_ENTROPY', 'float', 'S_B = ln W = ln(N!/∏nₖ!)  (Boltzmann 1877, extensiva)'),
    'm1_H_hist':             ('CAT3_M1_ENTROPY', 'float', 'H_hist = −Σ pₖ ln pₖ  pₖ=nₖ/N  (histograma frecuencias)'),
    'm1_T_eff':              ('CAT3_M1_ENTROPY', 'float', 'T_eff = σ²(E)/|⟨E⟩|  (cap. en 50; inf→50)'),
    'm1_T_eff_is_inf':       ('CAT3_M1_ENTROPY', 'bool',  '1 si T_eff es divergente (⟨E⟩≈0)'),
    'm1_lnW_per_bond':       ('CAT3_M1_ENTROPY', 'float', 'S_B / N_bonds  (Boltzmann intensiva ≈ H_hist por Stirling)'),
    # CAT4_AL_ENERGY
    'al_E_total':            ('CAT4_AL_ENERGY', 'float', 'Suma de energías de bono bajo Alvarado'),
    'al_E_mean':             ('CAT4_AL_ENERGY', 'float', 'Energía media de bonos Alvarado'),
    'al_E_std':              ('CAT4_AL_ENERGY', 'float', 'Std de energías de bono Alvarado'),
    'al_E_mean_active':      ('CAT4_AL_ENERGY', 'float', 'Energía media de bonos activos Alvarado'),
    'al_E_std_active':       ('CAT4_AL_ENERGY', 'float', 'Std de bonos activos Alvarado'),
    'al_n_active_bonds':     ('CAT4_AL_ENERGY', 'int',   'Número de bonos activos (E≠0) Alvarado'),
    'al_frac_active':        ('CAT4_AL_ENERGY', 'float', 'Fracción de bonos activos Alvarado'),
    'al_frac_En1':           ('CAT4_AL_ENERGY', 'float', 'Fracción de bonos E=−1 (Alvarado: B×W, W×B)'),
    'al_frac_E0':            ('CAT4_AL_ENERGY', 'float', 'Fracción de bonos E=0 (vacío o fuera de borde)'),
    'al_frac_Ep1':           ('CAT4_AL_ENERGY', 'float', 'Fracción de bonos E=+1 (Alvarado: B×B, W×W)'),
    'al_frac_Eneg':          ('CAT4_AL_ENERGY', 'float', 'Fracción bonos negativos Alvarado (interacción opuesta)'),
    'al_frac_Epos':          ('CAT4_AL_ENERGY', 'float', 'Fracción bonos positivos Alvarado (mismo color)'),
    'al_E_asym':             ('CAT4_AL_ENERGY', 'float', 'Asimetría Alvarado: frac_pos − frac_neg'),
    # CAT5_AL_ENTROPY
    'al_S_shannon':          ('CAT5_AL_ENTROPY', 'float', 'S_Shannon ponderada |E| bajo Alvarado'),
    'al_S_gibbs':            ('CAT5_AL_ENTROPY', 'float', 'S_Gibbs bajo Alvarado'),
    'al_S_boltzmann':        ('CAT5_AL_ENTROPY', 'float', 'S_B = ln W bajo Alvarado (0 si todos bonos iguales)'),
    'al_H_hist':             ('CAT5_AL_ENTROPY', 'float', 'H_hist bajo Alvarado'),
    'al_T_eff':              ('CAT5_AL_ENTROPY', 'float', 'T_eff bajo Alvarado (cap. en 50)'),
    'al_T_eff_is_inf':       ('CAT5_AL_ENTROPY', 'bool',  '1 si T_eff Alvarado es divergente'),
    'al_lnW_per_bond':       ('CAT5_AL_ENTROPY', 'float', 'S_B / N_bonds Alvarado'),
    # CAT6_MAP_M1
    'map_E_total':           ('CAT6_MAP_M1', 'float', 'Energía total del mapa de energía M1 (celda-nivel)'),
    'map_E_mean':            ('CAT6_MAP_M1', 'float', 'Energía media del mapa de energía M1'),
    'map_E_std':             ('CAT6_MAP_M1', 'float', 'Std del mapa de energía M1'),
    'map_E_max':             ('CAT6_MAP_M1', 'float', 'Celda más energética del mapa M1'),
    'map_E_min':             ('CAT6_MAP_M1', 'float', 'Celda menos energética del mapa M1'),
    'map_E_range':           ('CAT6_MAP_M1', 'float', 'Rango del mapa de energía M1'),
    'map_n_pos_cells':       ('CAT6_MAP_M1', 'int',   'Celdas con energía positiva en mapa M1'),
    'map_n_neg_cells':       ('CAT6_MAP_M1', 'int',   'Celdas con energía negativa en mapa M1'),
    'map_n_zero_cells':      ('CAT6_MAP_M1', 'int',   'Celdas con energía cero en mapa M1'),
    'map_frac_pos':          ('CAT6_MAP_M1', 'float', 'Fracción de celdas con energía positiva'),
    'map_frac_neg':          ('CAT6_MAP_M1', 'float', 'Fracción de celdas con energía negativa'),
    'map_S_shannon':         ('CAT6_MAP_M1', 'float', 'S_Shannon del mapa de energía M1 (celda-nivel)'),
    'map_S_boltzmann':       ('CAT6_MAP_M1', 'float', 'S_Boltzmann del mapa de energía M1'),
    'map_T_eff':             ('CAT6_MAP_M1', 'float', 'T_eff del mapa de energía M1'),
    'map_T_eff_is_inf':      ('CAT6_MAP_M1', 'bool',  '1 si T_eff mapa es divergente'),
    # CAT7_COMPARE
    'cmp_delta_S_shannon':   ('CAT7_COMPARE', 'float', 'ΔS_Shannon = S_sh_M1 − S_sh_AL (positivo: M1 más desordenado)'),
    'cmp_delta_S_boltzmann': ('CAT7_COMPARE', 'float', 'Δln W = lnW_M1 − lnW_AL'),
    'cmp_delta_S_gibbs':     ('CAT7_COMPARE', 'float', 'ΔS_Gibbs = S_Gibbs_M1 − S_Gibbs_AL'),
    'cmp_delta_H_hist':      ('CAT7_COMPARE', 'float', 'ΔH_hist = H_hist_M1 − H_hist_AL'),
    'cmp_delta_E_total':     ('CAT7_COMPARE', 'float', 'ΔE_total = E_tot_M1 − E_tot_AL'),
    'cmp_delta_T_eff':       ('CAT7_COMPARE', 'float', 'ΔT_eff = T_M1 − T_AL (ambos capados)'),
    'cmp_delta_n_active':    ('CAT7_COMPARE', 'float', 'Δn_activos = n_M1 − n_AL (M1 ve más interacciones)'),
    'cmp_ratio_S_shannon':   ('CAT7_COMPARE', 'float', 'S_sh_M1 / S_sh_AL (9999 si AL=0)'),
    'cmp_ratio_S_boltzmann': ('CAT7_COMPARE', 'float', 'lnW_M1 / lnW_AL (9999 si AL=0)'),
    'cmp_ratio_n_active':    ('CAT7_COMPARE', 'float', 'n_active_M1 / n_active_AL'),
    'm1_stirling_residual':  ('CAT7_COMPARE', 'float', 'lnW_M1 − N·H_hist_M1 (error de Stirling, ≤0)'),
    'al_stirling_residual':  ('CAT7_COMPARE', 'float', 'lnW_AL − N·H_hist_AL (error de Stirling, ≤0)'),
}


# ═══════════════════════════════════════════════════════════════════════════════
# MAIN
# ═══════════════════════════════════════════════════════════════════════════════

def main():
    print("\n" + "="*65)
    print("  DATASET DE FEATURES — 19 PATRONES DE APERTURA DE GO")
    print("="*65)

    # 1. Extraer features de todos los patrones
    rows      = []
    board_rows = []
    print("\nExtrayendo features...")
    for pid, desc, stones in PATTERNS:
        print(f"  {pid}: {desc[:45]}")
        feat = extract_features(pid, desc, stones)
        rows.append(feat)
        board_rows.append(board_flat_row(pid, stones))
    print(f"\n  OK: {len(rows)} patrones procesados")

    # 2. DataFrame principal
    df = pd.DataFrame(rows)

    # Ordenar columnas: id, desc, luego por categoría
    cat_order = ['CAT1_BOARD', 'CAT2_M1_ENERGY', 'CAT3_M1_ENTROPY',
                 'CAT4_AL_ENERGY', 'CAT5_AL_ENTROPY', 'CAT6_MAP_M1', 'CAT7_COMPARE']
    meta_cols  = ['id', 'desc']
    feat_cols  = [f for cat in cat_order
                  for f in FEATURE_META if f in df.columns
                  and FEATURE_META[f][0] == cat]
    df = df[meta_cols + feat_cols]

    # Añadir rankings por S_shannon (referencia)
    df.insert(2, 'rank_M1_S_shannon',
              df['m1_S_shannon'].rank(ascending=False).astype(int))
    df.insert(3, 'rank_AL_S_shannon',
              df['al_S_shannon'].rank(ascending=False, method='min').astype(int))
    df.insert(4, 'rank_M1_S_boltzmann',
              df['m1_S_boltzmann'].rank(ascending=False).astype(int))

    # 3. Guardar CSV principal
    csv_path = os.path.join(RESULTS, 'dataset_features.csv')
    df.to_csv(csv_path, index=False, float_format='%.6f')
    print(f"\n  CSV principal:  {csv_path}")
    print(f"  Shape: {df.shape[0]} patrones × {df.shape[1]} columnas")

    # 4. Tablero aplanado
    df_board = pd.DataFrame(board_rows)
    cols_board = ['id'] + [c for c in df_board.columns if c != 'id']
    df_board = df_board[cols_board]
    board_path = os.path.join(RESULTS, 'dataset_board_flat.csv')
    df_board.to_csv(board_path, index=False)
    print(f"  Tablero flat:   {board_path}  (81 celdas: B=-1, vacío=0, W=+1)")

    # 5. Metadata JSON
    meta = {}
    for fname, (cat, ftype, fdesc) in FEATURE_META.items():
        if fname in df.columns:
            col = df[fname]
            meta[fname] = {
                'category':    cat,
                'type':        ftype,
                'description': fdesc,
                'stats': {
                    'min':    round(float(col.min()), 6),
                    'max':    round(float(col.max()), 6),
                    'mean':   round(float(col.mean()), 6),
                    'std':    round(float(col.std()), 6),
                    'n_unique': int(col.nunique()),
                }
            }
    # Añadir rankings al metadata
    for rk in ['rank_M1_S_shannon', 'rank_AL_S_shannon', 'rank_M1_S_boltzmann']:
        meta[rk] = {
            'category': 'RANKING',
            'type': 'int',
            'description': f'Ranking de 1 (mayor) a 19 por {rk.replace("rank_","")}'
        }
    meta_path = os.path.join(RESULTS, 'dataset_metadata.json')
    with open(meta_path, 'w', encoding='utf-8') as f:
        json.dump(meta, f, indent=2, ensure_ascii=False)
    print(f"  Metadata JSON:  {meta_path}")

    # 6. Resumen en texto
    num_df = df.select_dtypes(include=[float, int]).drop(
        columns=['rank_M1_S_shannon', 'rank_AL_S_shannon', 'rank_M1_S_boltzmann'],
        errors='ignore')

    summary_path = os.path.join(RESULTS, 'dataset_summary.txt')
    with open(summary_path, 'w', encoding='utf-8') as f:
        f.write("DATASET DE FEATURES — 19 PATRONES DE APERTURA DE GO\n")
        f.write("="*65 + "\n\n")
        f.write(f"Patrones: {df.shape[0]}\n")
        f.write(f"Features numéricas: {num_df.shape[1]}\n")
        f.write(f"Columnas totales (incl. id, desc, rankings): {df.shape[1]}\n\n")

        for cat in cat_order:
            cols_cat = [f for f in feat_cols if f in FEATURE_META
                        and FEATURE_META[f][0] == cat]
            f.write(f"\n{'─'*65}\n{cat}  ({len(cols_cat)} features)\n{'─'*65}\n")
            f.write(f"  {'Feature':<28} {'min':>9} {'max':>9} {'mean':>9} {'std':>9}\n")
            for col in cols_cat:
                if col in num_df.columns:
                    s = num_df[col]
                    f.write(f"  {col:<28} {s.min():>9.3f} {s.max():>9.3f} "
                            f"{s.mean():>9.3f} {s.std():>9.3f}\n")

        # Tabla completa de patrones (features clave)
        f.write(f"\n\n{'='*65}\nTABLA COMPLETA — FEATURES PRINCIPALES\n{'='*65}\n")
        key_cols = ['id', 'board_n_stones', 'board_balance',
                    'm1_S_shannon', 'm1_S_boltzmann', 'm1_T_eff',
                    'al_S_shannon', 'al_S_boltzmann', 'al_T_eff',
                    'cmp_delta_S_shannon', 'cmp_ratio_S_boltzmann',
                    'rank_M1_S_shannon']
        sub = df[[c for c in key_cols if c in df.columns]]
        f.write(sub.to_string(index=False))

        # Correlaciones entre features de entropía
        f.write(f"\n\n{'='*65}\nMATRIZ DE CORRELACIÓN — ENTROPÍAS\n{'='*65}\n")
        ent_cols = ['m1_S_shannon', 'm1_S_gibbs', 'm1_S_boltzmann', 'm1_H_hist',
                    'al_S_shannon', 'al_S_gibbs', 'al_S_boltzmann',
                    'board_n_stones', 'm1_n_active_bonds', 'al_n_active_bonds']
        ent_df = df[[c for c in ent_cols if c in df.columns]]
        corr = ent_df.corr().round(3)
        f.write(corr.to_string())

    print(f"  Resumen TXT:    {summary_path}")

    # 7. Print resumen en consola
    print(f"\n{'='*65}")
    print(f"  RESUMEN DE FEATURES ({num_df.shape[1]} numéricas)")
    print(f"{'='*65}")
    counts = {}
    for f_name in feat_cols:
        if f_name in FEATURE_META:
            cat = FEATURE_META[f_name][0]
            counts[cat] = counts.get(cat, 0) + 1
    for cat in cat_order:
        print(f"  {cat:<20} {counts.get(cat, 0):>3} features")

    print(f"\n{'-'*65}")
    print(f"  Top 5 patrones por S_Boltzmann (M1):")
    top5 = df.nlargest(5, 'm1_S_boltzmann')[['id', 'desc', 'board_n_stones',
                                              'm1_S_boltzmann', 'm1_S_shannon',
                                              'rank_M1_S_shannon']]
    for _, r in top5.iterrows():
        print(f"    {r['id']:<4} n={int(r['board_n_stones'])}  "
              f"lnW={r['m1_S_boltzmann']:7.2f}  "
              f"S_sh={r['m1_S_shannon']:.3f}  "
              f"rk={r['rank_M1_S_shannon']}  {r['desc'][:35]}")

    print(f"\n  Correlacion S_Boltzmann M1 vs AL: "
          f"r={df['m1_S_boltzmann'].corr(df['al_S_boltzmann']):.3f}")
    print(f"  Correlacion S_Shannon   M1 vs AL: "
          f"r={df['m1_S_shannon'].corr(df['al_S_shannon']):.3f}")
    print(f"  Correlacion lnW vs S_Shannon M1:  "
          f"r={df['m1_S_boltzmann'].corr(df['m1_S_shannon']):.3f}")
    print(f"  Correlacion lnW vs n_stones  M1:  "
          f"r={df['m1_S_boltzmann'].corr(df['board_n_stones']):.3f}")
    print(f"\n{'='*65}")
    print(f"  Archivos generados en results/")
    print(f"{'='*65}\n")

    return df


if __name__ == '__main__':
    df = main()
