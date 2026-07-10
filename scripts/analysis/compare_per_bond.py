"""
compare_per_bond.py
===================
Comparacion correcta al nivel de BONO (par i -> j), no de celda.

Nuestro modelo:  energia del bono (i->j) = coef(d) * H(si, sj)
Alvarado:        energia del bono (i->j) = xi * xj    (UNA libertad a la vez)

La entropia se calcula sobre la distribucion de TODOS los bonos del tablero,
no sobre las celdas. Esto es la comparacion binaria correcta:
cada bono es UNA interaccion binaria independiente.

Diferencias clave que esto revela:
  - Nuestro modelo: H(si,sj) es ASIMETRICO  [H(-1,+1)=+1 pero H(+1,-1)=-1]
  - Alvarado: xi*xj es SIMETRICO            [(-1)(+1) = (+1)(-1) = -1]
  - Nuestro modelo: celdas vacias son ACTIVAS [H(0,xj) = 2xj != 0]
  - Alvarado: celdas vacias son INVISIBLES   [0 * xj = 0]

Salidas:
  results/bond_interaction_table.png   -- tabla de bonos para ambos modelos
  results/bond_entropy_compare.png     -- entropia por bono: 19 patrones
  results/bond_distribution.png        -- distribucion de bonos por patron
"""

import os, sys
from pathlib import Path
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.gridspec as gridspec
from matplotlib.patches import Circle, Rectangle, FancyArrow, FancyBboxPatch
from matplotlib.colors import TwoSlopeNorm
import matplotlib.cm as cm

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from src.go_ising_classical import IsingGoConfig, ClassicalIsingModel
from src.go_entropy         import board_from_stones
from analysis_patterns      import PATTERNS, BOARD_SIZE

RESULTS = os.path.join(str(Path(__file__).resolve().parents[2]), 'results', '02_enlaces_ising')
os.makedirs(RESULTS, exist_ok=True)

BG         = '#F9F6EE'
SPIN_VALS  = [-1, 0, +1]
SPIN_MINI  = {-1: '●', 0: '·', +1: '○'}
SPIN_NAME  = {-1: 'Negro', 0: 'Vacío', +1: 'Blanco'}
CONFIG     = IsingGoConfig()
MODEL_M1   = ClassicalIsingModel(manhattan_distance=1)

NORM  = TwoSlopeNorm(vmin=-2.5, vcenter=0, vmax=2.5)
CMAP  = cm.RdBu_r

def ec(h):
    r, g, b, _ = CMAP(NORM(np.clip(h, -2.5, 2.5)))
    return (r, g, b, 1.0)


# ══════════════════════════════════════════════════════════════════════════════
# ENERGIAS POR BONO
# ══════════════════════════════════════════════════════════════════════════════

def H_nuestro(s0, s1, d=1):
    """Energia de UN bono en nuestro modelo: coef(d) * H(s0, s1)."""
    coef = CONFIG.INTERACTION_COEFFS.get(d, 0.0)
    return coef * MODEL_M1._hamiltonian(s0, s1, MODEL_M1.params)

def H_alvarado(x0, x1):
    """Energia de UN bono en Alvarado: x0 * x1."""
    return float(x0 * x1)


def all_bond_energies_nuestro(board, manhattan_distance=1):
    """
    Coleccion de energias de todos los bonos dirigidos (i->j)
    del tablero bajo nuestro modelo con kernel Manhattan-d.
    Retorna array 1D.
    """
    positions = CONFIG.get_kernel_positions(manhattan_distance)
    N, M      = board.shape
    energies  = []
    for r in range(N):
        for c in range(M):
            si = CONFIG.STONE_TO_SPIN[board[r, c]]
            for idx, (dr, dc) in positions.items():
                if idx == 0:
                    continue
                nr, nc = r + dr, c + dc
                sj = (CONFIG.STONE_TO_SPIN[board[nr, nc]]
                      if 0 <= nr < N and 0 <= nc < M else 0.0)
                d  = abs(dr) + abs(dc)
                energies.append(H_nuestro(si, sj, d))
    return np.array(energies)


