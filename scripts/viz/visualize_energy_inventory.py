"""
visualize_energy_inventory.py
==============================
Inventario de energias para kernels Manhattan-1 y Manhattan-2.

Para cada par (s0, s1) muestra:
  - H(s0, s1) base
  - Contribucion ponderada a distancia 1 (coef = 1.000)
  - Contribucion ponderada a distancia 2 (coef = 0.250)

Ademas: geometria del kernel, coeficientes, y rangos de energia
posibles segun el tipo de celda central.

Salida: results/energy_inventory.png
"""

import os, sys
from pathlib import Path
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.gridspec as gridspec
from matplotlib.patches import Circle, Rectangle, FancyArrow
from matplotlib.colors import TwoSlopeNorm
import matplotlib.colors
import matplotlib.cm as cm

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
RESULTS = os.path.join(str(Path(__file__).resolve().parents[2]), 'results')
os.makedirs(RESULTS, exist_ok=True)

# ─── Constantes ───────────────────────────────────────────────────────────────
SPIN_VALS  = [-1, 0, +1]
SPIN_LABEL = {-1: 'Negro ●', 0: 'Vacío ·', +1: 'Blanco ○'}
SPIN_MINI  = {-1: '●', 0: '·', +1: '○'}
COEFS      = {1: 1.0, 2: 0.25, 3: 0.111, 4: 0.0625}
BG         = '#F9F6EE'
BOARD_C    = '#C8A96E'

NORM = TwoSlopeNorm(vmin=-2.5, vcenter=0, vmax=2.5)
CMAP = cm.RdBu_r


def H(s0, s1):
    return float(s0 + 2*s1 - s0*(s1**2) - (s0**2)*s1)


def ec(h, alpha=1.0):
    r, g, b, _ = CMAP(NORM(np.clip(h, -2.5, 2.5)))
    return (r, g, b, alpha)


def draw_stone(ax, x, y, spin, r=0.28, zorder=4):
    if spin == -1:
        ax.add_patch(Circle((x, y), r, fc='#111111', ec='#000000', lw=1.2, zorder=zorder))
    elif spin == +1:
        ax.add_patch(Circle((x, y), r, fc='#F5F5F0', ec='#333333', lw=1.5, zorder=zorder))
    else:
        ax.add_patch(Circle((x, y), r, fc='none', ec='#777777', lw=1.0, ls='--', zorder=zorder))


# ══════════════════════════════════════════════════════════════════════════════
# PANEL A — Diagrama del kernel
# ══════════════════════════════════════════════════════════════════════════════

def draw_kernel(ax, max_d, label):
    """
    Dibuja una cuadricula 5x5 mostrando que celdas pertenecen al kernel
    de distancia Manhattan max_d y su coeficiente de ponderacion.
    """
    N = 5
    cx = cy = 2        # centro en (2,2)
    ax.set_facecolor('#E8E2D6')
    ax.set_xlim(-0.5, N - 0.5)
    ax.set_ylim(N - 0.5, -0.5)
    ax.set_aspect('equal')
    ax.set_xticks(range(N))
    ax.set_yticks(range(N))
    ax.set_xticklabels([f'{i-2:+d}' for i in range(N)], fontsize=7, color='#666666')
    ax.set_yticklabels([f'{i-2:+d}' for i in range(N)], fontsize=7, color='#666666')
    ax.set_xlabel('Δcol', fontsize=8, color='#444444')
    ax.set_ylabel('Δfila', fontsize=8, color='#444444')
    ax.set_title(label, fontsize=11, fontweight='bold', pad=6)

    for r in range(N):
        for c in range(N):
            d = abs(r - cy) + abs(c - cx)

            if r == cy and c == cx:
                # Centro
                ax.add_patch(Rectangle((c-.45, r-.45), .9, .9,
                                       fc='#F59E0B', ec='#D97706', lw=2, zorder=2))
                ax.text(c, r, 'centro\n$s_0$', ha='center', va='center',
                        fontsize=7, fontweight='bold', color='#1a1a1a', zorder=3)
            elif 1 <= d <= max_d:
                coef = COEFS[d]
                if d == 1:
                    fc, tc = '#1D4ED8', 'white'
                else:
                    fc, tc = '#93C5FD', '#1a1a1a'
                ax.add_patch(Rectangle((c-.45, r-.45), .9, .9,
                                       fc=fc, ec='white', lw=1.2, zorder=2))
                ax.text(c, r, f'd={d}\n×{coef:.3f}',
                        ha='center', va='center', fontsize=6.5,
                        fontweight='bold', color=tc, zorder=3)
            else:
                ax.add_patch(Rectangle((c-.45, r-.45), .9, .9,
                                       fc='#D5CDBE', ec='#C8C0B0', lw=0.5, zorder=1))
                ax.text(c, r, '—', ha='center', va='center',
                        fontsize=9, color='#AAAAAA')

    # Grid fino
    for i in range(N):
        ax.plot([-0.5, N-.5], [i-.5, i-.5], '-', color='#B8B0A0', lw=0.4)
        ax.plot([i-.5, i-.5], [-0.5, N-.5], '-', color='#B8B0A0', lw=0.4)

    n_vecinos = sum(1 for r in range(N) for c in range(N)
                    if 1 <= abs(r-cy)+abs(c-cx) <= max_d)
    n_capas   = max_d
    ax.text(0.5, -0.12,
            f'{n_vecinos} vecinos en {n_capas} capa(s)',
            transform=ax.transAxes, ha='center', fontsize=9,
            color='#333333', style='italic')


