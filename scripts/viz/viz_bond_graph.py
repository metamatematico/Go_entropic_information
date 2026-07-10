"""
viz_bond_graph.py — Grafo de interacción por bono
===================================================
Visualización tipo red: 3 nodos (●, ·, ○) con flechas
coloreadas por energía. Hace inmediatamente visible:
  1. Alvarado: el Vacío (·) no interactúa con nadie
  2. Nuestro modelo: asimetría (●→○ ≠ ○→●)
  3. Comparación directa de ambos modelos
"""
import os, sys, math
from pathlib import Path
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import matplotlib.gridspec as gridspec
from matplotlib.patches import FancyArrowPatch, Circle, Rectangle

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from src.go_ising_classical import IsingGoConfig, ClassicalIsingModel

RESULTS = os.path.join(str(Path(__file__).resolve().parents[2]), 'results')
os.makedirs(RESULTS, exist_ok=True)

BG     = '#F9F6EE'
CONFIG = IsingGoConfig()
MODEL  = ClassicalIsingModel(manhattan_distance=1)

SPINS = [-1, 0, +1]
SYMB  = {-1: '●', 0: '·', +1: '○'}
N_LBL = {-1: 'Negro\n(−1)', 0: 'Vacío\n(0)', +1: 'Blanco\n(+1)'}

# Node visual properties
N_FC = {-1: '#111111', 0: '#CCCCCC', +1: '#F0F0F0'}
N_EC = {-1: '#000000', 0: '#777777', +1: '#333333'}
N_TC = {-1: 'white',   0: '#111111', +1: '#111111'}

# Energy → color / width / alpha
ECOL = {
    -2: '#1848c4',   # fuerte atracción (azul oscuro)
    -1: '#5ba4f5',   # débil atracción  (azul claro)
     0: '#C0C0C0',   # sin interacción  (gris)
    +1: '#f58b5b',   # débil repulsión  (rojo claro)
    +2: '#c41818',   # fuerte repulsión (rojo oscuro)
}
ELW  = {-2: 4.0, -1: 2.5, 0: 0.5, +1: 2.5, +2: 4.0}
EALP = {-2: 0.92, -1: 0.87, 0: 0.25, +1: 0.87, +2: 0.92}

# Node positions (data coords)  — triángulo equilátero
_cx, _cy = 3.5, 2.9
_r = 2.2
POS = {
    -1: np.array([_cx - _r * math.sin(math.pi/3),  _cy + _r * math.cos(math.pi/3)]),
     0: np.array([_cx,                              _cy - _r]),
    +1: np.array([_cx + _r * math.sin(math.pi/3),  _cy + _r * math.cos(math.pi/3)]),
}
NODE_R = 0.44


# ── helpers ──────────────────────────────────────────────────────────────────

def H_our(s0, s1):
    """Energía de bono en nuestro modelo (coef=1 a d=1)."""
    return MODEL._hamiltonian(s0, s1, MODEL.params)

def H_alv(s0, s1):
    """Energía de bono en Alvarado."""
    return float(s0 * s1)

def vi(h):
    """Redondea a entero de energía."""
    return int(round(h))

def vs(h):
    """String de energía con signo."""
    v = vi(h)
    return f'{v:+d}' if v != 0 else '0'


# ── componentes de dibujo ─────────────────────────────────────────────────────