def all_bond_energies_alvarado(board):
    """
    Coleccion de energias de todos los bonos dirigidos (i->j)
    bajo Alvarado (solo N4, xi*xj).
    Retorna array 1D.
    """
    N, M     = board.shape
    energies = []
    for r in range(N):
        for c in range(M):
            xi = CONFIG.STONE_TO_SPIN[board[r, c]]
            for dr, dc in [(-1,0),(1,0),(0,-1),(0,1)]:
                nr, nc = r + dr, c + dc
                xj = (CONFIG.STONE_TO_SPIN[board[nr, nc]]
                      if 0 <= nr < N and 0 <= nc < M else 0.0)
                energies.append(H_alvarado(xi, xj))
    return np.array(energies)


def bond_shannon_entropy(bond_energies):
    """Entropia de Shannon sobre la distribucion de |energia de bono|."""
    flat  = np.abs(bond_energies)
    total = flat.sum()
    if total < 1e-12:
        return 0.0
    p = flat / total
    p = p[p > 1e-12]
    return float(-np.sum(p * np.log(p)))


def bond_T_eff(bond_energies):
    """
    Temperatura efectiva de la distribucion de bonos.
    T_eff = sigma^2(E) / |mean(E)|  (solo sobre bonos no nulos).
    Analogo de fluctuacion-disipacion: T_eff alto = posicion caliente.
    """
    nz = bond_energies[np.abs(bond_energies) > 1e-10]
    if len(nz) == 0:
        return 0.0
    mean_e = float(np.mean(nz))
    var_e  = float(np.var(nz))
    if abs(mean_e) < 1e-10:
        return float('inf')
    return var_e / abs(mean_e)


def bond_boltzmann_entropy(bond_energies, T=None):
    """
    Entropia de Boltzmann sobre la distribucion de energias de bono.

    p_i = exp(-E_i / T) / Z   con Z = sum_j exp(-E_j / T)
    S_B = -sum_i p_i ln(p_i)

    Si T is None, usa T_eff calculado de los mismos bonos.
    - T -> 0 : solo el bono de menor energia contribuye -> S_B ~ 0
    - T -> inf: todos los bonos equiprobables -> S_B -> ln(N)
    """
    if T is None:
        T = bond_T_eff(bond_energies)
    # Si T_eff es inf (mean ~ 0) usamos T grande -> distribucion plana
    T_safe = max(T if np.isfinite(T) else 50.0, 1e-10)
    flat = bond_energies - bond_energies.min()   # estabilidad numerica
    w = np.exp(-flat / T_safe)
    Z = w.sum()
    if Z < 1e-12:
        return 0.0
    p = w / Z
    p = p[p > 1e-12]
    return float(-np.sum(p * np.log(p)))


def bond_histogram_entropy(bond_energies):
    """
    Entropía de Shannon del histograma de frecuencias de energías de bono.
    p_k = n_k / N  (fracción de bonos con energía E_k)
    H = -Σ p_k ln p_k

    Esta es la entropía que aparece en la relación de Stirling:
        ln W / N  ≈  H_hist   para N grande.

    Distinta de bond_shannon_entropy (que usa pesos |E_i|/Σ|E_j|).
    """
    N = len(bond_energies)
    if N == 0:
        return 0.0
    rounded = np.round(bond_energies.astype(float), 8)
    unique, counts = np.unique(rounded, return_counts=True)
    p = counts.astype(float) / N
    p = p[p > 0]
    return float(-np.sum(p * np.log(p)))


def bond_boltzmann_lnW(bond_energies):
    """
    Entropía de Boltzmann termodinámica  S_B = ln W

    W = N! / (n_1! · n_2! · ... · n_k!)
    es el número de microestados compatibles con el macroestado definido
    por el histograma de energías de bono observado.

    Propiedad: S_B ≈ N · S_Shannon  (Stirling, N grande).
    Es extensiva: escala con el número total de bonos N.

    A diferencia de S_Gibbs (que construye p_b = e^{-E_b/T_eff}/Z),
    S_B solo cuenta combinaciones del histograma real sin asumir equilibrio
    térmico ni temperatura.
    """
    from math import lgamma
    N = len(bond_energies)
    if N == 0:
        return 0.0
    rounded = np.round(bond_energies.astype(float), 8)
    unique, counts = np.unique(rounded, return_counts=True)
    log_W = lgamma(N + 1) - float(sum(lgamma(int(c) + 1) for c in counts))
    return log_W


# ══════════════════════════════════════════════════════════════════════════════
# FIGURA 1 — Tabla de bonos comparada
# ══════════════════════════════════════════════════════════════════════════════

