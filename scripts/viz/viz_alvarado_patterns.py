"""
viz_alvarado_patterns.py
========================
Visualizacion del modelo Alvarado (Atomic-Go) para los 19 patrones de apertura.

Genera:
  results/energy_grid_alvarado.png  — cuadricula de 19 tableros con overlay de energia
  results/dashboard_alvarado.png    — dashboard: scatter T_eff vs S_shannon + ranking
"""

import os, sys
from pathlib import Path
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.gridspec as gridspec
from matplotlib.patches import Circle, FancyBboxPatch
from matplotlib.colors import Normalize, TwoSlopeNorm
from matplotlib.cm import ScalarMappable
import matplotlib.cm as cm

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from compare_per_bond import (
    H_alvarado, all_bond_energies_alvarado,
    bond_shannon_entropy, bond_boltzmann_entropy, bond_T_eff,
    SPIN_VALS,
)
from analysis_patterns import PATTERNS, BOARD_SIZE
from src.go_entropy import board_from_stones

RESULTS = os.path.join(str(Path(__file__).resolve().parents[2]), 'results')
os.makedirs(RESULTS, exist_ok=True)

BG       = '#F9F6EE'
BOARD_C  = '#C8A96E'
CORNER   = 6
SPIN     = {'B': -1, '.': 0, 'W': +1}


# ═══════════════════════════════════════════════════════════════════════════
# UTILIDADES
# ═══════════════════════════════════════════════════════════════════════════

def spin(v):
    if isinstance(v, str):
        return SPIN.get(v, 0)
    return int(v)


def alvarado_energy_map(board):
    """Energia total de cada celda bajo Alvarado: E_i = sum_j(s_i * s_j)."""
    rows, cols = board.shape
    emap = np.zeros((rows, cols), dtype=float)
    dirs = [(0, 1), (0, -1), (1, 0), (-1, 0)]
    for r in range(rows):
        for c in range(cols):
            si = spin(board[r, c])
            for dr, dc in dirs:
                nr, nc = r + dr, c + dc
                if 0 <= nr < rows and 0 <= nc < cols:
                    sj = spin(board[nr, nc])
                    emap[r, c] += si * sj
    return emap


def compute_metrics(board):
    bAL = all_bond_energies_alvarado(board)
    T   = bond_T_eff(bAL)
    return {
        'emap':  alvarado_energy_map(board),
        'bonds': bAL,
        'S_sh':  bond_shannon_entropy(bAL),
        'S_bo':  bond_boltzmann_entropy(bAL),
        'T':     T,
        'T_cap': min(T, 25.0) if np.isfinite(T) else 25.0,
        'T_inf': not np.isfinite(T),
        'E_tot': float(bAL.sum()),
    }


def compute_all():
    records = []
    for pid, desc, stones in PATTERNS:
        board = board_from_stones(BOARD_SIZE, stones)
        m = compute_metrics(board)
        records.append({
            'id': pid, 'desc': desc, 'n': len(stones),
            'board': board, **m,
        })
    return records


def draw_mini_board(ax, board, emap=None, size=CORNER, sr=0.39, show_energy=True):
    b = board[:size, :size]
    ax.set_facecolor(BOARD_C)
    ax.set_xlim(-0.5, size - 0.5)
    ax.set_ylim(size - 0.5, -0.5)
    ax.set_aspect('equal')
    ax.set_xticks([])
    ax.set_yticks([])
    for sp in ax.spines.values():
        sp.set_linewidth(0.8)
        sp.set_edgecolor('#8B6914')

    for i in range(size):
        ax.plot([0, size - 1], [i, i], '-', color='#5A3A1A', lw=0.35, zorder=1)
        ax.plot([i, i], [0, size - 1], '-', color='#5A3A1A', lw=0.35, zorder=1)

    if emap is not None and show_energy:
        e = emap[:size, :size]
        vmax = max(abs(e.min()), abs(e.max()), 1e-6)
        norm = TwoSlopeNorm(vmin=-vmax, vcenter=0, vmax=vmax)
        ax.imshow(e, cmap='RdBu_r', norm=norm,
                  origin='upper', alpha=0.50, zorder=2,
                  extent=(-0.5, size - 0.5, size - 0.5, -0.5))

    for r in range(size):
        for c in range(size):
            s = b[r, c]
            if s == 'B':
                ax.add_patch(Circle((c, r), sr, fc='#111', ec='#000',
                                    lw=0.8, zorder=3))
            elif s == 'W':
                ax.add_patch(Circle((c, r), sr, fc='white', ec='#444',
                                    lw=1.0, zorder=3))


# ═══════════════════════════════════════════════════════════════════════════
# FIGURA 1: ENERGY GRID (cuadricula 19 patrones)
# ═══════════════════════════════════════════════════════════════════════════