def draw_self_loop(ax, s, h):
    v = vi(h)
    color = ECOL.get(v, '#888')
    lw    = ELW.get(v, 1.0)
    alpha = EALP.get(v, 0.5)

    pos = POS[s]
    loop_dir = {
        -1: np.array([-0.75, 0.70]),
         0: np.array([ 0.00,-1.00]),
        +1: np.array([ 0.75, 0.70]),
    }[s]
    ld_norm = loop_dir / np.linalg.norm(loop_dir)
    center  = pos + loop_dir * 0.52
    r       = 0.34

    # Loop circle
    circle = Circle(center, r, fill=False, ec=color, lw=lw, alpha=alpha, zorder=3)
    ax.add_patch(circle)

    # Tiny arrowhead on loop
    ang = math.atan2(loop_dir[1], loop_dir[0])
    tip_a = center + r * np.array([math.cos(ang + 0.30), math.sin(ang + 0.30)])
    tip_b = center + r * np.array([math.cos(ang + 0.02), math.sin(ang + 0.02)])
    ax.annotate('', xy=tip_a, xytext=tip_b,
                arrowprops=dict(arrowstyle='->', color=color, lw=max(lw*0.6, 0.8)),
                zorder=4)

    # Energy label
    lpos = center + ld_norm * (r + 0.30)
    fc_label = 'white' if v in (-2, -1) else BG
    tc_label = color
    ax.text(lpos[0], lpos[1], vs(h), ha='center', va='center',
            fontsize=10, fontweight='bold', color=tc_label, zorder=6,
            bbox=dict(boxstyle='round,pad=0.20', fc=fc_label, ec=color, lw=1.0))


def draw_edge(ax, s0, s1, h):
    v     = vi(h)
    color = ECOL.get(v, '#888')
    lw    = ELW.get(v, 0.8)
    alpha = EALP.get(v, 0.3)

    p0, p1 = POS[s0].copy(), POS[s1].copy()
    dv = p1 - p0
    dn = np.linalg.norm(dv)
    du = dv / dn

    # Move start/end to node boundary
    start = p0 + du * NODE_R
    end   = p1 - du * NODE_R

    # Curvature: s0 < s1 → curve one way, s0 > s1 → other way (no overlap)
    rad = 0.30 if s0 < s1 else -0.30

    arrow = FancyArrowPatch(
        start, end,
        arrowstyle='->', mutation_scale=13,
        connectionstyle=f'arc3,rad={rad}',
        color=color, lw=lw, alpha=alpha,
        shrinkA=0, shrinkB=0, zorder=3,
    )
    ax.add_patch(arrow)

    # Label: place perpendicular to midpoint, offset by arc bend
    perp = np.array([-du[1], du[0]])
    mid  = (start + end) / 2 + perp * dn * rad * 0.42
    # Shift label outward from midpoint
    lpos = mid + perp * (0.30 if rad < 0 else -0.30)

    if v != 0:
        fc_l = 'white' if v in (-2, -1) else BG
        ax.text(lpos[0], lpos[1], vs(h), ha='center', va='center',
                fontsize=10, fontweight='bold', color=color, zorder=7,
                bbox=dict(boxstyle='round,pad=0.18', fc=fc_l, ec=color, lw=1.0))
    else:
        ax.text(lpos[0], lpos[1], '0', ha='center', va='center',
                fontsize=8, color='#AAAAAA', alpha=0.55, zorder=7)


def draw_graph(ax, func, title, formula):
    ax.set_facecolor(BG)
    ax.set_xlim(0.0, 7.0)
    ax.set_ylim(-0.2, 5.8)
    ax.set_aspect('equal')
    ax.axis('off')

    # Title
    ax.text(3.5, 5.65, title, ha='center', va='top',
            fontsize=12.5, fontweight='bold', color='#1a1a1a')
    ax.text(3.5, 5.20, formula, ha='center', va='top',
            fontsize=8.5, color='#555555', style='italic')

    # Edges (under nodes)
    for s0 in SPINS:
        for s1 in SPINS:
            if s0 != s1:
                draw_edge(ax, s0, s1, func(s0, s1))
    for s in SPINS:
        draw_self_loop(ax, s, func(s, s))

    # Nodes (on top)
    for s in SPINS:
        pos = POS[s]
        # Shadow
        ax.add_patch(Circle(pos + np.array([0.05, -0.05]), NODE_R,
                            fc='#00000018', ec='none', zorder=4))
        ax.add_patch(Circle(pos, NODE_R, fc=N_FC[s], ec=N_EC[s],
                            lw=2.5, zorder=5))
        ax.text(pos[0], pos[1] + 0.04, SYMB[s], ha='center', va='center',
                fontsize=22, fontweight='bold', color=N_TC[s], zorder=6)
        ax.text(pos[0], pos[1] - NODE_R - 0.13, N_LBL[s],
                ha='center', va='top', fontsize=8, color='#444',
                multialignment='center', zorder=6)