# ══════════════════════════════════════════════════════════════════════════════
# PANEL B — Tabla de contribuciones energeticas
# ══════════════════════════════════════════════════════════════════════════════

def draw_contribution_table(ax):
    ax.set_facecolor(BG)
    for sp in ax.spines.values(): sp.set_visible(False)
    ax.set_xticks([]); ax.set_yticks([])
    ax.set_title('Contribución energética por distancia y par $(s_0, s_1)$',
                 fontsize=10, fontweight='bold', pad=8)

    # Posiciones de columnas (en coordenadas de axes)
    cx = [0.08, 0.20, 0.38, 0.58, 0.79]
    headers = ['$s_0$', '$s_1$',
               '$H(s_0,s_1)$',
               'dist=1\n$\\times 1.000$',
               'dist=2\n$\\times 0.250$']

    y0 = 0.94
    for h, x in zip(headers, cx):
        ax.text(x, y0, h, ha='center', va='top', transform=ax.transAxes,
                fontsize=9, fontweight='bold', color='#1a1a1a')

    # Separador cabecera
    ax.plot([0.01, 0.99], [0.86, 0.86], '-', color='#888888',
            lw=1.0, transform=ax.transAxes)

    y = 0.82
    dy = 0.082
    row = 0

    for s0 in SPIN_VALS:
        for s1 in SPIN_VALS:
            hval = H(s0, s1)
            c1   = 1.000 * hval
            c2   = 0.250 * hval

            # Fondo alternado
            bg = '#F0ECE4' if row % 2 == 0 else BG
            ax.add_patch(Rectangle((0.01, y - dy*0.5), 0.98, dy,
                                   transform=ax.transAxes,
                                   fc=bg, ec='none', zorder=0))

            # s0
            ax.text(cx[0], y, SPIN_MINI[s0], ha='center', va='center',
                    transform=ax.transAxes, fontsize=13, color='#111111',
                    fontweight='bold')
            # s1
            ax.text(cx[1], y, SPIN_MINI[s1], ha='center', va='center',
                    transform=ax.transAxes, fontsize=13, color='#444444')

            # H
            h_str = f'{int(hval):+d}' if hval == int(hval) else f'{hval:+.2f}'
            ax.text(cx[2], y, h_str, ha='center', va='center',
                    transform=ax.transAxes,
                    fontsize=11, fontweight='bold', color=ec(hval),
                    bbox=dict(boxstyle='round,pad=0.25',
                              fc=ec(hval, 0.12), ec='none'))

            # Contribucion d=1
            c1s = f'{int(c1):+d}' if c1 == int(c1) else f'{c1:+.3f}'
            ax.text(cx[3], y, c1s, ha='center', va='center',
                    transform=ax.transAxes, fontsize=10,
                    fontweight='bold', color=ec(c1))

            # Contribucion d=2 — color intenso por signo, no por magnitud
            if c2 > 0:
                c2_color = '#C2410C'   # rojo intenso
            elif c2 < 0:
                c2_color = '#1D4ED8'   # azul intenso
            else:
                c2_color = '#6B7280'   # gris

            ax.text(cx[4], y, f'{c2:+.3f}', ha='center', va='center',
                    transform=ax.transAxes, fontsize=10,
                    fontweight='bold', color=c2_color,
                    bbox=dict(boxstyle='round,pad=0.18',
                              fc=(*matplotlib.colors.to_rgb(c2_color), 0.10),
                              ec='none'))

            y   -= dy
            row += 1


# ══════════════════════════════════════════════════════════════════════════════
# PANEL C — Rangos de energia total por tipo de centro
# ══════════════════════════════════════════════════════════════════════════════

