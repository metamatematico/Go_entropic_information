"""
build_trajectory_dataset.py
============================
Matriz de trayectoria completa para los 19 patrones de apertura de Go.

Por cada patron de n piedras construye una matriz (n x m_features):
cada FILA = un turno k, cada COLUMNA = una feature de esa jugada.

Features por turno:
  Identidad        color, go_pos, line_from_edge, n_occ_neighbors
  Energia M1       dE_M1_total, dE_M1_stone, cum_E_M1
  Bonos M1 k->j   fraccion de cada valor {-2,-1,0,+1,+2} (solo vecinos ocupados)
  Bonos M1 j->k   idem en direccion inversa
  Asimetria M1     dE_M1_asym = sum(kj) - sum(jk)
  Entropia M1      cum_S_M1, dS_M1
  Energia AL       dE_AL_total, dE_AL_stone, cum_E_AL
  Bonos AL         fraccion {-1,0,+1} (simetrico, solo kj)
  Entropia AL      cum_S_AL, dS_AL

Salidas:
  results/trajectory_full.csv        -- una fila por (patron, turno)
  results/trajectory_summary.csv     -- features agregadas por patron
  results/trajectory_viz.png         -- heatmaps + curvas de trayectoria
"""

import os, sys, csv
from pathlib import Path
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.gridspec as gridspec
from matplotlib.colors import TwoSlopeNorm, Normalize

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from analysis_patterns import PATTERNS, BOARD_SIZE
from compare_per_bond  import (
    all_bond_energies_nuestro, all_bond_energies_alvarado,
    bond_shannon_entropy, H_nuestro, H_alvarado,
)
from src.go_entropy    import board_from_stones
from src.go_ising_classical import IsingGoConfig

RESULTS = os.path.join(str(Path(__file__).resolve().parents[2]), 'results')
os.makedirs(RESULTS, exist_ok=True)

COL_LETTERS = list('ABCDEFGHJ')
CONFIG      = IsingGoConfig()
S2S         = CONFIG.STONE_TO_SPIN   # {'B':-1,'W':+1,'.':0}
NEIGHBORS   = [(-1,0),(1,0),(0,-1),(0,1)]

CAT_OF = {
    '1b':'apertura','2b':'apertura','3b':'approach','4b':'invasion',
    '5b':'joseki','6b':'joseki','7b':'approach','8b':'approach',
    '9b':'joseki','10b':'enclosure','11b':'approach','12b':'joseki',
    '13b':'approach','14b':'joseki','15b':'joseki','16b':'approach',
    '17b':'joseki','18b':'joseki','19b':'joseki',
}
CAT_COLOR = {
    'apertura':'#2E6B4A','approach':'#1748A3','invasion':'#C0392B',
    'joseki':'#7C3AED','enclosure':'#D97706',
}

def to_go(row, col):
    return f'{COL_LETTERS[col]}{BOARD_SIZE - row}'

def spin(cell):
    return S2S.get(cell, 0.0)

def frac_val(bonds, val, eps=1e-5):
    if not bonds:
        return 0.0
    return sum(1 for b in bonds if abs(b - val) < eps) / len(bonds)


# ─────────────────────────────────────────────────────────────────────────────
# Calculo de features por turno
# ─────────────────────────────────────────────────────────────────────────────