def _draw_bond_example(ax):
    """
    Panel explicativo: que es un BONO.
    Flechas i→j y j→i con ejemplos numericos, badges de modelo y contador.
    """
    ax.set_facecolor('#EEF3F8')
    for sp in ax.spines.values():
        sp.set_visible(False)
    ax.set_xticks([]); ax.set_yticks([])
    ax.set_xlim(0, 10); ax.set_ylim(0, 10)

    # ── Titulo ────────────────────────────────────────────────────────────
    ax.text(5.0, 9.75, 'QUE ES UN "BONO"  (bond)',
            ha='center', va='top', fontsize=11, fontweight='bold',
            color='#1a1a1a')

    # ── Definicion ───────────────────────────────────────────────────────
    ax.text(5.0, 9.1,
            'Un bono es la interaccion energetica entre DOS celdas vecinas '
            '(distancia Manhattan = 1).\n'
            'Por cada par de celdas adyacentes existen DOS bonos dirigidos: '
            'i→j  y  j→i.   '
            'Tablero 9x9:  81 celdas x 4 vecinos = 324 bonos dirigidos totales.',
            ha='center', va='top', fontsize=8.5, color='#333',
            linespacing=1.65, style='italic')

    # ── Diagrama de flechas ───────────────────────────────────────────────
    ax0, ax1 = 0.8, 6.0
    axm = (ax0 + ax1) / 2
    y_ij  = 7.2
    y_ji  = 3.5
    y_sep = (y_ij + y_ji) / 2

    # Flecha i→j
    ax.annotate('', xy=(ax1, y_ij), xytext=(ax0, y_ij),
                arrowprops=dict(arrowstyle='->', color='#1D4ED8',
                                lw=2.5, mutation_scale=18))
    ax.text(ax0 - 0.12, y_ij, 'i', ha='right', va='center',
            fontsize=12, fontweight='bold', color='#1D4ED8')
    ax.text(ax1 + 0.12, y_ij, 'j', ha='left', va='center',
            fontsize=12, fontweight='bold', color='#1D4ED8')
    ax.text(axm, y_ij + 0.55,
            'bono  i→j  =  H( s_i ,  s_j )',
            ha='center', va='bottom', fontsize=10,
            fontweight='bold', color='#1D4ED8')
    ax.text(axm, y_ij - 0.42,
            'ej. Negro→Blanco:  H(−1, +1) = −1 + 2(+1) − (−1)(+1)² − (−1)²(+1) = +1',
            ha='center', va='top', fontsize=7.8, color='#555', style='italic')

    # Separador
    ax.plot([ax0 - 0.2, ax1 + 0.2], [y_sep, y_sep],
            '--', color='#BBBBBB', lw=0.9)
    ax.text(axm, y_sep + 0.15,
            'M1:  i→j  ≠  j→i     (modelo asimetrico)',
            ha='center', va='bottom', fontsize=8.5,
            color='#7C3AED', style='italic', fontweight='bold')

    # Flecha j→i
    ax.annotate('', xy=(ax0, y_ji), xytext=(ax1, y_ji),
                arrowprops=dict(arrowstyle='->', color='#DC2626',
                                lw=2.5, mutation_scale=18))
    ax.text(ax0 - 0.12, y_ji, 'i', ha='right', va='center',
            fontsize=12, fontweight='bold', color='#DC2626')
    ax.text(ax1 + 0.12, y_ji, 'j', ha='left', va='center',
            fontsize=12, fontweight='bold', color='#DC2626')
    ax.text(axm, y_ji - 0.55,
            'bono  j→i  =  H( s_j ,  s_i )',
            ha='center', va='top', fontsize=10,
            fontweight='bold', color='#DC2626')
    ax.text(axm, y_ji + 0.42,
            'ej. Blanco→Negro:  H(+1, −1) = +1 + 2(−1) − (+1)(−1)² − (+1)²(−1) = −1',
            ha='center', va='bottom', fontsize=7.8, color='#555', style='italic')

    # ── Badge contador ────────────────────────────────────────────────────
    ax.text(8.5, 5.35,
            '9x9 tablero:\n81 celdas x 4 vecinos\n= 324 bonos dirigidos',
            ha='center', va='center', fontsize=9, color='#1a1a1a',
            bbox=dict(boxstyle='round,pad=0.55', fc='#FFFBE8',
                      ec='#D97706', lw=1.6),
            linespacing=1.9)

    # ── Cajas M1 vs Alvarado ──────────────────────────────────────────────
    cajas = [
        ('M1  impar cubico',
         'H = s_i + 2s_j − s_i·s_j² − s_i²·s_j',
         'grado 3,   asimetrico: i→j  ≠  j→i',
         '#1D4ED8', '#EFF6FF'),
        ('Alvarado  par',
         'H = x_i · x_j',
         'grado 2,   simetrico: i→j  =  j→i',
         '#D97706', '#FFFBEB'),
    ]
    y_b = 9.1
    for name, formula, nota, col, bg_col in cajas:
        ax.add_patch(FancyBboxPatch((6.9, y_b - 1.15), 2.95, 1.05,
                                    boxstyle='round,pad=0.08',
                                    fc=bg_col, ec=col, lw=1.5, zorder=2))
        ax.text(8.37, y_b - 0.22, name,
                ha='center', va='top', fontsize=9,
                fontweight='bold', color=col, zorder=3)
        ax.text(8.37, y_b - 0.56, formula,
                ha='center', va='top', fontsize=7.8,
                color='#333', style='italic', zorder=3)
        ax.text(8.37, y_b - 0.85, nota,
                ha='center', va='top', fontsize=7.5,
                color='#555', zorder=3)
        y_b -= 1.32


