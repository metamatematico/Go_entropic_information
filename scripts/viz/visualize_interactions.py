"""
visualize_interactions.py
=========================
Visualiza las 9 interacciones binarias del Hamiltoniano de Ising clasico:

    H(s0, s1) = s0 + 2*s1 - s0*s1^2 - s0^2*s1

con s0, s1 in {-1, 0, +1}  (Negro, Vacio, Blanco)

Genera:
    results/interactions_H.png   — figura completa
    results/interactions_H.txt   — tabla de texto
"""

import os, sys
from pathlib import Path
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.gridspec as gridspec
from matplotlib.patches import Circle
from matplotlib.colors import TwoSlopeNorm
import matplotlib.cm as cm

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
RESULTS = os.path.join(str(Path(__file__).resolve().parents[2]), 'results')
os.makedirs(RESULTS, exist_ok=True)

# ─── Datos ────────────────────────────────────────────────────────────────────

SPIN_VALS  = [-1, 0, +1]
SPIN_LABEL = {-1: 'Negro  ●', 0: 'Vacío  ·', +1: 'Blanco ○'}
SPIN_SHORT = {-1: '●', 0: '·', +1: '○'}
BOARD_C    = '#C8A96E'
GRID_C     = '#7A5C2E'
BG         = '#F9F6EE'


def H(s0, s1):
    """Hamiltoniano clasico de Ising para Go."""
    return float(s0 + 2*s1 - s0*(s1**2) - (s0**2)*s1)


H_tab = np.array([[H(s0, s1) for s1 in SPIN_VALS] for s0 in SPIN_VALS])
VMAX  = 2.0
NORM  = TwoSlopeNorm(vmin=-VMAX, vcenter=0, vmax=VMAX)
CMAP  = cm.RdBu_r


def hcolor(h):
    return CMAP(NORM(h))


# ─── Helpers de dibujo ────────────────────────────────────────────────────────

def draw_stone(ax, x, y, spin, r=0.30):
    if spin == -1:
        ax.add_patch(Circle((x, y), r, fc='#111111', ec='#000000', lw=1.2, zorder=3))
    elif spin == +1:
        ax.add_patch(Circle((x, y), r, fc='#F5F5F0', ec='#333333', lw=1.5, zorder=3))
    else:
        ax.add_patch(Circle((x, y), r, fc='none', ec='#888888',
                            lw=1.0, ls='--', zorder=3))


def draw_cell(ax, s0, s1):
    """
    Dibuja en 'ax' la interaccion entre el centro (s0) y un vecino (s1).

    Distribucion espacial:
        - Piedra s0 en x=0  (CENTRO)
        - Piedra s1 en x=2  (VECINO)
        - Linea de tablero entre ellas
    """
    h   = H(s0, s1)
    ec  = hcolor(h)

    ax.set_facecolor(BOARD_C)
    ax.set_xlim(-0.8, 2.8)
    ax.set_ylim(-1.05, 1.75)
    ax.set_aspect('equal')
    ax.set_xticks([]); ax.set_yticks([])
    for sp in ax.spines.values():          # borde coloreado segun H
        sp.set_linewidth(3.5)
        sp.set_color(ec)

    # Segmento de tablero (linea horizontal + ticks verticales)
    ax.plot([0, 2], [0, 0], '-', color=GRID_C, lw=1.5, zorder=1)
    for xi in [0, 1, 2]:
        ax.plot([xi, xi], [-0.25, 0.25], '-', color=GRID_C, lw=0.8, alpha=0.6, zorder=1)

    # Piedras
    draw_stone(ax, 0, 0, s0)
    draw_stone(ax, 2, 0, s1)

    # Flecha de interaccion
    ax.annotate('', xy=(1.62, 0.0), xytext=(0.38, 0.0),
                arrowprops=dict(arrowstyle='<->', color='#555555', lw=1.2,
                                mutation_scale=12))

    # Etiquetas: spin y nombre de variable
    ax.text(0, 0.65,  r'$s_0$',        ha='center', fontsize=9,
            fontweight='bold', color='#1a1a1a')
    ax.text(2, 0.65,  r'$s_1$',        ha='center', fontsize=9, color='#555555')
    ax.text(0, 1.15,  SPIN_SHORT[s0],  ha='center', fontsize=15, color='#111111',
            fontweight='bold')
    ax.text(2, 1.15,  SPIN_SHORT[s1],  ha='center', fontsize=15, color='#444444')

    # Valor H con caja de color
    h_str = f'H = {int(h):+d}' if h == int(h) else f'H = {h:+.2f}'
    txt_c = '#FFFFFF' if abs(h) > 1.2 else '#111111'
    ax.text(1.0, -0.70, h_str,
            ha='center', va='center', fontsize=11, fontweight='bold',
            color=txt_c,
            bbox=dict(boxstyle='round,pad=0.35', fc=ec, ec='none', alpha=0.92))