def make_energy_grid(records, out_path):
    COLS = 5
    ROWS = 4   # 4 filas × 5 cols = 20, usamos 19
    fig = plt.figure(figsize=(22, 18), facecolor=BG)

    fig.text(0.5, 0.975,
             'Modelo Alvarado (Atomic-Go)  —  Mapas de Energia por Patron de Apertura',
             ha='center', fontsize=16, fontweight='bold', color='#0F2044')
    fig.text(0.5, 0.955,
             r'$H(x_i, x_j) = x_i \cdot x_j$'
             r'     ($\mu=0$, $w_{ij}=1$)     |     '
             r'Color de fondo: energia celda $E_i = \sum_j x_i x_j$     |     '
             r'Azul = atraccion, Rojo = repulsion',
             ha='center', fontsize=11, color='#444')

    gs_outer = gridspec.GridSpec(
        ROWS, COLS, figure=fig,
        left=0.03, right=0.97, top=0.945, bottom=0.04,
        wspace=0.10, hspace=0.30,
    )

    cmap_S  = cm.get_cmap('RdYlBu_r')
    S_all   = [r['S_sh'] for r in records]
    norm_S  = Normalize(vmin=min(S_all), vmax=max(S_all))

    for idx, rec in enumerate(records):
        row, col = divmod(idx, COLS)
        inner = gridspec.GridSpecFromSubplotSpec(
            2, 1, subplot_spec=gs_outer[row, col],
            height_ratios=[9, 1], hspace=0.04,
        )
        ax_b = fig.add_subplot(inner[0])
        ax_s = fig.add_subplot(inner[1])

        draw_mini_board(ax_b, rec['board'], rec['emap'])

        # Titulo del tablero
        ax_b.set_title(
            f"{rec['id']}: {rec['desc'][:22]}",
            fontsize=7.5, fontweight='bold', pad=3, color='#1F2937',
        )
        # Metricas en esquina
        T_lbl = 'inf' if rec['T_inf'] else f"{rec['T']:.2f}"
        ax_b.text(0.02, 0.97,
                  f"S={rec['S_sh']:.2f}  T={T_lbl}",
                  transform=ax_b.transAxes, ha='left', va='top',
                  fontsize=7, color='white',
                  bbox=dict(fc='#00000077', ec='none', pad=2))

        # Barra de color S_shannon
        color = cmap_S(norm_S(rec['S_sh']))
        ax_s.set_facecolor(color)
        ax_s.set_xticks([])
        ax_s.set_yticks([])
        ax_s.text(0.5, 0.5, f"S = {rec['S_sh']:.3f} nats",
                  transform=ax_s.transAxes, ha='center', va='center',
                  fontsize=7.5, fontweight='bold',
                  color='white' if rec['S_sh'] > (min(S_all) + max(S_all)) / 2 else '#222')

    # Celda 20 vacía — leyenda de color
    row, col = divmod(len(records), COLS)
    ax_leg = fig.add_subplot(gs_outer[row, col])
    ax_leg.set_facecolor(BG)
    ax_leg.axis('off')
    sm = ScalarMappable(cmap='RdYlBu_r', norm=norm_S)
    sm.set_array([])
    cbar = fig.colorbar(sm, ax=ax_leg, orientation='vertical',
                        fraction=0.6, pad=0.0)
    cbar.set_label('S_Shannon (nats)', fontsize=9)
    ax_leg.text(0.5, 0.0, 'Azul=ordenado\nRojo=caotico',
                transform=ax_leg.transAxes, ha='center', va='bottom',
                fontsize=8, color='#444')

    plt.savefig(out_path, dpi=150, bbox_inches='tight', facecolor=BG)
    plt.close()
    print(f'  Guardado: {out_path}')


# ═══════════════════════════════════════════════════════════════════════════
# FIGURA 2: DASHBOARD ALVARADO
# ═══════════════════════════════════════════════════════════════════════════