def plot_bond_table(out_path):
    # Layout: fila superior = panel explicativo, fila inferior = dos tablas
    fig = plt.figure(figsize=(16, 13), facecolor=BG)
    gs = gridspec.GridSpec(2, 2,
                           height_ratios=[0.52, 1.0],
                           hspace=0.08, wspace=0.06,
                           left=0.02, right=0.98,
                           top=0.96, bottom=0.03)

    ax_exp   = fig.add_subplot(gs[0, :])   # panel explicativo (ancho completo)
    ax_left  = fig.add_subplot(gs[1, 0])   # tabla M1
    ax_right = fig.add_subplot(gs[1, 1])   # tabla Alvarado

    fig.suptitle(
        'Energia de UN Bono  (interaccion binaria $i \\to j$)\n'
        'Comparacion correcta: cada bono es UNA libertad analizada independientemente',
        fontsize=12, fontweight='bold', y=0.985
    )

    # ── Panel explicativo ──────────────────────────────────────────────────
    _draw_bond_example(ax_exp)

    # ── Configuracion de las dos tablas ───────────────────────────────────
    configs = [
        (ax_left,
         'Nuestro modelo  M1',
         'Modelo impar cubico  (grado 3)',
         r'$H(s_0,s_1)=s_0+2s_1-s_0 s_1^2-s_0^2 s_1$',
         '[ASIMETRICO: bono A→B ≠ bono B→A]',
         '#1D4ED8',
         lambda s0, s1: H_nuestro(s0, s1, d=1)),
        (ax_right,
         'Alvarado  (Atomic-Go)',
         'Modelo par  (grado 2)',
         r'$H(x_i,x_j)=x_i \cdot x_j$',
         '[SIMETRICO: bono A→B = bono B→A]',
         '#D97706',
         lambda x0, x1: H_alvarado(x0, x1)),
    ]

    TIPOS = {
        (-1,-1):'Negro — Negro',   (-1,0):'Negro — Vacio',
        (-1,+1):'Negro — Blanco',  (0,-1):'Vacio — Negro',
        (0, 0): 'Vacio — Vacio',   (0,+1):'Vacio — Blanco',
        (+1,-1):'Blanco — Negro',  (+1,0):'Blanco — Vacio',
        (+1,+1):'Blanco — Blanco',
    }

    cx = [0.09, 0.22, 0.50, 0.75, 0.94]
    hdrs = ['$s_0$', '$s_1$', 'Par', 'Bono $i \\to j$', 'Bono $j \\to i$']

    def styled_val(h, size=11):
        if h > 0:    fc, bc = '#FEF2F2', '#DC2626'
        elif h < 0:  fc, bc = '#EFF6FF', '#1D4ED8'
        else:        fc, bc = '#F9FAFB', '#6B7280'
        return dict(fontsize=size, fontweight='bold', color=bc,
                    bbox=dict(boxstyle='round,pad=0.25',
                              fc=fc, ec=bc, lw=1.3))

    for ax, name, tipo_label, formula, simetria_label, col, func in configs:
        ax.set_facecolor(BG)
        for sp in ax.spines.values(): sp.set_visible(False)
        ax.set_xticks([]); ax.set_yticks([])

        # ── Encabezado de la tabla ─────────────────────────────────────────
        # Linea de separacion con el panel superior
        ax.plot([0.02, 0.98], [0.995, 0.995], '-', color='#CCCCCC',
                lw=1.5, transform=ax.transAxes)

        # Nombre del modelo (grande)
        ax.text(0.5, 0.975, name, ha='center', va='top',
                transform=ax.transAxes,
                fontsize=11, fontweight='bold', color='#1a1a1a')

        # Tag tipo de modelo (badge coloreado)
        ax.text(0.5, 0.942,
                tipo_label,
                ha='center', va='top', transform=ax.transAxes,
                fontsize=8.8, fontweight='bold', color=col,
                bbox=dict(boxstyle='round,pad=0.28',
                          fc=('#EFF6FF' if col == '#1D4ED8' else '#FFFBEB'),
                          ec=col, lw=1.2))

        # Formula
        ax.text(0.5, 0.905, formula, ha='center', va='top',
                transform=ax.transAxes, fontsize=8.5, color='#444',
                style='italic')

        # Etiqueta simetria
        ax.text(0.5, 0.870, simetria_label, ha='center', va='top',
                transform=ax.transAxes, fontsize=7.8,
                color='#7C3AED' if 'ASIMETRICO' in simetria_label else '#15803D',
                fontweight='bold')

        # ── Cabecera de columnas ───────────────────────────────────────────
        for h, x in zip(hdrs, cx):
            ax.text(x, 0.825, h, ha='center', va='top',
                    transform=ax.transAxes,
                    fontsize=9, fontweight='bold', color='#1a1a1a')
        ax.plot([0.02, 0.98], [0.796, 0.796], '-', color='#888',
                lw=0.8, transform=ax.transAxes)

        # ── Filas de la tabla ──────────────────────────────────────────────
        y = 0.753; dy = 0.081; row = 0
        for s0 in SPIN_VALS:
            for s1 in SPIN_VALS:
                h_ij = func(s0, s1)
                h_ji = func(s1, s0)
                asym = abs(h_ij - h_ji) > 1e-9

                bg = '#F0ECE4' if row % 2 == 0 else BG
                ax.add_patch(Rectangle((0.02, y - dy*0.52), 0.96, dy,
                                       transform=ax.transAxes,
                                       fc=bg, ec='none', zorder=0))

                ax.text(cx[0], y, SPIN_MINI[s0], ha='center', va='center',
                        transform=ax.transAxes, fontsize=13,
                        fontweight='bold', color='#111')
                ax.text(cx[1], y, SPIN_MINI[s1], ha='center', va='center',
                        transform=ax.transAxes, fontsize=13, color='#444')
                ax.text(cx[2], y, TIPOS[(s0,s1)], ha='center', va='center',
                        transform=ax.transAxes, fontsize=8, color='#555')

                h_str   = f'{int(h_ij):+d}' if h_ij==int(h_ij) else f'{h_ij:+.2f}'
                hji_str = f'{int(h_ji):+d}' if h_ji==int(h_ji) else f'{h_ji:+.2f}'

                ax.text(cx[3], y, h_str, ha='center', va='center',
                        transform=ax.transAxes, **styled_val(h_ij))
                ax.text(cx[4], y, hji_str, ha='center', va='center',
                        transform=ax.transAxes, **styled_val(h_ji, size=10))

                if asym:
                    ax.text(0.988, y, '≠', ha='right', va='center',
                            transform=ax.transAxes, fontsize=9,
                            color='#7C3AED', fontweight='bold')
                y -= dy; row += 1

        ax.text(0.5, 0.01,
                '●  Negro=−1     ·  Vacio=0     ○  Blanco=+1     '
                '■ ≠  indica asimetria  i→j vs j→i',
                ha='center', va='bottom', transform=ax.transAxes,
                fontsize=7.5, color='#666', style='italic')

    plt.savefig(out_path, dpi=150, bbox_inches='tight', facecolor=BG)
    print(f'Guardado: {out_path}')
    plt.close(fig)


