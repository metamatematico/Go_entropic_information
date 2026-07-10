"""
viz_interaction_comparison.py
==============================
Tabla de interaccion binaria (un bono i->j) vista desde 4 angulos:
  1. Mapas de calor 3x3 — nuestro modelo y Alvarado
  2. Matriz de diferencias (nuestro - Alvarado)
  3. Grafico de barras — los 9 pares lado a lado
  4. Grafos de nodos — flechas coloreadas por energia

Salida: results/interaction_comparison.png
"""
import os, sys, math
from pathlib import Path
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.gridspec as gridspec
from matplotlib.patches import FancyArrowPatch, Circle, FancyBboxPatch
import matplotlib.patches as mpatches

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from src.go_ising_classical import IsingGoConfig, ClassicalIsingModel

RESULTS = os.path.join(str(Path(__file__).resolve().parents[2]), 'results')
os.makedirs(RESULTS, exist_ok=True)

BG     = '#FAFAF8'
CONFIG = IsingGoConfig()
MODEL  = ClassicalIsingModel(manhattan_distance=1)

SPINS = [-1, 0, +1]
SYMB  = {-1: '●', 0: '·', +1: '○'}   # ●  ·  ○
SNAME = {-1: 'Negro (−1)', 0: 'Vacío (0)', +1: 'Blanco (+1)'}

# Colores por valor de energia
ECOL = {-2: '#1848c4', -1: '#5ba4f5', 0: '#DCDCDC', +1: '#f58b5b', +2: '#c41818'}
ELW  = {-2: 4.0, -1: 2.5, 0: 0.6, +1: 2.5, +2: 4.0}
EALP = {-2: 0.92, -1: 0.87, 0: 0.22, +1: 0.87, +2: 0.92}

# Colores de los nodos
N_FC = {-1: '#111111', 0: '#C8C8C8', +1: '#F0F0F0'}
N_EC = {-1: '#000000', 0: '#777777', +1: '#333333'}
N_TC = {-1: 'white',   0: '#111111', +1: '#111111'}


def H_our(s0, s1):
    return MODEL._hamiltonian(s0, s1, MODEL.params)

def H_alv(s0, s1):
    return float(s0 * s1)

def vi(h): return int(round(h))
def vs(h):
    v = vi(h)
    return f'{v:+d}' if v != 0 else '0'

# Matrices
MA = np.array([[H_our(s0, s1) for s1 in SPINS] for s0 in SPINS])
MB = np.array([[H_alv(s0, s1) for s1 in SPINS] for s0 in SPINS])
MD = MA - MB


# ─────────────────────────────────────────────────────────────────────────────
# 1. HEATMAP 3x3
# ─────────────────────────────────────────────────────────────────────────────