def draw_energy_ranges(ax):
    """
    Para una celda en interior del tablero (maximos vecinos disponibles):
      M1: 4 vecinos a d=1, coef=1.0
      M2: 4 vecinos a d=1 (coef=1.0) + 8 vecinos a d=2 (coef=0.25)
    Muestra el rango [min, max] de energia total segun que piedras
    esten en esos vecinos.
    """
    ax.set_facecolor('#F5F5F5')
    ax.set_title('Rango de energía total posible  (celda en interior del tablero)',
                 fontsize=10, fontweight='bold', pad=8)

    n_d1 = 4
    n_d2 = 8

    entries = []
    for s0 in SPIN_VALS:
        h_all = [H(s0, s) for s in SPIN_VALS]
        h_min, h_max = min(h_all), max(h_all)

        # Cada vecino puede ser cualquier spin → elegimos independientemente
        m1_min = n_d1 * COEFS[1] * h_min
        m1_max = n_d1 * COEFS[1] * h_max
        m2_min = n_d1 * COEFS[1] * h_min + n_d2 * COEFS[2] * h_min
        m2_max = n_d1 * COEFS[1] * h_max + n_d2 * COEFS[2] * h_max

        entries.append((s0, m1_min, m1_max, m2_min, m2_max,
                        f'{SPIN_LABEL[s0]}\n$(s_0={s0:+d})$'))

    x_pos  = np.array([0.0, 1.8, 3.6])
    width  = 0.55
    col_m1 = '#1D4ED8'
    col_m2 = '#F97316'

    for xi, (s0, m1n, m1x, m2n, m2x, lbl) in zip(x_pos, entries):
        # M1
        ax.bar(xi - width*0.55, m1x - m1n, bottom=m1n,
               width=width, color=col_m1, alpha=0.78, label='Manhattan-1' if s0==-1 else '')
        ax.text(xi - width*0.55, m1x + 0.15, f'{m1x:+.0f}',
                ha='center', fontsize=8.5, fontweight='bold', color=col_m1)
        ax.text(xi - width*0.55, m1n - 0.15, f'{m1n:+.0f}',
                ha='center', va='top', fontsize=8.5, fontweight='bold', color=col_m1)

        # M2
        ax.bar(xi + width*0.55, m2x - m2n, bottom=m2n,
               width=width, color=col_m2, alpha=0.78, label='Manhattan-2' if s0==-1 else '')
        ax.text(xi + width*0.55, m2x + 0.15, f'{m2x:+.0f}',
                ha='center', fontsize=8.5, fontweight='bold', color=col_m2)
        ax.text(xi + width*0.55, m2n - 0.15, f'{m2n:+.0f}',
                ha='center', va='top', fontsize=8.5, fontweight='bold', color=col_m2)

        # Label de tipo de centro (con mini stone)
        ax.text(xi, -15, lbl, ha='center', va='top', fontsize=9,
                fontweight='bold', color='#222222')

    ax.axhline(0, color='#444444', lw=1.5, zorder=3)
    ax.set_xticks([])
    ax.set_ylim(-16, 14)
    ax.set_ylabel('Energía total en la celda central', fontsize=9)
    ax.legend(loc='upper right', fontsize=9, framealpha=0.85)
    ax.grid(axis='y', alpha=0.3)

    # Anotacion explicativa
    ax.text(0.5, 0.01,
            'Cada vecino puede ser ● · ○ independientemente  →  '
            'se elige la combinacion que maximiza o minimiza la suma',
            transform=ax.transAxes, ha='center', va='bottom',
            fontsize=7.5, color='#666666', style='italic')


# ══════════════════════════════════════════════════════════════════════════════
# FIGURA PRINCIPAL
# ══════════════════════════════════════════════════════════════════════════════

def create_figure(out_path):
    fig = plt.figure(figsize=(20, 15), facecolor=BG)

    # Titulo global
    fig.text(0.5, 0.983,
             'Inventario de Energías — Modelo de Ising Clásico para Go',
             ha='center', fontsize=15, fontweight='bold', color='#1a1a1a')
    fig.text(0.5, 0.960,
             r'$H(s_0,\,s_1) = s_0 + 2s_1 - s_0 s_1^2 - s_0^2 s_1'
             r'\qquad\text{coef}(d) = 1/d^2'
             r'\quad\Rightarrow\quad'
             r'\text{coef}(1)=1.000,\;\text{coef}(2)=0.250$',
             ha='center', fontsize=11, color='#333333', style='italic')

    gs = gridspec.GridSpec(
        2, 3,
        left=0.04, right=0.98, top=0.950, bottom=0.06,
        wspace=0.28, hspace=0.38,
        width_ratios=[1, 1, 1.55],
        height_ratios=[1.3, 1],
    )

    # ── Kernels ───────────────────────────────────────────────────────────────
    ax_k1 = fig.add_subplot(gs[0, 0])
    draw_kernel(ax_k1, 1,
                'Kernel Manhattan-1\n(4 vecinos, 1 capa)')

    ax_k2 = fig.add_subplot(gs[0, 1])
    draw_kernel(ax_k2, 2,
                'Kernel Manhattan-2\n(12 vecinos, 2 capas)')

    # ── Tabla de contribuciones ───────────────────────────────────────────────
    ax_tab = fig.add_subplot(gs[0, 2])
    draw_contribution_table(ax_tab)

    # ── Rangos de energia ─────────────────────────────────────────────────────
    ax_rng = fig.add_subplot(gs[1, :])
    draw_energy_ranges(ax_rng)

    plt.savefig(out_path, dpi=150, bbox_inches='tight', facecolor=BG)
    print(f'Guardado: {out_path}')
    plt.close(fig)


if __name__ == '__main__':
    out = os.path.join(RESULTS, 'energy_inventory.png')
    create_figure(out)
    print('Listo.')