# ── matriz 3×3 como inset ────────────────────────────────────────────────────

def draw_matrix(ax, func, label_col='#333'):
    """Mini heatmap 3×3 dentro de un eje ya existente."""
    ax.set_facecolor(BG)
    ax.axis('off')
    ax.set_xlim(0, 1); ax.set_ylim(0, 1)

    cw, ch = 0.22, 0.26    # cell width/height (normalizado 0-1)
    ox, oy = 0.28, 0.10    # origin (esquina inferior izquierda de la grilla)

    # Encabezados
    ax.text(0.5, 0.98, 'Tabla de energías  (fila = origen  s_i,  columna = destino  s_j)',
            ha='center', va='top', fontsize=8.5, fontweight='bold',
            color=label_col, transform=ax.transAxes)

    for ci, s1 in enumerate(SPINS):
        x = ox + cw * (ci + 0.5)
        y = oy + ch * 3 + 0.04
        ax.text(x, y, SYMB[s1], ha='center', va='bottom',
                fontsize=14, fontweight='bold', color=N_FC[s1],
                transform=ax.transAxes,
                bbox=dict(boxstyle='circle,pad=0.2', fc=N_EC[s1], ec='none'))
        ax.text(x, oy + ch*3 + 0.17, f'({SPINS[ci]:+d})',
                ha='center', va='bottom', fontsize=7, color='#777',
                transform=ax.transAxes)

    for ri, s0 in enumerate(SPINS):
        y = oy + ch * (2 - ri + 0.5)
        ax.text(ox - 0.05, y, SYMB[s0], ha='center', va='center',
                fontsize=14, fontweight='bold', color=N_FC[s0],
                transform=ax.transAxes,
                bbox=dict(boxstyle='circle,pad=0.2', fc=N_EC[s0], ec='none'))
        for ci, s1 in enumerate(SPINS):
            h = func(s0, s1)
            v = vi(h)
            x = ox + cw * ci
            y = oy + ch * (2 - ri)
            fc = ECOL.get(v, '#888')
            tc = 'white' if v in (-2, -1) else ('#111' if v != 0 else '#888')

            rect = Rectangle((x, y), cw * 0.92, ch * 0.88,
                              transform=ax.transAxes,
                              fc=fc, ec='white', lw=1.2, alpha=0.80, zorder=2)
            ax.add_patch(rect)
            ax.text(x + cw*0.46, y + ch*0.44, vs(h),
                    ha='center', va='center',
                    fontsize=11, fontweight='bold', color=tc,
                    transform=ax.transAxes, zorder=3)

            # Marca ≠ si hay asimetría con el par inverso
            h_inv = func(s1, s0)
            if abs(h - h_inv) > 0.01 and s0 != s1:
                ax.text(x + cw*0.86, y + ch*0.78, '≠',
                        ha='center', va='center', fontsize=7,
                        color='#7C3AED', fontweight='bold',
                        transform=ax.transAxes, zorder=4)

    # Etiquetas de ejes
    ax.text(ox + cw*1.5, oy + ch*3 + 0.30, '⟶  destino (s_j)',
            ha='center', va='bottom', fontsize=7.5, color='#666',
            transform=ax.transAxes)
    ax.text(ox - 0.18, oy + ch*1.5, '↑\norigen\n(s_i)',
            ha='center', va='center', fontsize=7, color='#666',
            multialignment='center', transform=ax.transAxes)


# ── figura principal ──────────────────────────────────────────────────────────