def draw_heatmap(ax, matrix, ref_matrix, title, formula, mark_diff=False):
    """
    Dibuja una matriz 3x3 coloreada.
    mark_diff=True: marca con borde violeta las celdas donde matrix != ref_matrix.
    """
    ax.set_facecolor(BG)
    ax.set_xlim(-1.1, 3.6)
    ax.set_ylim(-0.7, 3.6)
    ax.set_aspect('equal')
    ax.axis('off')

    # Titulo y formula
    ax.text(1.0, 3.45, title, ha='center', va='top',
            fontsize=11, fontweight='bold', color='#111')
    ax.text(1.0, 3.10, formula, ha='center', va='top',
            fontsize=8.5, color='#555', style='italic')

    # Flecha "destino →"
    ax.annotate('', xy=(2.65, 2.72), xytext=(-0.65, 2.72),
                arrowprops=dict(arrowstyle='->', color='#999', lw=1.2))
    ax.text(1.0, 2.82, 'destino  (sⱼ)', ha='center', va='bottom',
            fontsize=7.5, color='#888')

    # Flecha "origen ↑"
    ax.annotate('', xy=(-0.85, 2.55), xytext=(-0.85, -0.45),
                arrowprops=dict(arrowstyle='->', color='#999', lw=1.2))
    ax.text(-1.0, 1.05, 'origen\n(sᵢ)', ha='center', va='center',
            fontsize=7.5, color='#888', multialignment='center')

    # Etiquetas de columna (s_j)
    for ci, s1 in enumerate(SPINS):
        fc = N_FC[s1]; ec = N_EC[s1]; tc = N_TC[s1]
        circ = Circle((ci, 2.55), 0.22, fc=fc, ec=ec, lw=1.5, zorder=5)
        ax.add_patch(circ)
        ax.text(ci, 2.55, SYMB[s1], ha='center', va='center',
                fontsize=13, fontweight='bold', color=tc, zorder=6)

    # Etiquetas de fila (s_i)
    for ri, s0 in enumerate(SPINS):
        fc = N_FC[s0]; ec = N_EC[s0]; tc = N_TC[s0]
        circ = Circle((-0.65, 2 - ri), 0.22, fc=fc, ec=ec, lw=1.5, zorder=5)
        ax.add_patch(circ)
        ax.text(-0.65, 2 - ri, SYMB[s0], ha='center', va='center',
                fontsize=13, fontweight='bold', color=tc, zorder=6)

    # Celdas
    for ri, s0 in enumerate(SPINS):
        for ci, s1 in enumerate(SPINS):
            h  = matrix[ri, ci]
            v  = vi(h)
            fc = ECOL.get(v, '#CCCCCC')

            diff_here = mark_diff and (vi(ref_matrix[ri, ci]) != v)

            ec_cell = '#7C3AED' if diff_here else 'white'
            lw_cell = 2.5 if diff_here else 1.2

            cell = FancyBboxPatch((ci - 0.44, 2 - ri - 0.44), 0.88, 0.88,
                                  boxstyle='round,pad=0.06',
                                  fc=fc, ec=ec_cell, lw=lw_cell,
                                  alpha=0.88, zorder=2)
            ax.add_patch(cell)

            tc = 'white' if v in (-2, -1) else ('#1a1a1a' if v != 0 else '#999')
            ax.text(ci, 2 - ri, vs(h), ha='center', va='center',
                    fontsize=16, fontweight='bold', color=tc, zorder=3)

            # Marca de asimetria dentro del mismo modelo
            h_rev = vi(matrix[SPINS.index(s1), SPINS.index(s0)])
            if s0 != s1 and h_rev != v:
                ax.text(ci + 0.36, 2 - ri + 0.36, '≠',
                        ha='center', va='center', fontsize=7,
                        color='#7C3AED', fontweight='bold', zorder=4)

    # Leyenda de asimetria (solo si hay)
    asym = any(vi(matrix[i, j]) != vi(matrix[j, i])
               for i in range(3) for j in range(3) if i != j)
    if asym:
        ax.text(1.0, -0.55, '≠  celda asimetrica: H(i→j) ≠ H(j→i)',
                ha='center', va='top', fontsize=7, color='#7C3AED', style='italic')


def draw_diff_heatmap(ax, diff_matrix):
    """Matriz de diferencias (nuestro - Alvarado), coloreada por signo."""
    ax.set_facecolor(BG)
    ax.set_xlim(-1.1, 3.6)
    ax.set_ylim(-0.7, 3.6)
    ax.set_aspect('equal')
    ax.axis('off')

    ax.text(1.0, 3.45, 'Diferencia', ha='center', va='top',
            fontsize=11, fontweight='bold', color='#111')
    ax.text(1.0, 3.10, 'Nuestro modelo − Alvarado', ha='center', va='top',
            fontsize=8.5, color='#555', style='italic')

    for ci, s1 in enumerate(SPINS):
        fc = N_FC[s1]; ec = N_EC[s1]; tc = N_TC[s1]
        circ = Circle((ci, 2.55), 0.22, fc=fc, ec=ec, lw=1.5, zorder=5)
        ax.add_patch(circ)
        ax.text(ci, 2.55, SYMB[s1], ha='center', va='center',
                fontsize=13, fontweight='bold', color=tc, zorder=6)
    for ri, s0 in enumerate(SPINS):
        fc = N_FC[s0]; ec = N_EC[s0]; tc = N_TC[s0]
        circ = Circle((-0.65, 2 - ri), 0.22, fc=fc, ec=ec, lw=1.5, zorder=5)
        ax.add_patch(circ)
        ax.text(-0.65, 2 - ri, SYMB[s0], ha='center', va='center',
                fontsize=13, fontweight='bold', color=tc, zorder=6)

    DIFF_COL = {
        -3: '#0a2a8c', -2: '#1848c4', -1: '#5ba4f5',
         0: '#DCDCDC',
        +1: '#f58b5b', +2: '#c41818', +3: '#7a0a0a',
    }
    for ri in range(3):
        for ci in range(3):
            d  = vi(diff_matrix[ri, ci])
            fc = DIFF_COL.get(d, '#CCCCCC')
            cell = FancyBboxPatch((ci - 0.44, 2 - ri - 0.44), 0.88, 0.88,
                                  boxstyle='round,pad=0.06',
                                  fc=fc, ec='white', lw=1.2,
                                  alpha=0.88, zorder=2)
            ax.add_patch(cell)
            tc = 'white' if abs(d) >= 1 else '#999'
            label = f'{d:+d}' if d != 0 else '0'
            ax.text(ci, 2 - ri, label, ha='center', va='center',
                    fontsize=16, fontweight='bold', color=tc, zorder=3)

    ax.text(1.0, -0.55,
            'Azul: nuestro modelo menor  |  Rojo: nuestro modelo mayor  |  Gris: iguales',
            ha='center', va='top', fontsize=7, color='#555', style='italic')


