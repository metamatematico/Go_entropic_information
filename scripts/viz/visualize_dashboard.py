"""
visualize_dashboard.py
======================
Dashboard comprensivo para los 19 patrones de apertura de Go.

Muestra en una sola figura:
  - Mini tableros (con las piedras reales) ORDENADOS de menor a mayor entropia
  - Barra de color por patron (gradiente: azul=ordenado → rojo=caotico)
  - Scatter T_eff vs S_shannon (espacio termodinamico)
  - Ranking horizontal con descripcion completa

Uso:
    python visualize_dashboard.py           # M=1 por defecto
    python visualize_dashboard.py --m 2     # kernel Manhattan-2
"""

import sys
from pathlib import Path
import os
import argparse
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.gridspec as gridspec
from matplotlib.patches import Circle
from matplotlib.colors import Normalize
from matplotlib.cm import ScalarMappable

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from src.go_entropy import GoEntropyAnalyzer, board_from_stones
from analysis_patterns import PATTERNS, BOARD_SIZE

RESULTS_DIR = os.path.join(str(Path(__file__).resolve().parents[2]), 'results')
os.makedirs(RESULTS_DIR, exist_ok=True)

CORNER = 6   # cuantas filas/cols mostrar en el mini tablero


# ============================================================================
# HELPERS
# ============================================================================

def compute_all(manhattan_distance: int = 1) -> list:
    """Calcula metricas para los 19 patrones y los devuelve ordenados por S."""
    analyzer = GoEntropyAnalyzer(manhattan_distance=manhattan_distance)
    records = []
    for pid, desc, stones in PATTERNS:
        board = board_from_stones(BOARD_SIZE, stones)
        r = analyzer.analyze(board)
        T = r['T_eff']
        records.append({
            'id':    pid,
            'desc':  desc,
            'n':     len(stones),
            'board': board,
            'emap':  r['energy_map'],
            'S':     r['S_shannon'],
            'T':     T,
            'T_cap': min(T, 25.0),     # version sin inf para graficar
            'T_inf': not np.isfinite(T),
            'Sb':    r['S_boltzmann'],
            'E':     r['total_energy'],
        })
    records.sort(key=lambda x: x['S'])
    return records


def draw_mini_board(ax, board: np.ndarray, emap: np.ndarray = None,
                    size: int = CORNER, stone_radius: float = 0.39):
    """
    Dibuja un mini tablero mostrando los primeros 'size' x 'size' casillas
    (esquina superior izquierda, donde estan los patrones de apertura).
    Superpone el mapa de energia como fondo de color si se provee.
    """
    b = board[:size, :size]

    ax.set_facecolor('#C8A05A')
    ax.set_xlim(-0.5, size - 0.5)
    ax.set_ylim(size - 0.5, -0.5)   # invertido: fila 0 arriba
    ax.set_aspect('equal')
    ax.set_xticks([])
    ax.set_yticks([])
    for spine in ax.spines.values():
        spine.set_linewidth(0.5)

    # Cuadricula
    for i in range(size):
        ax.plot([0, size-1], [i, i], 'k-', lw=0.3, zorder=1)
        ax.plot([i, i], [0, size-1], 'k-', lw=0.3, zorder=1)

    # Mapa de energia (overlay suave)
    if emap is not None:
        e = emap[:size, :size]
        vmax = max(abs(e.min()), abs(e.max()), 1e-9)
        ax.imshow(e, cmap='RdBu_r', vmin=-vmax, vmax=vmax,
                  origin='upper', alpha=0.45, zorder=2,
                  extent=(-0.5, size-0.5, size-0.5, -0.5))

    # Piedras
    for r in range(size):
        for c in range(size):
            s = b[r, c]
            if s == 'B':
                ax.add_patch(Circle((c, r), stone_radius,
                                    fc='#111111', ec='black', lw=0.6, zorder=3))
            elif s == 'W':
                ax.add_patch(Circle((c, r), stone_radius,
                                    fc='white', ec='#444444', lw=0.8, zorder=3))


# ============================================================================
# DASHBOARD PRINCIPAL
# ============================================================================