# ══════════════════════════════════════════════════════════════════════════════
# FIGURA 2 — Entropia por bono: 19 patrones
# ══════════════════════════════════════════════════════════════════════════════

def compute_bond_metrics():
    records = []
    for pid, desc, stones in PATTERNS:
        board  = board_from_stones(BOARD_SIZE, stones)
        bonds_A = all_bond_energies_nuestro(board, manhattan_distance=1)
        bonds_B = all_bond_energies_alvarado(board)
        SA = bond_shannon_entropy(bonds_A)
        SB = bond_shannon_entropy(bonds_B)
        records.append({
            'id': pid, 'desc': desc, 'n': len(stones),
            'SA': SA, 'SB': SB,
            'bonds_A': bonds_A, 'bonds_B': bonds_B,
        })
    return records


def plot_bond_entropy(records, out_path):
    ids  = [r['id']  for r in records]
    SA   = [r['SA']  for r in records]
    SB   = [r['SB']  for r in records]
    diff = [a - b for a, b in zip(SA, SB)]

    n = len(records)
    x = np.arange(n)
    w = 0.38

    fig, axes = plt.subplots(2, 1, figsize=(18, 10), facecolor=BG)
    fig.suptitle(
        'Entropía sobre Distribución de Bonos  (interacciones binarias individuales)\n'
        'Nuestro modelo M1  vs  Atomic-Go (Alvarado 2019)',
        fontsize=13, fontweight='bold'
    )

    # Panel 1: S por bono
    ax = axes[0]
    ax.set_facecolor('#F5F5F5')
    bars_A = ax.bar(x - w/2, SA, width=w, color='#1D4ED8', alpha=0.82,
                    label='Nuestro M1  (bonos $H(s_i,s_j)$)',
                    edgecolor='white', lw=0.5)
    bars_B = ax.bar(x + w/2, SB, width=w, color='#D97706', alpha=0.82,
                    label='Atomic-Go  (bonos $x_i \\cdot x_j$)',
                    edgecolor='white', lw=0.5)
    ax.set_xticks(x); ax.set_xticklabels(ids, rotation=45, ha='right', fontsize=9)
    ax.set_ylabel('Entropía S_bono (nats)', fontsize=10)
    ax.set_title('Entropía de Shannon sobre todos los bonos del tablero\n'
                 '[mayor S = distribución de energías de bono más uniforme]',
                 fontsize=10, fontweight='bold')
    ax.legend(fontsize=9, loc='upper left')
    ax.grid(axis='y', alpha=0.3)

    for bar, v in zip(bars_A, SA):
        if v > 0.05:
            ax.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 0.01,
                    f'{v:.2f}', ha='center', fontsize=7, color='#1D4ED8',
                    fontweight='bold')
    for bar, v in zip(bars_B, SB):
        if v > 0.05:
            ax.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 0.01,
                    f'{v:.2f}', ha='center', fontsize=7, color='#D97706',
                    fontweight='bold')

    # Panel 2: Diferencia
    ax2 = axes[1]
    ax2.set_facecolor('#F5F5F5')
    colors_d = ['#1D4ED8' if d > 0 else '#D97706' for d in diff]
    ax2.bar(x, diff, color=colors_d, alpha=0.82, edgecolor='white', lw=0.5)
    ax2.axhline(0, color='#333', lw=1.5)
    ax2.set_xticks(x); ax2.set_xticklabels(ids, rotation=45, ha='right', fontsize=9)
    ax2.set_ylabel('$S_A - S_B$ (nats)', fontsize=10)
    ax2.set_title('Diferencia  [Azul: nuestro mayor  |  Naranja: Alvarado mayor]',
                  fontsize=10, fontweight='bold')
    ax2.grid(axis='y', alpha=0.3)
    for xi, d in zip(x, diff):
        if abs(d) > 0.02:
            ax2.text(xi, d + (0.02 if d >= 0 else -0.02),
                     f'{d:+.2f}', ha='center',
                     va='bottom' if d >= 0 else 'top',
                     fontsize=7.5, fontweight='bold',
                     color='#1D4ED8' if d > 0 else '#D97706')

    plt.tight_layout(rect=[0, 0, 1, 0.93])
    plt.savefig(out_path, dpi=150, bbox_inches='tight', facecolor=BG)
    print(f'Guardado: {out_path}')
    plt.close(fig)