# ─────────────────────────────────────────────────────────────────────────────
# 2. GRAFICO DE BARRAS
# ─────────────────────────────────────────────────────────────────────────────

def draw_bars(ax):
    pairs  = [(s0, s1) for s0 in SPINS for s1 in SPINS]
    labels = [f'{SYMB[s0]}→{SYMB[s1]}' for s0, s1 in pairs]
    vA     = [H_our(s0, s1) for s0, s1 in pairs]
    vB     = [H_alv(s0, s1) for s0, s1 in pairs]

    x  = np.arange(len(pairs))
    w  = 0.35

    ax.set_facecolor('#F4F4F2')
    barsA = ax.bar(x - w/2, vA, width=w, color='#1D4ED8', alpha=0.85,
                   label='Nuestro modelo M1', edgecolor='white', lw=0.6)
    barsB = ax.bar(x + w/2, vB, width=w, color='#D97706', alpha=0.85,
                   label='Alvarado Atomic-Go', edgecolor='white', lw=0.6)

    ax.axhline(0, color='#333', lw=1.4)
    ax.set_xticks(x)
    ax.set_xticklabels(labels, fontsize=11, fontweight='bold')
    ax.set_ylabel('Energía del bono  H(s_i, s_j)', fontsize=9.5)
    ax.set_yticks([-2, -1, 0, 1, 2])
    ax.set_ylim(-2.6, 2.8)
    ax.grid(axis='y', alpha=0.3, lw=0.8)
    ax.legend(fontsize=9.5, loc='upper right', framealpha=0.9)
    ax.set_title('Valor de energía para cada par de celdas vecinas',
                 fontsize=10.5, fontweight='bold', pad=6)

    # Etiquetas de valor
    for bar, v in zip(barsA, vA):
        if v != 0:
            ax.text(bar.get_x() + bar.get_width()/2,
                    v + (0.06 if v > 0 else -0.12),
                    f'{int(v):+d}', ha='center', fontsize=8,
                    fontweight='bold', color='#1D4ED8',
                    va='bottom' if v > 0 else 'top')
    for bar, v in zip(barsB, vB):
        if v != 0:
            ax.text(bar.get_x() + bar.get_width()/2,
                    v + (0.06 if v > 0 else -0.12),
                    f'{int(v):+d}', ha='center', fontsize=8,
                    fontweight='bold', color='#D97706',
                    va='bottom' if v > 0 else 'top')

    # Zonas de fondo por tipo de par
    zone_colors = ['#E8EEF8', '#EEF3EE', '#F8EEE8']
    zone_labels = ['Pares con Negro (●)', 'Pares con Vacío (·)', 'Pares con Blanco (○)']
    for k in range(3):
        ax.axvspan(k*3 - 0.5, k*3 + 2.5, alpha=0.25,
                   color=zone_colors[k], zorder=0)
        ax.text(k*3 + 1, 2.55, zone_labels[k],
                ha='center', va='bottom', fontsize=7.5,
                color='#777', style='italic')

    for sp in ['top', 'right']:
        ax.spines[sp].set_visible(False)