def step_features(stones_before, new_stone, board_size=BOARD_SIZE):
    """
    Features del turno k: colocar new_stone dado stones_before en el tablero.

    dE_M1_total : cambio en energia total de todos los bonos del tablero.
    dE_M1_stone : contribucion exclusiva de los bonos piedra-piedra
                  (excluye bonos con celdas vacias para aislar interaccion directa).
    bond_M1_kj_* : valores de los bonos k->j con vecinos ocupados.
    bond_M1_jk_* : valores de los bonos j->k con vecinos ocupados.
    dE_M1_asym  : diferencia suma(kj) - suma(jk)  [0 si fuera simetrico].
    """
    color_str, row, col = new_stone
    s_k = S2S[color_str]

    board_bef = board_from_stones(board_size, stones_before)
    board_aft = board_from_stones(board_size, stones_before + [new_stone])

    # Energia total antes y despues
    bonds_bef_M1 = all_bond_energies_nuestro(board_bef)
    bonds_aft_M1 = all_bond_energies_nuestro(board_aft)
    bonds_bef_AL = all_bond_energies_alvarado(board_bef)
    bonds_aft_AL = all_bond_energies_alvarado(board_aft)

    dE_M1_total = float(bonds_aft_M1.sum() - bonds_bef_M1.sum())
    dE_AL_total = float(bonds_aft_AL.sum() - bonds_bef_AL.sum())
    cum_E_M1    = float(bonds_aft_M1.sum())
    cum_E_AL    = float(bonds_aft_AL.sum())

    # Bonos con vecinos ocupados (stone-stone)
    bonds_kj_M1, bonds_jk_M1 = [], []
    bonds_kj_AL, bonds_jk_AL = [], []
    occ_count = 0

    for dr, dc in NEIGHBORS:
        nr, nc = row + dr, col + dc
        if not (0 <= nr < board_size and 0 <= nc < board_size):
            continue
        s_j = spin(board_bef[nr, nc])
        if s_j == 0.0:
            continue
        occ_count += 1
        # M1: energia bono antes (celda vacia -> vecino) y despues (nueva piedra -> vecino)
        bonds_kj_M1.append(H_nuestro(s_k, s_j, d=1))
        bonds_jk_M1.append(H_nuestro(s_j, s_k, d=1))
        bonds_kj_AL.append(H_alvarado(s_k, s_j))
        bonds_jk_AL.append(H_alvarado(s_j, s_k))

    # dE_stone = nueva energia piedra-piedra menos la que habia antes (vacío->vecino)
    # Before: H(0, s_j) = 2*s_j  y  H(s_j, 0) = s_j  (suma = 3*s_j)
    # After:  H(s_k, s_j) + H(s_j, s_k)
    dE_M1_stone = 0.0
    dE_AL_stone = 0.0
    for i, (dr, dc) in enumerate(NEIGHBORS):
        nr, nc = row + dr, col + dc
        if not (0 <= nr < board_size and 0 <= nc < board_size):
            continue
        s_j = spin(board_bef[nr, nc])
        if s_j == 0.0:
            continue
        after_M1  = H_nuestro(s_k, s_j, d=1) + H_nuestro(s_j, s_k, d=1)
        before_M1 = H_nuestro(0.0, s_j, d=1) + H_nuestro(s_j, 0.0, d=1)
        dE_M1_stone += after_M1 - before_M1
        after_AL  = H_alvarado(s_k, s_j) + H_alvarado(s_j, s_k)
        before_AL = H_alvarado(0.0, s_j) + H_alvarado(s_j, 0.0)
        dE_AL_stone += after_AL - before_AL

    # Entropia de Shannon sobre distribucion de bonos (tablero completo)
    S_M1_bef = bond_shannon_entropy(bonds_bef_M1)
    S_M1_aft = bond_shannon_entropy(bonds_aft_M1)
    S_AL_bef = bond_shannon_entropy(bonds_bef_AL)
    S_AL_aft = bond_shannon_entropy(bonds_aft_AL)

    # Posicion en el tablero
    line_from_edge = min(row, col, board_size-1-row, board_size-1-col) + 1

    # Asimetria del bono M1 (diferencia forward vs backward)
    dE_M1_asym = (sum(bonds_kj_M1) - sum(bonds_jk_M1)) if bonds_kj_M1 else 0.0

    feat = {
        # Identidad de la jugada
        'color':             s_k,
        'go_pos':            to_go(row, col),
        'line_from_edge':    line_from_edge,
        'n_occ_neighbors':   occ_count,

        # M1 energia
        'dE_M1_total':       round(dE_M1_total, 6),
        'dE_M1_stone':       round(dE_M1_stone, 6),
        'cum_E_M1':          round(cum_E_M1, 6),

        # M1 bonos k->j con vecinos ocupados
        'bond_M1_kj_En2':    frac_val(bonds_kj_M1, -2),
        'bond_M1_kj_En1':    frac_val(bonds_kj_M1, -1),
        'bond_M1_kj_E0':     frac_val(bonds_kj_M1,  0),
        'bond_M1_kj_Ep1':    frac_val(bonds_kj_M1,  1),
        'bond_M1_kj_Ep2':    frac_val(bonds_kj_M1,  2),

        # M1 bonos j->k (direccion inversa)
        'bond_M1_jk_En2':    frac_val(bonds_jk_M1, -2),
        'bond_M1_jk_En1':    frac_val(bonds_jk_M1, -1),
        'bond_M1_jk_E0':     frac_val(bonds_jk_M1,  0),
        'bond_M1_jk_Ep1':    frac_val(bonds_jk_M1,  1),
        'bond_M1_jk_Ep2':    frac_val(bonds_jk_M1,  2),

        # M1 asimetria
        'dE_M1_asym':        round(dE_M1_asym, 6),

        # M1 entropia
        'cum_S_M1':          round(S_M1_aft, 6),
        'dS_M1':             round(S_M1_aft - S_M1_bef, 6),

        # AL energia
        'dE_AL_total':       round(dE_AL_total, 6),
        'dE_AL_stone':       round(dE_AL_stone, 6),
        'cum_E_AL':          round(cum_E_AL, 6),

        # AL bonos k->j (AL es simetrico, kj=jk)
        'bond_AL_kj_En1':    frac_val(bonds_kj_AL, -1),
        'bond_AL_kj_E0':     frac_val(bonds_kj_AL,  0),
        'bond_AL_kj_Ep1':    frac_val(bonds_kj_AL,  1),

        # AL entropia
        'cum_S_AL':          round(S_AL_aft, 6),
        'dS_AL':             round(S_AL_aft - S_AL_bef, 6),
    }
    return feat