# ══════════════════════════════════════════════════════════════════════════════
# FIGURA 3 — Distribucion de bonos para patrones seleccionados
# ══════════════════════════════════════════════════════════════════════════════

def plot_bond_distributions(records, out_path):
    sel_ids = ['1b', '4b', '5b', '8b', '14b', '19b']
    sel     = [r for r in records if r['id'] in sel_ids]

    fig, axes = plt.subplots(2, len(sel), figsize=(20, 8), facecolor=BG)
    fig.suptitle(
        'Distribución de Energías de Bono — Patrones Seleccionados\n'
        'Fila superior: Nuestro modelo M1  |  Fila inferior: Atomic-Go',
        fontsize=12, fontweight='bold'
    )

    for j, rec in enumerate(sel):
        for row, (bonds, label, color) in enumerate([
            (rec['bonds_A'], 'Nuestro M1', '#1D4ED8'),
            (rec['bonds_B'], 'Atomic-Go',  '#D97706'),
        ]):
            ax = axes[row, j]
            ax.set_facecolor('#F5F5F5')

            # Valores unicos y sus frecuencias
            unique, counts = np.unique(np.round(bonds, 6), return_counts=True)
            total = counts.sum()
            freqs = counts / total

            bar_colors = [ec(u) for u in unique]
            ax.bar([str(f'{u:+.2f}').replace('+0.00','+0') if u==0 else
                    f'{int(u):+d}' if u==int(u) else f'{u:+.2f}'
                    for u in unique],
                   freqs, color=bar_colors,
                   edgecolor='white', lw=0.5, width=0.6)

            S = bond_shannon_entropy(bonds)
            ax.set_title(
                f'{label}  (S={S:.3f})',
                fontsize=8, fontweight='bold', color=color
            )
            if row == 0:
                ax.set_xlabel(f"{rec['id']}: {rec['desc'][:18]}",
                              fontsize=8, fontweight='bold', labelpad=5)
                ax.xaxis.set_label_position('top')
                ax.xaxis.tick_top()
            ax.set_ylabel('Frecuencia', fontsize=7)
            ax.tick_params(labelsize=7)
            ax.grid(axis='y', alpha=0.3)

            for i_b, (u, f) in enumerate(zip(unique, freqs)):
                ax.text(i_b, f + 0.005, f'{f:.2f}',
                        ha='center', va='bottom', fontsize=6.5,
                        fontweight='bold', color='#222')

    plt.tight_layout(rect=[0, 0, 1, 0.91])
    plt.savefig(out_path, dpi=150, bbox_inches='tight', facecolor=BG)
    print(f'Guardado: {out_path}')
    plt.close(fig)