# ─────────────────────────────────────────────────────────────────────────────
# 3. GRAFO DE NODOS
# ─────────────────────────────────────────────────────────────────────────────

def _node_pos():
    cx, cy, r = 3.5, 2.8, 2.0
    return {
        -1: np.array([cx - r*math.sin(math.pi/3), cy + r*math.cos(math.pi/3)]),
         0: np.array([cx,                          cy - r]),
        +1: np.array([cx + r*math.sin(math.pi/3), cy + r*math.cos(math.pi/3)]),
    }

NODE_R = 0.40
POS    = _node_pos()

def draw_self_loop(ax, s, h):
    v     = vi(h)
    color = ECOL.get(v, '#888')
    lw    = ELW.get(v, 0.8)
    alpha = EALP.get(v, 0.3)
    pos   = POS[s]
    loop_dir = {
        -1: np.array([-0.70, 0.65]),
         0: np.array([ 0.00,-0.95]),
        +1: np.array([ 0.70, 0.65]),
    }[s]
    ld   = loop_dir / np.linalg.norm(loop_dir)
    ctr  = pos + loop_dir * 0.50
    r    = 0.30

    circ = plt.Circle(ctr, r, fill=False, ec=color, lw=lw, alpha=alpha, zorder=3)
    ax.add_patch(circ)

    ang   = math.atan2(loop_dir[1], loop_dir[0])
    tip_a = ctr + r * np.array([math.cos(ang+0.32), math.sin(ang+0.32)])
    tip_b = ctr + r * np.array([math.cos(ang+0.05), math.sin(ang+0.05)])
    ax.annotate('', xy=tip_a, xytext=tip_b,
                arrowprops=dict(arrowstyle='->', color=color, lw=max(lw*0.6, 0.7)),
                zorder=4)

    if v != 0:
        lpos = ctr + ld * (r + 0.28)
        fc_l = 'white' if v in (-2, -1) else BG
        ax.text(lpos[0], lpos[1], vs(h), ha='center', va='center',
                fontsize=9.5, fontweight='bold', color=color, zorder=6,
                bbox=dict(boxstyle='round,pad=0.18', fc=fc_l, ec=color, lw=0.9))

def draw_edge(ax, s0, s1, h):
    v     = vi(h)
    color = ECOL.get(v, '#888')
    lw    = ELW.get(v, 0.6)
    alpha = EALP.get(v, 0.25)

    p0, p1 = POS[s0].copy(), POS[s1].copy()
    dv  = p1 - p0
    dn  = np.linalg.norm(dv)
    du  = dv / dn
    st  = p0 + du * NODE_R
    en  = p1 - du * NODE_R
    rad = 0.28 if s0 < s1 else -0.28

    arrow = FancyArrowPatch(
        st, en,
        arrowstyle='->', mutation_scale=12,
        connectionstyle=f'arc3,rad={rad}',
        color=color, lw=lw, alpha=alpha,
        shrinkA=0, shrinkB=0, zorder=3,
    )
    ax.add_patch(arrow)

    perp = np.array([-du[1], du[0]])
    mid  = (st + en) / 2 + perp * dn * rad * 0.42
    lpos = mid + perp * (0.28 if rad < 0 else -0.28)

    if v != 0:
        fc_l = 'white' if v in (-2, -1) else BG
        ax.text(lpos[0], lpos[1], vs(h), ha='center', va='center',
                fontsize=9.5, fontweight='bold', color=color, zorder=7,
                bbox=dict(boxstyle='round,pad=0.17', fc=fc_l, ec=color, lw=0.9))
    else:
        ax.text(lpos[0], lpos[1], '0', ha='center', va='center',
                fontsize=7.5, color='#BBBBBB', alpha=0.6, zorder=7)