# ─────────────────────────────────────────────────────────────────────────────
# Trayectoria completa de un patron
# ─────────────────────────────────────────────────────────────────────────────

def compute_trajectory(pid, stones, board_size=BOARD_SIZE):
    """
    Lista de dicts: uno por turno k=1..n_stones.
    Incluye columnas de identificacion: pattern_id, step, step_norm, n_total.
    """
    n = len(stones)
    rows = []
    for k in range(n):
        stones_before = stones[:k]
        new_stone     = stones[k]
        feat = step_features(stones_before, new_stone, board_size)
        feat['pattern_id']  = pid
        feat['step']        = k + 1
        feat['n_total']     = n
        feat['step_norm']   = round((k + 1) / n, 4)
        feat['is_last']     = int(k + 1 == n)
        rows.append(feat)
    return rows


# ─────────────────────────────────────────────────────────────────────────────
# CSV principal
# ─────────────────────────────────────────────────────────────────────────────

FIELD_ORDER = [
    'pattern_id','step','n_total','step_norm','is_last',
    'color','go_pos','line_from_edge','n_occ_neighbors',
    'dE_M1_total','dE_M1_stone','cum_E_M1',
    'bond_M1_kj_En2','bond_M1_kj_En1','bond_M1_kj_E0','bond_M1_kj_Ep1','bond_M1_kj_Ep2',
    'bond_M1_jk_En2','bond_M1_jk_En1','bond_M1_jk_E0','bond_M1_jk_Ep1','bond_M1_jk_Ep2',
    'dE_M1_asym','cum_S_M1','dS_M1',
    'dE_AL_total','dE_AL_stone','cum_E_AL',
    'bond_AL_kj_En1','bond_AL_kj_E0','bond_AL_kj_Ep1',
    'cum_S_AL','dS_AL',
]


def build_csv(all_trajs):
    path = os.path.join(RESULTS, 'trajectory_full.csv')
    with open(path, 'w', newline='', encoding='utf-8') as f:
        w = csv.DictWriter(f, fieldnames=FIELD_ORDER)
        w.writeheader()
        for traj in all_trajs:
            for row in traj:
                w.writerow({k: row.get(k, '') for k in FIELD_ORDER})
    print(f'CSV guardado: {path}')
    return path


# ─────────────────────────────────────────────────────────────────────────────
# CSV resumen (una fila por patron)
# ─────────────────────────────────────────────────────────────────────────────

def build_summary_csv(all_trajs, pattern_list):
    rows = []
    for (pid, desc, _), traj in zip(pattern_list, all_trajs):
        n = len(traj)
        dE_seq  = [r['dE_M1_stone'] for r in traj]
        cum_seq = [r['cum_E_M1']    for r in traj]
        asym_seq= [r['dE_M1_asym']  for r in traj]
        occ_seq = [r['n_occ_neighbors'] for r in traj]
        dS_seq  = [r['dS_M1']       for r in traj]

        rows.append({
            'id':               pid,
            'description':      desc,
            'category':         CAT_OF.get(pid, '?'),
            'n_steps':          n,
            # Estadisticas de la secuencia dE_M1_stone
            'dE_stone_mean':    round(np.mean(dE_seq), 4),
            'dE_stone_std':     round(np.std(dE_seq), 4),
            'dE_stone_first':   round(dE_seq[0], 4),
            'dE_stone_last':    round(dE_seq[-1], 4),
            'dE_stone_max':     round(max(dE_seq), 4),
            'dE_stone_min':     round(min(dE_seq), 4),
            'dE_stone_range':   round(max(dE_seq) - min(dE_seq), 4),
            # Monotonicidad: fraccion de pasos donde dE crece
            'dE_monotone_inc':  round(sum(1 for i in range(1,n) if dE_seq[i] > dE_seq[i-1]) / max(n-1,1), 4),
            # Energia final acumulada
            'cum_E_M1_final':   round(cum_seq[-1], 4),
            # Asimetria media de bonos M1
            'asym_M1_mean':     round(np.mean(asym_seq), 4),
            # Vecinos ocupados promedio por turno
            'occ_neighbors_mean': round(np.mean(occ_seq), 4),
            # Cambio de entropia medio
            'dS_M1_mean':       round(np.mean(dS_seq), 4),
            'dS_M1_total':      round(sum(dS_seq), 4),
        })
    path = os.path.join(RESULTS, 'trajectory_summary.csv')
    fields = list(rows[0].keys())
    with open(path, 'w', newline='', encoding='utf-8') as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        w.writerows(rows)
    print(f'Resumen guardado: {path}')
    return rows