# ══════════════════════════════════════════════════════════════════════════════
# MAIN
# ══════════════════════════════════════════════════════════════════════════════

def main():
    print('\n' + '='*62)
    print('  COMPARACION POR BONO: Nuestro M1  vs  Alvarado Atomic-Go')
    print('='*62)

    print('\n[1/4] Tabla de bonos...')
    plot_bond_table(os.path.join(RESULTS, 'bond_interaction_table.png'))

    print('[2/4] Calculando metricas por bono...')
    records = compute_bond_metrics()

    print(f"\n{'ID':<5} {'SA_bono':>8} {'SB_bono':>8} {'diff':>8}  Descripcion")
    print('-'*60)
    for r in records:
        print(f"{r['id']:<5} {r['SA']:>8.4f} {r['SB']:>8.4f} "
              f"{r['SA']-r['SB']:>+8.4f}  {r['desc'][:30]}")

    print('\n[3/4] Grafica de entropia por bono...')
    plot_bond_entropy(records, os.path.join(RESULTS, 'bond_entropy_compare.png'))

    print('[4/4] Distribucion de bonos...')
    plot_bond_distributions(records, os.path.join(RESULTS, 'bond_distribution.png'))

    # Resumen
    SA_vals = [r['SA'] for r in records]
    SB_vals = [r['SB'] for r in records]
    n_A_mayor = sum(1 for a, b in zip(SA_vals, SB_vals) if a > b)
    n_igual    = sum(1 for a, b in zip(SA_vals, SB_vals) if abs(a-b) < 0.01)
    n_B_mayor  = sum(1 for a, b in zip(SA_vals, SB_vals) if b > a + 0.01)
    print(f'\nRESUMEN:')
    print(f'  SA > SB : {n_A_mayor}/19 patrones')
    print(f'  SA ~ SB : {n_igual}/19 patrones')
    print(f'  SB > SA : {n_B_mayor}/19 patrones')
    print(f'  Brecha media: {np.mean([a-b for a,b in zip(SA_vals,SB_vals)]):.4f} nats')
    print(f'\nListo. Resultados en: {RESULTS}')


if __name__ == '__main__':
    main()