def draw_graph(ax, func, title, formula):
    ax.set_facecolor(BG)
    ax.set_xlim(0.0, 7.0)
    ax.set_ylim(-0.3, 5.6)
    ax.set_aspect('equal')
    ax.axis('off')

    ax.text(3.5, 5.45, title, ha='center', va='top',
            fontsize=11, fontweight='bold', color='#111')
    ax.text(3.5, 5.05, formula, ha='center', va='top',
            fontsize=8.5, color='#555', style='italic')

    for s0 in SPINS:
        for s1 in SPINS:
            if s0 != s1:
                draw_edge(ax, s0, s1, func(s0, s1))
    for s in SPINS:
        draw_self_loop(ax, s, func(s, s))

    for s in SPINS:
        pos = POS[s]
        ax.add_patch(plt.Circle(pos + np.array([0.05,-0.05]), NODE_R,
                                fc='#00000018', ec='none', zorder=4))
        ax.add_patch(plt.Circle(pos, NODE_R, fc=N_FC[s], ec=N_EC[s],
                                lw=2.2, zorder=5))
        ax.text(pos[0], pos[1]+0.04, SYMB[s], ha='center', va='center',
                fontsize=20, fontweight='bold', color=N_TC[s], zorder=6)
        ax.text(pos[0], pos[1]-NODE_R-0.14, SNAME[s],
                ha='center', va='top', fontsize=7.5, color='#444',
                multialignment='center', zorder=6)


# ─────────────────────────────────────────────────────────────────────────────
# FIGURA PRINCIPAL
# ─────────────────────────────────────────────────────────────────────────────

def main():
    fig = plt.figure(figsize=(19, 15), facecolor=BG)

    gs = gridspec.GridSpec(
        3, 3,
        height_ratios=[1.55, 1.0, 1.55],
        hspace=0.32, wspace=0.10,
        left=0.04, right=0.97,
        top=0.93, bottom=0.05,
    )

    ax_hA   = fig.add_subplot(gs[0, 0])   # heatmap nuestro
    ax_hB   = fig.add_subplot(gs[0, 1])   # heatmap alvarado
    ax_hD   = fig.add_subplot(gs[0, 2])   # diferencia
    ax_bars = fig.add_subplot(gs[1, :])   # barras (ancho completo)
    ax_gA   = fig.add_subplot(gs[2, 0:2]) # grafo nuestro (mas ancho)
    ax_gB   = fig.add_subplot(gs[2, 2])   # grafo alvarado

    # ── Titulo global
    fig.suptitle(
        'Interaccion Binaria por Bono  (sᵢ → sⱼ)\n'
        'Cuatro representaciones de la misma tabla',
        fontsize=15, fontweight='bold', y=0.97
    )

    # ── Heatmaps
    draw_heatmap(ax_hA, MA, MB,
                 'Nuestro Modelo M1',
                 'H = sᵢ + 2sⱼ − sᵢsⱼ² − sᵢ²sⱼ',
                 mark_diff=False)

    draw_heatmap(ax_hB, MB, MA,
                 'Atomic-Go  (Alvarado 2019)',
                 'H = xᵢ · xⱼ',
                 mark_diff=False)

    draw_diff_heatmap(ax_hD, MD)

    # ── Barras
    draw_bars(ax_bars)

    # ── Grafos
    draw_graph(ax_gA, H_our,
               'Nuestro Modelo M1',
               'H(sᵢ, sⱼ) = sᵢ + 2sⱼ − sᵢsⱼ² − sᵢ²sⱼ')

    draw_graph(ax_gB, H_alv,
               'Atomic-Go  (Alvarado)',
               'H(xᵢ, xⱼ) = xᵢ · xⱼ')

    # ── Leyenda global de colores
    handles = [
        mpatches.Patch(fc='#c41818', label='+2  Repulsion fuerte'),
        mpatches.Patch(fc='#f58b5b', label='+1  Repulsion debil'),
        mpatches.Patch(fc='#DCDCDC', label=' 0   Sin interaccion'),
        mpatches.Patch(fc='#5ba4f5', label='−1  Atraccion debil'),
        mpatches.Patch(fc='#1848c4', label='−2  Atraccion fuerte'),
        mpatches.Patch(fc='white', ec='#7C3AED', lw=2,
                       label='≠  asimetrico H(i→j) ≠ H(j→i)'),
    ]
    fig.legend(handles=handles, loc='lower center', ncol=6,
               fontsize=9.5, bbox_to_anchor=(0.5, 0.0),
               frameon=True, framealpha=0.95, edgecolor='#ccc')

    out = os.path.join(RESULTS, 'interaction_comparison.png')
    plt.savefig(out, dpi=150, bbox_inches='tight', facecolor=BG)
    print(f'Guardado: {out}')
    plt.close(fig)


if __name__ == '__main__':
    main()