# ─────────────────────────────────────────────────────────────────────────────
# Visualizacion
# ─────────────────────────────────────────────────────────────────────────────

BG   = '#F5F0E8'
MAX_STEPS = max(len(s) for _, _, s in PATTERNS)   # = 7

def build_viz(all_trajs, pattern_list, summary_rows):
    fig = plt.figure(figsize=(22, 18), facecolor=BG)
    fig.suptitle(
        'Matriz de Trayectoria de Energia — Patrones de Apertura de Go\n'
        'Modelo M1 (Sesma & Jimenez 2025)  ·  Extraccion turno a turno',
        fontsize=13, fontweight='bold', y=0.985, color='#1a1a1a',
    )

    outer = gridspec.GridSpec(2, 2,
                              hspace=0.38, wspace=0.32,
                              left=0.07, right=0.97,
                              top=0.95, bottom=0.05)

    # ── Panel A: Heatmap dE_M1_stone (patron x turno) ──────────────────────
    ax_A = fig.add_subplot(outer[0, 0])
    _heatmap_dE(ax_A, all_trajs, pattern_list,
                key='dE_M1_stone',
                title='A  |  ΔE_stone por turno  (M1, solo bonos piedra-piedra)')

    # ── Panel B: Curvas cum_E_M1 por patron ────────────────────────────────
    ax_B = fig.add_subplot(outer[0, 1])
    _curves_cum_E(ax_B, all_trajs, pattern_list,
                  key='cum_E_M1',
                  title='B  |  Energía acumulada  cum_E_M1  vs  turno')

    # ── Panel C: Heatmap asimetria M1 ──────────────────────────────────────
    ax_C = fig.add_subplot(outer[1, 0])
    _heatmap_dE(ax_C, all_trajs, pattern_list,
                key='dE_M1_asym',
                title='C  |  Asimetría M1 por turno  ( sum(k→j) − sum(j→k) )',
                vabs=2.0)

    # ── Panel D: Curvas entropia Shannon cum_S_M1 ──────────────────────────
    ax_D = fig.add_subplot(outer[1, 1])
    _curves_cum_E(ax_D, all_trajs, pattern_list,
                  key='cum_S_M1',
                  title='D  |  Entropía Shannon acumulada  cum_S_M1  vs  turno',
                  ylabel='S_Shannon (nats)')

    out = os.path.join(RESULTS, 'trajectory_viz.png')
    plt.savefig(out, dpi=150, bbox_inches='tight', facecolor=BG)
    print(f'Imagen guardada: {out}')
    plt.close(fig)


def _heatmap_dE(ax, all_trajs, pattern_list, key, title, vabs=None):
    n_pat = len(pattern_list)
    mat   = np.full((n_pat, MAX_STEPS), np.nan)
    for i, traj in enumerate(all_trajs):
        for row in traj:
            mat[i, row['step'] - 1] = row[key]

    if vabs is None:
        absmax = np.nanmax(np.abs(mat))
        vabs   = absmax if absmax > 0 else 1.0

    norm = TwoSlopeNorm(vmin=-vabs, vcenter=0, vmax=vabs)
    im = ax.imshow(mat, aspect='auto', cmap='RdBu_r', norm=norm,
                   interpolation='nearest')

    ax.set_xticks(range(MAX_STEPS))
    ax.set_xticklabels([f't{k+1}' for k in range(MAX_STEPS)], fontsize=8)
    ax.set_yticks(range(n_pat))
    labels = [f'{pid}' for pid, _, _ in pattern_list]
    ax.set_yticklabels(labels, fontsize=7.5)

    # Color de etiquetas por categoria
    for tick, (pid, _, _) in zip(ax.get_yticklabels(), pattern_list):
        cat = CAT_OF.get(pid, 'joseki')
        tick.set_color(CAT_COLOR.get(cat, '#333'))

    # Anotar valores en celdas no-NaN
    for i in range(n_pat):
        for j in range(MAX_STEPS):
            v = mat[i, j]
            if not np.isnan(v):
                ax.text(j, i, f'{v:.1f}', ha='center', va='center',
                        fontsize=6.5, color='#111' if abs(v) < vabs*0.6 else '#fff',
                        fontweight='bold')

    # Contorno de celdas NaN (pasos que no existen)
    for i in range(n_pat):
        for j in range(MAX_STEPS):
            if np.isnan(mat[i, j]):
                ax.add_patch(plt.Rectangle((j-0.5, i-0.5), 1, 1,
                                           fc='#CCCCCC', ec='none', zorder=0))

    plt.colorbar(im, ax=ax, shrink=0.6, pad=0.02, label=key)
    ax.set_title(title, fontsize=9, fontweight='bold', pad=6, color='#1a1a1a')
    ax.set_xlabel('Turno k', fontsize=8)
    ax.set_ylabel('Patron', fontsize=8)

    # Leyenda categorias
    for cat, col in CAT_COLOR.items():
        ax.plot([], [], 'o', color=col, ms=5, label=cat)
    ax.legend(loc='lower right', fontsize=6, framealpha=0.8)