def create_dashboard(records: list, M: int, output_path: str):
    """
    Una sola figura con cuatro secciones:

      [A] Fila de mini tableros ordenados por entropia (izq=ordenado, der=caotico)
      [B] Barra de color debajo de cada tablero (gradiente de entropia)
      [C] Scatter T_eff vs S_shannon (espacio termodinamico)
      [D] Ranking horizontal con descripcion completa
    """
    n = len(records)
    S_all = [r['S'] for r in records]
    S_min, S_max = min(S_all), max(S_all)

    # Paleta de entropia: azul (ordenado) → rojo (caotico)
    cmap_S = plt.cm.get_cmap('RdYlBu_r')
    norm_S = Normalize(vmin=S_min, vmax=S_max)

    def color_S(s):
        return cmap_S(norm_S(s))

    fig = plt.figure(figsize=(24, 14))
    fig.patch.set_facecolor('#F8F8F8')

    # Titulo general
    fig.text(0.5, 0.97,
             f'Entropía de la distribución de energía (Ising Clásico, Manhattan-{M})\n'
             f'19 patrones de apertura de Go — Tabla I  '
             f'(Journal of Go Studies, 2025)',
             ha='center', va='top', fontsize=13, fontweight='bold', color='#1a1a1a')

    fig.text(0.5, 0.92,
             'Los tableros están ORDENADOS de menor (izquierda) a mayor entropía (derecha).\n'
             'Azul = energía concentrada en pocas celdas (patrón local).   '
             'Rojo = energía distribuida por todo el tablero (patrón complejo).',
             ha='center', va='top', fontsize=9, color='#444444', style='italic')

    # ---- Seccion A+B: mini tableros + barra de color ----
    # 19 columnas, 2 filas (tablero + barra)
    gs_top = gridspec.GridSpec(
        2, n,
        left=0.01, right=0.99,
        top=0.88, bottom=0.50,
        hspace=0.05, wspace=0.06,
        height_ratios=[5, 1],
    )

    for i, rec in enumerate(records):
        # Fila 0: mini tablero
        ax_board = fig.add_subplot(gs_top[0, i])
        draw_mini_board(ax_board, rec['board'], rec['emap'])

        # Etiqueta de ID encima del tablero
        ax_board.set_title(rec['id'], fontsize=8, fontweight='bold',
                           pad=2, color='#111111')

        # Fila 1: barra de color con S y T
        ax_bar = fig.add_subplot(gs_top[1, i])
        ax_bar.set_facecolor(color_S(rec['S']))
        ax_bar.set_xticks([])
        ax_bar.set_yticks([])
        for spine in ax_bar.spines.values():
            spine.set_color('white')
            spine.set_linewidth(0.4)

        t_str = '∞' if rec['T_inf'] else f"{rec['T']:.1f}"
        text_color = 'white' if rec['S'] > (S_min + S_max) / 2 else '#222222'
        ax_bar.text(0.5, 0.62, f"S={rec['S']:.2f}",
                    ha='center', va='center', fontsize=6.5,
                    fontweight='bold', color=text_color,
                    transform=ax_bar.transAxes)
        ax_bar.text(0.5, 0.20, f"T={t_str}",
                    ha='center', va='center', fontsize=5.5,
                    color=text_color, transform=ax_bar.transAxes)

    # Etiquetas de extremos
    fig.text(0.01, 0.50, '← Más ordenado\n   (S bajo)',
             ha='left', va='top', fontsize=8, color='#2563EB', fontweight='bold')
    fig.text(0.99, 0.50, 'Más desordenado →\n(S alto)',
             ha='right', va='top', fontsize=8, color='#DC2626', fontweight='bold')

    # ---- Seccion C: Scatter T vs S ----
    gs_bot = gridspec.GridSpec(
        1, 2,
        left=0.05, right=0.99,
        top=0.46, bottom=0.06,
        wspace=0.32,
    )

    ax_sc = fig.add_subplot(gs_bot[0, 0])
    ax_sc.set_facecolor('#FAFAFA')

    T_cap = [r['T_cap'] for r in records]
    S_vals = [r['S'] for r in records]
    n_vals = [r['n'] for r in records]
    colors_sc = [color_S(s) for s in S_vals]

    sc = ax_sc.scatter(S_vals, T_cap,
                       c=S_vals, cmap='RdYlBu_r', vmin=S_min, vmax=S_max,
                       s=[50 + 20 * nv for nv in n_vals],
                       edgecolors='#555', linewidths=0.6, zorder=3)

    for rec, t in zip(records, T_cap):
        offset = (4, 4) if rec['T'] < 15 else (4, -8)
        ax_sc.annotate(
            rec['id'],
            (rec['S'], t),
            xytext=offset, textcoords='offset points',
            fontsize=6.5, color='#222222',
            zorder=4,
        )
        if rec['T_inf']:
            ax_sc.annotate('↑∞', (rec['S'], t),
                           xytext=(0, 6), textcoords='offset points',
                           fontsize=7, color='#DC2626', ha='center', zorder=4)

    # Cuadrantes con fondo suave
    S_mid = (S_min + S_max) / 2
    T_mid = 8.0
    ax_sc.axvline(S_mid, color='gray', lw=0.8, ls='--', alpha=0.5)
    ax_sc.axhline(T_mid, color='gray', lw=0.8, ls='--', alpha=0.5)
    ax_sc.text(S_min + 0.02, T_mid + 0.3, 'Frío\nordenado',
               fontsize=7, color='#2563EB', style='italic', va='bottom')
    ax_sc.text(S_max - 0.02, T_mid + 0.3, 'Frío\ncaótico',
               fontsize=7, color='#7C3AED', style='italic', va='bottom', ha='right')
    ax_sc.text(S_min + 0.02, 0.3, 'Concentrado\nsin fluctuaciones',
               fontsize=7, color='#0369A1', style='italic', va='bottom')
    ax_sc.text(S_max - 0.02, 0.3, 'Difuso\nsin fluctuaciones',
               fontsize=7, color='#B45309', style='italic', va='bottom', ha='right')

    ax_sc.set_xlabel('Entropía de Shannon  S (nats)\n[mayor S = energía más distribuida]',
                     fontsize=9)
    ax_sc.set_ylabel('Temperatura efectiva T\n[∞ = distribución simétrica de energía]',
                     fontsize=9)
    ax_sc.set_title('Espacio termodinámico: T vs S\n'
                    'Tamaño del punto ∝ número de piedras',
                    fontsize=9, fontweight='bold')
    ax_sc.grid(True, alpha=0.25)

    cb = plt.colorbar(sc, ax=ax_sc, shrink=0.7, pad=0.02)
    cb.set_label('S Shannon', fontsize=8)

    # ---- Seccion D: Ranking horizontal con descripciones ----
    ax_rank = fig.add_subplot(gs_bot[0, 1])
    ax_rank.set_facecolor('#FAFAFA')

    labels  = [f"{r['id']:>3}  {r['desc'][:38]}" for r in records]
    s_vals  = [r['S'] for r in records]
    bar_colors = [color_S(s) for s in s_vals]

    ypos = np.arange(n)
    bars = ax_rank.barh(ypos, s_vals, color=bar_colors,
                        edgecolor='white', linewidth=0.4, height=0.75)
    ax_rank.set_yticks(ypos)
    ax_rank.set_yticklabels(labels, fontsize=7, fontfamily='monospace')
    ax_rank.set_xlabel('Entropía de Shannon S (nats)', fontsize=9)
    ax_rank.set_title('Ranking de menor a mayor entropía\n'
                      'Rojo = posición más compleja  /  Azul = posición más local',
                      fontsize=9, fontweight='bold')
    ax_rank.set_xlim(0, S_max * 1.18)
    ax_rank.invert_yaxis()   # más ordenado arriba

    for bar, s, rec in zip(bars, s_vals, records):
        t_str = '∞' if rec['T_inf'] else f"T={rec['T']:.1f}"
        ax_rank.text(s + 0.01, bar.get_y() + bar.get_height() / 2,
                     f" {s:.2f}  {t_str}",
                     va='center', fontsize=6.5, color='#333333')

    ax_rank.grid(axis='x', alpha=0.25)

    # Leyenda de piedras en scatter
    for nv, label in [(1, '1 piedra'), (3, '3 piedras'), (5, '5+ piedras')]:
        ax_sc.scatter([], [], s=50 + 20*nv, c='gray', alpha=0.5,
                      edgecolors='gray', linewidths=0.5, label=label)
    ax_sc.legend(fontsize=7, loc='lower right', framealpha=0.7)

    plt.savefig(output_path, dpi=150, bbox_inches='tight', facecolor=fig.get_facecolor())
    print(f"Guardado: {output_path}")
    plt.close(fig)


# ============================================================================
# MAIN
# ============================================================================

def main():
    parser = argparse.ArgumentParser(description='Dashboard de entropia de patrones de Go')
    parser.add_argument('--m', type=int, default=1, choices=[1, 2],
                        help='Kernel Manhattan (default: 1)')
    args = parser.parse_args()

    M = args.m
    print(f"\nCalculando metricas con Manhattan-{M}...")
    records = compute_all(manhattan_distance=M)

    out = os.path.join(RESULTS_DIR, f'dashboard_M{M}.png')
    create_dashboard(records, M, out)
    print(f"\nListo: {out}")


if __name__ == '__main__':
    main()