def main():
    fig = plt.figure(figsize=(17, 11), facecolor=BG)
    gs  = gridspec.GridSpec(
        2, 2,
        height_ratios=[2.6, 1.0],
        hspace=0.08, wspace=0.04,
        left=0.02, right=0.98, top=0.93, bottom=0.09,
    )

    ax_gA = fig.add_subplot(gs[0, 0])   # grafo nuestro modelo
    ax_gB = fig.add_subplot(gs[0, 1])   # grafo Alvarado
    ax_mA = fig.add_subplot(gs[1, 0])   # matriz nuestro modelo
    ax_mB = fig.add_subplot(gs[1, 1])   # matriz Alvarado

    # ── Grafos ────────────────────────────────────────────────────────────────
    draw_graph(ax_gA, H_our,
               'Nuestro Modelo M1',
               r'$H(s_i, s_j) = s_i + 2s_j - s_i\,s_j^2 - s_i^2\,s_j$')

    draw_graph(ax_gB, H_alv,
               'Atomic-Go  (Alvarado 2019)',
               r'$H(x_i, x_j) = x_i \cdot x_j$')

    # ── Matrices ──────────────────────────────────────────────────────────────
    draw_matrix(ax_mA, H_our)
    draw_matrix(ax_mB, H_alv)

    # ── Título global ─────────────────────────────────────────────────────────
    fig.suptitle(
        '¿Cómo interactúa un par de celdas vecinas?\n'
        'Cada flecha = un bono  i → j  (una interacción binaria independiente)',
        fontsize=14, fontweight='bold', y=0.99
    )

    # ── Leyenda de colores ────────────────────────────────────────────────────
    legend_handles = [
        mpatches.Patch(fc='#c41818', label='+2  Repulsión fuerte'),
        mpatches.Patch(fc='#f58b5b', label='+1  Repulsión débil'),
        mpatches.Patch(fc='#C0C0C0', label=' 0   Sin interacción'),
        mpatches.Patch(fc='#5ba4f5', label='−1  Atracción débil'),
        mpatches.Patch(fc='#1848c4', label='−2  Atracción fuerte'),
    ]
    fig.legend(handles=legend_handles, loc='lower center', ncol=5,
               fontsize=10, bbox_to_anchor=(0.5, 0.00),
               frameon=True, framealpha=0.95, edgecolor='#ccc')

    # ── Observaciones clave ───────────────────────────────────────────────────
    obs = (
        '(1)  Vacio (\xb7) en Alvarado: no hay flechas coloreadas desde/hacia \xb7  →  el Vacio es INVISIBLE para Alvarado\n'
        '(2)  Nuestro modelo es ASIMETRICO (violeta ≠): ●→○ = +1 (rojo) pero ○→● = −1 (azul)  |  '
        'Alvarado es SIMETRICO: x·y = y·x siempre\n'
        '(3)  Nuestro modelo tiene 5 valores posibles: {−2, −1, 0, +1, +2}  |  Alvarado solo tiene 3: {−1, 0, +1}'
    )
    fig.text(0.50, 0.065, obs, ha='center', va='top', fontsize=8.5,
             color='#1a1a1a', multialignment='center',
             bbox=dict(boxstyle='round,pad=0.5', fc='#FFFDE7', ec='#CCBB22', lw=1.2))

    out = os.path.join(RESULTS, 'bond_interaction_graph.png')
    plt.savefig(out, dpi=150, bbox_inches='tight', facecolor=BG)
    print(f'Guardado: {out}')
    plt.close(fig)

    # Verificación numérica en consola
    print('\nMatriz de energias -- Nuestro modelo:')
    print(f"{'':12}  s1=-1   s1=0  s1=+1")
    for s0 in SPINS:
        row = [f"{H_our(s0,s1):>+5.0f}" for s1 in SPINS]
        print(f"s0={s0:+d}   :  {'  '.join(row)}")

    print('\nMatriz de energias -- Alvarado:')
    print(f"{'':12}  s1=-1   s1=0  s1=+1")
    for s0 in SPINS:
        row = [f"{H_alv(s0,s1):>+5.0f}" for s1 in SPINS]
        print(f"s0={s0:+d}   :  {'  '.join(row)}")


if __name__ == '__main__':
    main()