# ─── Figura ───────────────────────────────────────────────────────────────────

def create_figure(out_png):
    fig = plt.figure(figsize=(19, 13), facecolor=BG)

    # Titulos globales
    fig.text(0.50, 0.982,
             'Interacciones Binarias — Hamiltoniano de Ising Clásico para Go',
             ha='center', fontsize=15, fontweight='bold', color='#1a1a1a')
    fig.text(0.50, 0.957,
             r'$H(s_0,\, s_1)\;=\;'
             r'h_0\,s_0 \;+\; h_1\,s_1 \;+\; K\,s_0\,s_1^2 \;+\; L\,s_0^2\,s_1$'
             r'$\quad$ con $\quad h_0=1,\; h_1=2,\; K=-1,\; L=-1$'
             r'$\qquad s_0,s_1 \in \{-1,\,0,\,+1\}$',
             ha='center', fontsize=11, color='#333333', style='italic')

    # Grid principal: 4 filas x 5 cols
    # col 0: etiqueta s0 | cols 1-3: celdas | col 4: paneles laterales
    # fila 0: etiquetas s1 | filas 1-3: celdas
    gs = gridspec.GridSpec(
        4, 5,
        left=0.07, right=0.99, top=0.935, bottom=0.03,
        wspace=0.07, hspace=0.10,
        width_ratios=[0.30, 1, 1, 1, 1.55],
        height_ratios=[0.28, 1, 1, 1],
    )

    # ── Etiqueta global de filas ─────────────────────────────────────────────
    fig.text(0.025, 0.55, 'CENTRO  ($s_0$)',
             ha='center', va='center', fontsize=11,
             fontweight='bold', color='#1a1a1a', rotation=90)

    # ── Etiqueta global de columnas ──────────────────────────────────────────
    fig.text(0.41, 0.958, 'VECINO  ($s_1$)',
             ha='center', fontsize=11, fontweight='bold', color='#1a1a1a')

    # ── Cabeceras de columnas (s1) ───────────────────────────────────────────
    for j, s1 in enumerate(SPIN_VALS):
        ax = fig.add_subplot(gs[0, j + 1])
        ax.set_facecolor('#EDE8DA')
        ax.set_xticks([]); ax.set_yticks([])
        for sp in ax.spines.values():
            sp.set_linewidth(1); sp.set_color('#CCBBAA')
        ax.set_xlim(-1.2, 1.2); ax.set_ylim(-0.6, 1.1)
        draw_stone(ax, 0, 0.15, s1, r=0.28)
        ax.text(0,  0.70, SPIN_LABEL[s1],
                ha='center', fontsize=9, fontweight='bold', color='#222222')
        ax.text(0, -0.35, f'$s_1 = {s1:+d}$' if s1 != 0 else r'$s_1 = 0$',
                ha='center', fontsize=8, color='#666666')

    # ── Cabeceras de filas (s0) ──────────────────────────────────────────────
    for i, s0 in enumerate(SPIN_VALS):
        ax = fig.add_subplot(gs[i + 1, 0])
        ax.set_facecolor('#EDE8DA')
        ax.set_xticks([]); ax.set_yticks([])
        for sp in ax.spines.values():
            sp.set_linewidth(1); sp.set_color('#CCBBAA')
        ax.set_xlim(-1.2, 1.2); ax.set_ylim(-0.9, 1.2)
        draw_stone(ax, 0, 0.0, s0, r=0.30)
        ax.text(0,  0.65, SPIN_LABEL[s0],
                ha='center', fontsize=8, fontweight='bold', color='#222222')
        ax.text(0, -0.55, f'$s_0 = {s0:+d}$' if s0 != 0 else r'$s_0 = 0$',
                ha='center', fontsize=8, color='#666666')

    # ── 3x3 celdas de interaccion ────────────────────────────────────────────
    for i, s0 in enumerate(SPIN_VALS):
        for j, s1 in enumerate(SPIN_VALS):
            ax = fig.add_subplot(gs[i + 1, j + 1])
            draw_cell(ax, s0, s1)

    # ── Paneles laterales ────────────────────────────────────────────────────
    gs_r = gridspec.GridSpecFromSubplotSpec(
        3, 1, subplot_spec=gs[:, 4],
        hspace=0.55, height_ratios=[1.1, 1.2, 0.9]
    )

    # Panel 1 — Mapa de calor
    ax_hm = fig.add_subplot(gs_r[0])
    im = ax_hm.imshow(H_tab, cmap='RdBu_r', vmin=-VMAX, vmax=VMAX, aspect='equal')
    ticks = ['●\n(−1)', '·\n(0)', '○\n(+1)']
    ax_hm.set_xticks([0, 1, 2]); ax_hm.set_xticklabels(ticks, fontsize=9)
    ax_hm.set_yticks([0, 1, 2]); ax_hm.set_yticklabels(ticks, fontsize=9)
    ax_hm.set_xlabel('Vecino $s_1$',  fontsize=9)
    ax_hm.set_ylabel('Centro $s_0$',  fontsize=9)
    ax_hm.set_title('Mapa de calor  $H(s_0, s_1)$',
                    fontsize=10, fontweight='bold', pad=5)
    for i in range(3):
        for j in range(3):
            h = H_tab[i, j]
            tc = 'white' if abs(h) > 1.2 else '#111111'
            ax_hm.text(j, i, f'{int(h):+d}', ha='center', va='center',
                       fontsize=16, fontweight='bold', color=tc)
    cb = plt.colorbar(im, ax=ax_hm, shrink=0.85, pad=0.02)
    cb.set_label('H', fontsize=9)

    # Panel 2 — Distribucion de valores H
    ax_d = fig.add_subplot(gs_r[1])
    ax_d.set_facecolor('#F5F5F5')
    uvals, ucounts = np.unique(H_tab.flatten(), return_counts=True)
    bcols = [hcolor(h) for h in uvals]
    bars  = ax_d.bar([f'{int(h):+d}' for h in uvals], ucounts,
                     color=bcols, edgecolor='white', lw=0.5, width=0.65)
    for bar, cnt in zip(bars, ucounts):
        ax_d.text(bar.get_x() + bar.get_width()/2,
                  bar.get_height() + 0.06, str(cnt),
                  ha='center', fontsize=11, fontweight='bold', color='#222222')
    ax_d.set_ylim(0, max(ucounts) * 1.35)
    ax_d.set_xlabel('Valor de H', fontsize=9)
    ax_d.set_ylabel('Veces que aparece\nen las 9 interacciones', fontsize=8)
    ax_d.set_title('Distribución de valores de $H$', fontsize=10, fontweight='bold')
    ax_d.grid(axis='y', alpha=0.3)
    ax_d.tick_params(labelsize=9)

    # Panel 3 — Entropia
    ax_e = fig.add_subplot(gs_r[2])
    ax_e.set_facecolor('#F0EEE8')
    ax_e.set_xticks([]); ax_e.set_yticks([])
    for sp in ax_e.spines.values():
        sp.set_linewidth(1); sp.set_color('#CCBBAA')

    abs_h  = np.abs(H_tab.flatten())
    total  = abs_h.sum()
    probs  = abs_h[abs_h > 0] / total
    S_val  = -np.sum(probs * np.log(probs))
    S_max  = np.log(8)      # 8 interacciones con H != 0

    lines = [
        (r'Entropía de Shannon', 10, 'bold',   '#1a1a1a'),
        (r'$p_i = |H_i|\,/\,\sum|H_j|$',  9,  'normal', '#444444'),
        (r'$S = -\sum_i p_i \ln p_i$',     9,  'normal', '#444444'),
        ('', 7, 'normal', 'white'),
        (fr'$S = {S_val:.4f}$ nats', 13, 'bold', '#1a3a6a'),
        ('', 7, 'normal', 'white'),
        (fr'$S_{{max}} = \ln(8) = {S_max:.4f}$', 8, 'normal', '#666666'),
        (fr'$S / S_{{max}} = {S_val/S_max:.3f}$', 8, 'normal', '#666666'),
    ]
    y = 0.96
    for txt, fs, fw, fc in lines:
        ax_e.text(0.5, y, txt, ha='center', va='top',
                  transform=ax_e.transAxes,
                  fontsize=fs, fontweight=fw, color=fc)
        y -= 0.135

    plt.savefig(out_png, dpi=150, bbox_inches='tight', facecolor=BG)
    print(f'PNG guardado: {out_png}')
    plt.close(fig)