def make_dashboard(records, out_path):
    rec_sorted = sorted(records, key=lambda x: x['S_sh'])
    n   = len(rec_sorted)
    S_a = [r['S_sh'] for r in rec_sorted]

    cmap_S = cm.get_cmap('RdYlBu_r')
    norm_S = Normalize(vmin=min(S_a), vmax=max(S_a))

    fig = plt.figure(figsize=(24, 14), facecolor='#F8F8F8')
    fig.text(0.5, 0.975,
             'Dashboard — Modelo Alvarado (Atomic-Go)  |  19 Patrones de Apertura',
             ha='center', fontsize=15, fontweight='bold', color='#0F2044')
    fig.text(0.5, 0.955,
             r'$H(x_i, x_j) = x_i \cdot x_j$   |   '
             r'Ordenados de menor (izquierda) a mayor (derecha) entropia de Shannon',
             ha='center', fontsize=10, color='#555', style='italic')

    gs = gridspec.GridSpec(
        3, n, figure=fig,
        left=0.04, right=0.98, top=0.940, bottom=0.08,
        wspace=0.12, hspace=0.35,
        height_ratios=[4, 0.4, 3],
    )

    for i, rec in enumerate(rec_sorted):
        color = cmap_S(norm_S(rec['S_sh']))

        # Mini tablero con energia overlay
        ax_b = fig.add_subplot(gs[0, i])
        draw_mini_board(ax_b, rec['board'], rec['emap'], size=CORNER)

        pid = rec['id']
        ax_b.set_title(f"#{pid}", fontsize=8, fontweight='bold',
                       pad=2, color='#1F2937')
        T_lbl = 'inf' if rec['T_inf'] else f"{rec['T']:.1f}"
        ax_b.text(0.5, -0.07,
                  f"S={rec['S_sh']:.2f}\nT={T_lbl}",
                  transform=ax_b.transAxes, ha='center', va='top',
                  fontsize=6.5, color='#333', multialignment='center')

        # Barra de color
        ax_c = fig.add_subplot(gs[1, i])
        ax_c.set_facecolor(color)
        ax_c.set_xticks([])
        ax_c.set_yticks([])

    # Scatter S_shannon vs T_eff
    gs2 = gridspec.GridSpec(
        1, 2, figure=fig,
        left=0.06, right=0.94, top=0.38, bottom=0.09,
        wspace=0.30,
    )

    ax_sc = fig.add_subplot(gs2[0, 0])
    T_plot = [r['T_cap'] for r in rec_sorted]
    S_plot = [r['S_sh'] for r in rec_sorted]
    colors = [cmap_S(norm_S(s)) for s in S_plot]

    sc = ax_sc.scatter(S_plot, T_plot, c=colors, s=140, edgecolors='#333',
                       linewidths=0.8, zorder=3)
    for r, tp, sp in zip(rec_sorted, T_plot, S_plot):
        ax_sc.text(sp, tp + 0.3, str(r['id']),
                   ha='center', fontsize=7, color='#333')
    ax_sc.set_xlabel('Entropia de Shannon S (nats)', fontsize=10)
    ax_sc.set_ylabel('Temperatura efectiva T_eff (cap. en 25)', fontsize=9)
    ax_sc.set_title('Espacio termodinamico (Alvarado)', fontsize=11,
                    fontweight='bold', color='#D97706')
    ax_sc.axhline(25, color='#888', lw=0.8, ls='--', label='T_eff = inf')
    ax_sc.legend(fontsize=8)
    ax_sc.grid(alpha=0.3)

    # Ranking horizontal
    ax_rk = fig.add_subplot(gs2[0, 1])
    ax_rk.set_facecolor('white')
    ax_rk.set_xlim(0, 1)
    ax_rk.set_ylim(-0.5, n - 0.5)
    ax_rk.set_yticks([])
    ax_rk.set_xticks([])
    ax_rk.set_title('Ranking por S_Shannon (Alvarado)', fontsize=11,
                    fontweight='bold', color='#D97706')

    for ki, rec in enumerate(reversed(rec_sorted)):
        yi  = ki
        s   = rec['S_sh']
        bar_w = (s - min(S_a)) / (max(S_a) - min(S_a) + 1e-9) * 0.55
        color = cmap_S(norm_S(s))
        ax_rk.barh(yi, bar_w + 0.04, left=0.17, color=color, alpha=0.85,
                   height=0.82, zorder=2)
        T_lbl = 'inf' if rec['T_inf'] else f"T={rec['T']:.1f}"
        ax_rk.text(0.01, yi,
                   f"{n-ki:2d}. #{rec['id']}  {rec['desc'][:30]}",
                   va='center', fontsize=7.5, color='#1F2937', zorder=3)
        ax_rk.text(0.74, yi, f"{s:.3f} | {T_lbl}",
                   va='center', ha='left', fontsize=7.5,
                   color='#333', zorder=3)
    ax_rk.axvline(0.17, color='#ccc', lw=0.8)

    # Colorbar global
    sm = ScalarMappable(cmap='RdYlBu_r', norm=norm_S)
    sm.set_array([])
    cbar = fig.colorbar(sm, ax=[ax_sc, ax_rk], orientation='horizontal',
                        fraction=0.04, pad=0.12, aspect=40)
    cbar.set_label('S_Shannon (nats)  —  Azul = ordenado, Rojo = caotico',
                   fontsize=9)

    plt.savefig(out_path, dpi=150, bbox_inches='tight', facecolor='#F8F8F8')
    plt.close()
    print(f'  Guardado: {out_path}')


# ═══════════════════════════════════════════════════════════════════════════
# MAIN
# ═══════════════════════════════════════════════════════════════════════════

if __name__ == '__main__':
    print('Calculando metricas Alvarado para 19 patrones...')
    records = compute_all()
    for r in records:
        T = r['T']
        T_s = 'inf' if r['T_inf'] else f"{T:.3f}"
        print(f"  #{r['id']:2s}  n={r['n']}  S_sh={r['S_sh']:.3f}"
              f"  S_bo={r['S_bo']:.2f}  T_eff={T_s}  E={r['E_tot']:.1f}")

    print('\nGenerando energy grid...')
    make_energy_grid(records, os.path.join(RESULTS, 'energy_grid_alvarado.png'))

    print('Generando dashboard...')
    make_dashboard(records, os.path.join(RESULTS, 'dashboard_alvarado.png'))

    print('\nListo.')