def _curves_cum_E(ax, all_trajs, pattern_list, key, title, ylabel=None):
    ax.set_facecolor('#F0ECE2')
    ax.set_title(title, fontsize=9, fontweight='bold', pad=6, color='#1a1a1a')
    ax.set_xlabel('Turno k', fontsize=8)
    ax.set_ylabel(ylabel or key, fontsize=8)
    ax.axhline(0, color='#AAA', lw=0.8, ls='--', zorder=0)

    for (pid, desc, _), traj in zip(pattern_list, all_trajs):
        cat = CAT_OF.get(pid, 'joseki')
        col = CAT_COLOR.get(cat, '#888')
        steps = [r['step'] for r in traj]
        vals  = [r[key]    for r in traj]
        ax.plot(steps, vals, 'o-', color=col, lw=1.4, ms=4, alpha=0.8)
        # Etiqueta al final de cada curva
        ax.text(steps[-1] + 0.05, vals[-1], pid,
                fontsize=5.5, color=col, va='center', fontweight='bold')

    ax.set_xticks(range(1, MAX_STEPS + 1))
    ax.tick_params(labelsize=8)
    ax.grid(axis='y', alpha=0.3)

    for cat, col in CAT_COLOR.items():
        ax.plot([], [], '-o', color=col, ms=4, lw=1.4, label=cat)
    ax.legend(loc='upper left', fontsize=6, framealpha=0.85)


# ─────────────────────────────────────────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────────────────────────────────────────

def main():
    print('\n' + '='*62)
    print('  TRAYECTORIA COMPLETA — 19 PATRONES DE APERTURA DE GO')
    print('='*62)

    all_trajs = []
    for pid, desc, stones in PATTERNS:
        traj = compute_trajectory(pid, stones)
        all_trajs.append(traj)

        print(f'\n  {pid}  ({len(stones)} jugadas)  —  {desc}')
        hdr = f"  {'k':>2}  {'pos':>4}  {'col':>4}  {'occ':>4}  "
        hdr += f"{'dE_tot':>8}  {'dE_stone':>9}  {'cum_E':>7}  {'dS_M1':>7}"
        print(hdr)
        for r in traj:
            col_s = 'B' if r['color'] < 0 else 'W'
            print(
                f"  {r['step']:>2}  {r['go_pos']:>4}  {col_s:>4}  "
                f"{r['n_occ_neighbors']:>4}  "
                f"{r['dE_M1_total']:>8.2f}  {r['dE_M1_stone']:>9.2f}  "
                f"{r['cum_E_M1']:>7.2f}  {r['dS_M1']:>7.4f}"
            )

    build_csv(all_trajs)
    summary = build_summary_csv(all_trajs, PATTERNS)
    build_viz(all_trajs, PATTERNS, summary)

    print('\n' + '='*62)
    print('  RESUMEN DE TRAYECTORIAS')
    print('='*62)
    print(f"  {'id':<5} {'cat':<10} {'n':>2}  {'dE_mean':>8}  "
          f"{'dE_range':>9}  {'cum_E_fin':>10}  {'asym_mean':>10}")
    for r in summary:
        print(f"  {r['id']:<5} {r['category']:<10} {r['n_steps']:>2}  "
              f"{r['dE_stone_mean']:>8.2f}  {r['dE_stone_range']:>9.2f}  "
              f"{r['cum_E_M1_final']:>10.2f}  {r['asym_M1_mean']:>10.4f}")

    print('\nListo.')


if __name__ == '__main__':
    main()