# ─── Tabla de texto ───────────────────────────────────────────────────────────

def save_table_txt(out_txt):
    lines = [
        'TABLA DE INTERACCIONES BINARIAS — HAMILTONIANO DE ISING CLASICO',
        'H(s0, s1) = s0 + 2*s1 - s0*s1^2 - s0^2*s1',
        '  s0, s1 in {-1, 0, +1}  <->  {Negro(B), Vacio(.), Blanco(W)}',
        '=' * 68,
        '',
        f"{'Centro s0':>15} {'Vecino s1':>15} {'Tipo':>20} {'H':>6}",
        '-' * 68,
    ]
    types = {
        (-1,-1): 'Negro–Negro',
        (-1, 0): 'Negro–Vacío',
        (-1,+1): 'Negro–Blanco',
        ( 0,-1): 'Vacío–Negro',
        ( 0, 0): 'Vacío–Vacío',
        ( 0,+1): 'Vacío–Blanco',
        (+1,-1): 'Blanco–Negro',
        (+1, 0): 'Blanco–Vacío',
        (+1,+1): 'Blanco–Blanco',
    }
    for s0 in SPIN_VALS:
        for s1 in SPIN_VALS:
            h = H(s0, s1)
            lines.append(
                f"{SPIN_LABEL[s0]:>15} {SPIN_LABEL[s1]:>15} "
                f"{types[(s0,s1)]:>20} {int(h) if h==int(h) else h:>6}"
            )
    lines += [
        '',
        '=' * 68,
        'PROPIEDADES',
        f'  Antisimetria: H(-s0,-s1) = -H(s0,s1)  [demostrado algebraicamente]',
        f'  H(s0,s1) != H(s1,s0) en general  [h0=1 != h1=2]',
        '',
        'DISTRIBUCION DE VALORES:',
        f'  H = -2 : 1 vez   H = -1 : 3 veces   H = 0 : 1 vez',
        f'  H = +1 : 3 veces   H = +2 : 1 vez',
        '',
        'ENTROPIA DE SHANNON (p_i = |H_i|/sum|H_j|):',
    ]
    abs_h = np.abs(np.array([H(s0,s1) for s0 in SPIN_VALS for s1 in SPIN_VALS]))
    total = abs_h.sum()
    probs = abs_h[abs_h > 0] / total
    S_val = -np.sum(probs * np.log(probs))
    lines += [
        f'  sum|H_i| = {int(total)}',
        f'  p(|H|=2) = 2/10 = 0.20   (aparece 2 veces)',
        f'  p(|H|=1) = 1/10 = 0.10   (aparece 6 veces)',
        f'  p(|H|=0) = 0              (no contribuye)',
        f'  S = {S_val:.6f} nats',
        f'  S_max = ln(8) = {np.log(8):.6f} nats',
        f'  S/S_max = {S_val/np.log(8):.4f}',
    ]
    with open(out_txt, 'w', encoding='utf-8') as f:
        f.write('\n'.join(lines))
    print(f'TXT guardado: {out_txt}')


# ─── Main ─────────────────────────────────────────────────────────────────────

if __name__ == '__main__':
    create_figure(os.path.join(RESULTS, 'interactions_H.png'))
    save_table_txt(os.path.join(RESULTS, 'interactions_H.txt'))
    print('Listo.')
