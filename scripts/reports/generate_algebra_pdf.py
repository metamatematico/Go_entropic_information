"""
generate_algebra_pdf.py
========================
Genera el informe matemático/algebraico del proyecto:
  "Variedades, Topología, Energía e Información en el Anillo de Spins de Go"

Cubre:
  1. El anillo R^9 como álgebra de observables
  2. Las variedades de Alvarado (género 0) vs M1 (género 1 — elípticas)
  3. El símplex de probabilidad como espacio de estados
  4. Dualidad de Legendre: energía ↔ entropía
  5. Geometría de la información (métrica de Fisher)
  6. Homología persistente de la trayectoria

Salida: results/reports/informe_algebra_topologia.pdf
"""

import os, sys
from pathlib import Path
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.gridspec as gridspec
from matplotlib.backends.backend_pdf import PdfPages
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch
from matplotlib.lines import Line2D

BASE    = str(Path(__file__).resolve().parents[2])
OUT     = os.path.join(BASE, 'docs', 'informe_algebra_topologia.pdf')
os.makedirs(os.path.dirname(OUT), exist_ok=True)

# ── Paleta ────────────────────────────────────────────────────────────────────
BG      = '#F8F5EE'
INK     = '#1A1A2E'
RED     = '#C0392B'
BLUE    = '#1A5276'
GREEN   = '#1E8449'
PURPLE  = '#7D3C98'
GOLD    = '#B7950B'
GRAY    = '#7F8C8D'
LGRAY   = '#D5D8DC'

def page_bg(fig):
    fig.patch.set_facecolor(BG)

def rule(ax, y=0.97, lw=0.8, color=INK):
    ax.axhline(y, xmin=0.0, xmax=1.0, color=color, lw=lw,
               transform=ax.transAxes, clip_on=False)

def section_header(ax, text, y=0.93, color=BLUE, size=13):
    ax.text(0.0, y, text, transform=ax.transAxes,
            fontsize=size, fontweight='bold', color=color,
            va='top', ha='left')

def body(ax, text, y, x=0.0, size=9.5, color=INK, **kw):
    ax.text(x, y, text, transform=ax.transAxes,
            fontsize=size, color=color, va='top', ha='left',
            wrap=True, **kw)

def math(ax, expr, x, y, size=11, color=INK, ha='left', va='top', **kw):
    ax.text(x, y, expr, transform=ax.transAxes,
            fontsize=size, color=color, va=va, ha=ha,
            fontfamily='monospace', **kw)

def blank_ax(fig, rect):
    ax = fig.add_axes(rect)
    ax.set_xlim(0,1); ax.set_ylim(0,1)
    ax.axis('off')
    ax.set_facecolor(BG)
    return ax

# ─────────────────────────────────────────────────────────────────────────────
# PÁGINA 1 — PORTADA
# ─────────────────────────────────────────────────────────────────────────────

def page_cover(pdf):
    fig = plt.figure(figsize=(8.5, 11))
    page_bg(fig)

    ax = fig.add_axes([0, 0, 1, 1])
    ax.set_xlim(0,1); ax.set_ylim(0,1); ax.axis('off')
    ax.set_facecolor(BG)

    # Franja superior
    ax.add_patch(plt.Rectangle((0, 0.82), 1, 0.18, fc=INK, ec='none', zorder=1))
    ax.text(0.5, 0.915, 'Go Entropic Information', fontsize=11,
            color='#B7950B', fontweight='bold', ha='center', va='center',
            zorder=2, fontstyle='italic')
    ax.text(0.5, 0.875, 'Proyecto de investigación  ·  Jiménez & Mercado  ·  UNAM',
            fontsize=8.5, color=LGRAY, ha='center', va='center', zorder=2)

    # Título
    ax.text(0.5, 0.73,
            'Variedades, Topología y\nGeometría de la Información\nen el Anillo de Spins de Go',
            fontsize=20, fontweight='bold', color=INK,
            ha='center', va='top', linespacing=1.4)

    # Línea dorada
    ax.plot([0.12, 0.88], [0.615, 0.615], '-', color=GOLD, lw=2)

    # Subtítulo
    ax.text(0.5, 0.59,
            r'R[x,y] / (x$^3$$-$x, y$^3$$-$y)   $\cong$   R$^9$',
            fontsize=14, color=BLUE, ha='center', va='top',
            fontfamily='monospace')

    ax.text(0.5, 0.545,
            'El espacio de Hamiltonianos, sus variedades algebraicas,\n'
            'la dualidad energía–entropía y la geometría de Fisher',
            fontsize=10, color=GRAY, ha='center', va='top', linespacing=1.5)

    # Diagrama decorativo central: símplex + anillo
    cx, cy, r = 0.5, 0.35, 0.12
    theta = np.linspace(0, 2*np.pi, 200)
    ax.plot(cx + r*np.cos(theta), cy + r*np.sin(theta)*0.55,
            '-', color=BLUE, lw=1.2, alpha=0.6)
    ax.plot(cx + r*0.6*np.cos(theta), cy + r*0.6*np.sin(theta)*0.55,
            '--', color=RED, lw=0.8, alpha=0.5)
    tri_x = [cx-0.18, cx+0.18, cx, cx-0.18]
    tri_y = [cy-0.11, cy-0.11, cy+0.14, cy-0.11]
    ax.plot(tri_x, tri_y, '-', color=PURPLE, lw=1.0, alpha=0.7)
    ax.text(cx, cy-0.21, r'$\Delta^8$  (símplex de estados)',
            fontsize=8, color=PURPLE, ha='center')
    ax.text(cx+0.21, cy+0.04, r'$\mathcal{V}_{M1}$', fontsize=10,
            color=BLUE, ha='left', fontstyle='italic')
    ax.text(cx+0.21, cy-0.04, r'$\mathcal{V}_{AL}$', fontsize=10,
            color=RED, ha='left', fontstyle='italic')

    # Franja inferior
    ax.add_patch(plt.Rectangle((0, 0), 1, 0.12, fc=INK, ec='none'))
    ax.text(0.5, 0.06,
            'Leonardo Jiménez Martínez  ·  Mario Mercado Sánchez\n'
            'UNAM  ·  2025–2026',
            fontsize=9, color=LGRAY, ha='center', va='center', linespacing=1.5)

    pdf.savefig(fig, bbox_inches='tight')
    plt.close(fig)


# ─────────────────────────────────────────────────────────────────────────────
# PÁGINA 2 — EL ANILLO
# ─────────────────────────────────────────────────────────────────────────────

def page_ring(pdf):
    fig = plt.figure(figsize=(8.5, 11))
    page_bg(fig)
    ax = blank_ax(fig, [0.08, 0.06, 0.84, 0.90])

    # Cabecera
    ax.text(0.0, 1.0, '1.  El Anillo de Observables',
            fontsize=16, fontweight='bold', color=INK, va='top')
    ax.plot([0, 1], [0.965, 0.965], '-', color=GOLD, lw=1.5,
            transform=ax.transAxes)

    y = 0.930
    body(ax,
         'El tablero de Go asigna a cada intersección un spin s ∈ {−1, 0, +1} '
         '(Negro = −1, Vacío = 0, Blanco = +1).  Como s satisface s³ = s, '
         'todos los cálculos ocurren en el anillo cociente:',
         y, size=9.5)

    y -= 0.075
    math(ax,
         r'R[x,y] / (x$^3$$-$x,  y$^3$$-$y)',
         0.5, y, size=13, ha='center', color=BLUE)

    y -= 0.065
    body(ax,
         'Por el Teorema Chino del Resto, los ideales (x³−x) y (y³−y) factorizan '
         'en factores coprimos:',
         y, size=9.5)

    y -= 0.065
    math(ax,
         r'x$^3$$-$x = x(x$-$1)(x+1)    $\Rightarrow$    R[x]/(x$^3$$-$x) $\cong$ R$\times$R$\times$R',
         0.1, y, size=9, color=BLUE)
    y -= 0.045
    math(ax,
         r'R[x,y]/(x$^3$$-$x, y$^3$$-$y) $\cong$ (R$\times$R$\times$R) $\otimes$ (R$\times$R$\times$R) $\cong$ R$^9$',
         0.1, y, size=11, color=BLUE)

    y -= 0.065
    body(ax,
         'Este es el álgebra de todas las funciones f : {−1,0,+1}² → R.  '
         'Tiene dimensión 9 como espacio vectorial.  Una base natural es el '
         'conjunto de indicadoras de Lagrange δ_{a,b}(x,y) = L_a(x)·L_b(y):',
         y, size=9.5)

    y -= 0.065
    math(ax,
         r'L$_{-1}$(x) = x(x$-$1)/2       L$_0$(x) = 1$-$x$^2$       L$_{+1}$(x) = x(x+1)/2',
         0.08, y, size=9, color=GREEN)

    y -= 0.075
    # Tabla de la base
    body(ax, 'Los 9 idempotentes ortogonales (la identidad de la partición):', y, size=9)
    y -= 0.055

    headers = ['', 's₁=−1', 's₁=0', 's₁=+1']
    rows_lbl = ['s₀=−1', 's₀=0', 's₀=+1']
    table_data = [
        [r'$\delta_{-1,-1}$', r'$\delta_{-1,0}$', r'$\delta_{-1,+1}$'],
        [r'$\delta_{0,-1}$',  r'$\delta_{0,0}$',  r'$\delta_{0,+1}$'],
        [r'$\delta_{+1,-1}$', r'$\delta_{+1,0}$', r'$\delta_{+1,+1}$'],
    ]
    col_x = [0.05, 0.28, 0.55, 0.80]
    row_y = [y, y-0.042, y-0.084]

    ax.text(col_x[1], y+0.015, 's₁=−1', fontsize=8, ha='center',
            color=GRAY, transform=ax.transAxes)
    ax.text(col_x[2], y+0.015, 's₁=0',  fontsize=8, ha='center',
            color=GRAY, transform=ax.transAxes)
    ax.text(col_x[3], y+0.015, 's₁=+1', fontsize=8, ha='center',
            color=GRAY, transform=ax.transAxes)

    for i, (lbl, row) in enumerate(zip(rows_lbl, table_data)):
        ax.text(col_x[0], row_y[i], lbl, fontsize=8, ha='left',
                color=GRAY, transform=ax.transAxes, va='center')
        for j, cell in enumerate(row):
            ax.text(col_x[j+1], row_y[i], cell, fontsize=8.5,
                    ha='center', color=BLUE, transform=ax.transAxes,
                    va='center')

    y -= 0.13
    body(ax,
         'Los dos Hamiltonianos son elementos específicos de R⁹.  '
         'En la base monomial {1, x, y, x², y², xy, x²y, xy², x²y²}:',
         y, size=9.5)

    y -= 0.065
    math(ax,
         r'H$_{AL}$ = xy',
         0.12, y, size=11, color=RED)
    ax.text(0.45, y, r'$\longrightarrow$   vector: (0, 0, 0, 0, 0, 1, 0, 0, 0)',
            fontsize=8.5, color=GRAY, transform=ax.transAxes, va='top')

    y -= 0.055
    math(ax,
         r'H$_{M1}$ = x + 2y $-$ xy$^2$ $-$ x$^2$y',
         0.12, y, size=11, color=BLUE)
    ax.text(0.55, y, r'$\longrightarrow$   (0,1,2,0,0,0,−1,−1,0)',
            fontsize=8.5, color=GRAY, transform=ax.transAxes, va='top')

    y -= 0.065
    body(ax,
         'Cualquier otro Hamiltoniano (incluyendo interacciones de tercer '
         'vecino, campos externos, etc.) vive en el mismo espacio de dimensión 9.  '
         'No existe Hamiltoniano "más general" para spins ternarios.',
         y, size=9.5, color=PURPLE)

    pdf.savefig(fig, bbox_inches='tight')
    plt.close(fig)


# ─────────────────────────────────────────────────────────────────────────────
# PÁGINA 3 — MATRICES DE INTERACCIÓN
# ─────────────────────────────────────────────────────────────────────────────

def page_matrices(pdf):
    fig = plt.figure(figsize=(8.5, 11))
    page_bg(fig)
    ax = blank_ax(fig, [0.08, 0.06, 0.84, 0.90])

    ax.text(0.0, 1.0, '2.  Las Matrices de Interacción',
            fontsize=16, fontweight='bold', color=INK, va='top')
    ax.plot([0, 1], [0.965, 0.965], '-', color=GOLD, lw=1.5,
            transform=ax.transAxes)

    y = 0.925
    body(ax,
         'Cada Hamiltoniano define una matriz 3×3 con entradas H(s₀, s₁) para '
         '(s₀, s₁) ∈ {−1, 0, +1}²:',
         y, size=9.5)

    # ── Matrices como subfiguras ──────────────────────────────────────────────
    ax_m1 = fig.add_axes([0.10, 0.61, 0.36, 0.27])
    ax_al = fig.add_axes([0.54, 0.61, 0.36, 0.27])

    M1 = np.array([[-1, -1, +1],
                   [-2,  0, +2],
                   [-1, +1, +1]], dtype=float)
    AL = np.array([[+1, 0, -1],
                   [ 0, 0,  0],
                   [-1, 0, +1]], dtype=float)

    for axi, M, title, cmap in [(ax_m1, M1, 'H$_{M1}$ — Mercado & Jiménez', 'RdBu_r'),
                                  (ax_al, AL, 'H$_{AL}$ — Alvarado', 'RdBu_r')]:
        im = axi.imshow(M, cmap=cmap, vmin=-2, vmax=2, aspect='auto')
        axi.set_xticks([0,1,2]); axi.set_yticks([0,1,2])
        axi.set_xticklabels(['-1', '0', '+1'], fontsize=9)
        axi.set_yticklabels(['-1', '0', '+1'], fontsize=9)
        axi.set_xlabel('s₁', fontsize=9); axi.set_ylabel('s₀', fontsize=9)
        axi.set_title(title, fontsize=9.5, pad=6, color=INK, fontweight='bold')
        for i in range(3):
            for j in range(3):
                v = int(M[i,j])
                axi.text(j, i, f'{v:+d}', ha='center', va='center',
                         fontsize=12, fontweight='bold',
                         color='white' if abs(v) > 1 else INK)

    ax.text(0.5, 0.885,
            'Izquierda: M1  (no simétrica)                '
            'Derecha: Alvarado  (simétrica)',
            fontsize=8, color=GRAY, ha='center', transform=ax.transAxes)

    y = 0.540
    body(ax,
         'La diferencia algebraica fundamental:',
         y, size=9.5, color=INK)

    y -= 0.048
    rows = [
        ('Simetría',      'M ≠ Mᵀ  (no simétrica)',    'M = Mᵀ  (simétrica)'),
        ('Tipo',          'Forma bilineal general',      'Forma bilineal simétrica'),
        ('Forma cuadr.',  'NO es cuadrática',            'E_AL = σᵀ·A_grafo·σ  ✓'),
        ('Vacío activo',  'H(0, sⱼ) ≠ 0 en general',   'H(0, sⱼ) = 0 siempre'),
        ('Valores',       '{−2,−1,0,+1,+2}',            '{−1, 0, +1}'),
        ('Asimetrizador', 'M − Mᵀ ≠ 0  (contiene info)', 'M − Mᵀ = 0  (trivial)'),
    ]
    col_w = [0.30, 0.38, 0.30]
    col_x2 = [0.01, 0.32, 0.70]
    hdrs = ['Propiedad', 'M1', 'Alvarado']
    for j, (h, cx) in enumerate(zip(hdrs, col_x2)):
        ax.text(cx, y, h, fontsize=9, color=GRAY, fontweight='bold',
                transform=ax.transAxes, va='top')
    y -= 0.035
    ax.plot([0.01, 0.99], [y+0.015, y+0.015], '-', color=LGRAY, lw=0.5,
            transform=ax.transAxes)
    for prop, v1, v2 in rows:
        ax.text(col_x2[0], y, prop, fontsize=8.5, color=INK,
                transform=ax.transAxes, va='top')
        ax.text(col_x2[1], y, v1, fontsize=8.5, color=BLUE,
                transform=ax.transAxes, va='top')
        ax.text(col_x2[2], y, v2, fontsize=8.5, color=RED,
                transform=ax.transAxes, va='top')
        y -= 0.042
        ax.plot([0.01, 0.99], [y+0.008, y+0.008], '-', color=LGRAY, lw=0.3,
                transform=ax.transAxes)

    y -= 0.02
    body(ax,
         'El "asimetrizador" (M − Mᵀ)/2 de M1 extrae la parte antisimétrica: '
         'mide cuánta energía adicional aporta la DIRECCIÓN del enlace k→j vs j→k.  '
         'Esto no existe en Alvarado por construcción.  '
         'Es el origen de la feature dE_asym en el dataset de trayectoria.',
         y, size=9.5, color=PURPLE)

    pdf.savefig(fig, bbox_inches='tight')
    plt.close(fig)


# ─────────────────────────────────────────────────────────────────────────────
# PÁGINA 4 — SOPORTE DEL VECTOR E IMPLICACIONES GEOMÉTRICAS
# ─────────────────────────────────────────────────────────────────────────────

def page_vector_support(pdf):
    fig = plt.figure(figsize=(8.5, 11))
    page_bg(fig)
    ax = blank_ax(fig, [0.07, 0.06, 0.86, 0.90])

    ax.text(0.0, 1.0, '3.  El Soporte del Vector y la Topología de las Fibras',
            fontsize=15, fontweight='bold', color=INK, va='top')
    ax.plot([0, 1], [0.965, 0.965], '-', color=GOLD, lw=1.5,
            transform=ax.transAxes)

    y = 0.925
    body(ax,
         'El soporte de un vector en R⁹ es el conjunto de posiciones con '
         'coeficiente no nulo.  En el anillo R[x,y]/(x³−x, y³−y), cada posición '
         'corresponde a un monomio de grado específico.  '
         'El grado máximo del soporte determina el grado de las curvas de nivel '
         'H = c, y por la fórmula de Plücker, el género de esas curvas.',
         y, size=9.5)

    # ── Tabla de la base ──────────────────────────────────────────────────────
    y -= 0.075
    headers = ['Pos.', 'Monomio', 'Grado', 'Coef. H_AL', 'Coef. H_M1', 'En soporte de']
    col_x   = [0.00, 0.08, 0.20, 0.30, 0.44, 0.58]
    row_h   = 0.040

    # Cabecera
    for h, cx in zip(headers, col_x):
        ax.add_patch(plt.Rectangle((cx, y - row_h + 0.005), 0.13, row_h - 0.003,
                     fc=INK, ec='none', transform=ax.transAxes, zorder=0, clip_on=False))
        ax.text(cx + 0.005, y - 0.005, h, fontsize=8, color='white',
                transform=ax.transAxes, va='top', fontweight='bold')

    data = [
        ('0', '1',     '0', '0',  '0',  '—'),
        ('1', 'x',     '1', '0', '+1',  'M1  ←  campo en s₀'),
        ('2', 'y',     '1', '0', '+2',  'M1  ←  campo en s₁ (doble)'),
        ('3', 'x²',    '2', '0',  '0',  '—'),
        ('4', 'y²',    '2', '0',  '0',  '—'),
        ('5', 'xy',    '2', '+1', '0',  'AL  ←  único término'),
        ('6', 'x²y',   '3', '0', '−1',  'M1  ←  acopl. mediado por ocup.'),
        ('7', 'xy²',   '3', '0', '−1',  'M1  ←  acopl. mediado por ocup.'),
        ('8', 'x²y²',  '4', '0',  '0',  '—'),
    ]

    colors_row = [BG, '#FEF9F0', BG, '#FEF9F0', BG, '#EBF5FB',
                  '#FDEDEC', '#FDEDEC', BG]

    for i, (pos, mono, deg, cal, cm1, note) in enumerate(data):
        ry = y - (i + 1) * row_h
        ax.add_patch(plt.Rectangle((0.0, ry + 0.003), 0.99, row_h - 0.003,
                     fc=colors_row[i], ec='none', transform=ax.transAxes, zorder=0))
        vals = [pos, mono, deg, cal, cm1, note]
        txt_colors = [GRAY, INK, GRAY,
                      RED if cal != '0' else GRAY,
                      BLUE if cm1 != '0' else GRAY,
                      RED if 'AL' in note else (BLUE if 'M1' in note else GRAY)]
        for v, cx, tc in zip(vals, col_x, txt_colors):
            ax.text(cx + 0.005, ry + row_h - 0.007, v, fontsize=8.5,
                    color=tc, transform=ax.transAxes, va='top',
                    fontweight='bold' if v not in ('0', '—', '') else 'normal')

    y -= (len(data) + 1) * row_h + 0.015

    # ── Diagrama: soporte → grado → género ───────────────────────────────────
    ax_flow = fig.add_axes([0.06, 0.22, 0.88, 0.13])
    ax_flow.set_facecolor(BG); ax_flow.axis('off')
    ax_flow.set_xlim(0, 1); ax_flow.set_ylim(0, 1)

    blocks = [
        (0.05, 0.35, 'Soporte\ndel vector', '{5}', '{1,2,6,7}', RED, BLUE),
        (0.28, 0.20, 'Grado\nmáximo', 'deg = 2', 'deg = 3', RED, BLUE),
        (0.51, 0.20, 'Fórmula\nPlücker\ng=(d−1)(d−2)/2', 'g = 0', 'g = 1', RED, BLUE),
        (0.74, 0.20, 'Topología\nde la fibra', 'cónica\n(racional)', 'cúbica\nelíptica', RED, BLUE),
    ]

    for bx, bw, label, val_al, val_m1, cal, cm1 in blocks:
        ax_flow.add_patch(FancyBboxPatch((bx, 0.05), bw, 0.90,
                          boxstyle='round,pad=0.02', fc='white',
                          ec=LGRAY, lw=0.8))
        ax_flow.text(bx + bw/2, 0.90, label, ha='center', va='top',
                     fontsize=7.5, color=GRAY, linespacing=1.2)
        ax_flow.text(bx + bw/2, 0.55, val_al, ha='center', va='center',
                     fontsize=8, color=cal, fontweight='bold')
        ax_flow.text(bx + bw/2, 0.25, val_m1, ha='center', va='center',
                     fontsize=8, color=cm1, fontweight='bold')
        if bx < 0.74:
            ax_flow.annotate('', xy=(bx + bw + 0.005, 0.5),
                             xytext=(bx + bw, 0.5),
                             arrowprops=dict(arrowstyle='->', color=LGRAY, lw=1.2))

    ax_flow.text(0.01, 0.55, 'H_AL', fontsize=8, color=RED, va='center',
                 fontweight='bold')
    ax_flow.text(0.01, 0.25, 'H_M1', fontsize=8, color=BLUE, va='center',
                 fontweight='bold')

    y = 0.195
    body(ax,
         'La fórmula de Plücker g = (d−1)(d−2)/2 aplica para curvas planas '
         'proyectivas lisas de grado d.  '
         'Alvarado tiene soporte en el monomio xy de grado 2 → d=2 → g=0 '
         '(hipérbolas, racionalmente parametrizables).  '
         'M1 tiene soporte en x²y y xy² de grado 3 → d=3 → g=1 '
         '(curvas elípticas, no racionalmente parametrizables).  '
         'La AUSENCIA de x²y², xy², x²y en Alvarado y la AUSENCIA de xy en M1 '
         'no son accidentales: definen el tipo geométrico de cada modelo.',
         y, size=9.5, color=PURPLE)

    y -= 0.095
    body(ax,
         'Si se añadiera el término x²y² (posición 8) a cualquier modelo, '
         'el grado subiría a 4 y el género a g = (3)(2)/2 = 3.  '
         'Si se eliminaran los términos de grado 3 de M1, '
         'las fibras bajarían a género 0 y M1 perdería su riqueza topológica.',
         y, size=9, color=GRAY)

    pdf.savefig(fig, bbox_inches='tight')
    plt.close(fig)


# ─────────────────────────────────────────────────────────────────────────────
# PÁGINA 5 — ANÁLISIS COMPONENTE A COMPONENTE
# ─────────────────────────────────────────────────────────────────────────────

def page_component_analysis(pdf):
    fig = plt.figure(figsize=(8.5, 11))
    page_bg(fig)
    ax = blank_ax(fig, [0.07, 0.06, 0.86, 0.90])

    ax.text(0.0, 1.0, '4.  Análisis Componente a Componente',
            fontsize=15, fontweight='bold', color=INK, va='top')
    ax.plot([0, 1], [0.965, 0.965], '-', color=GOLD, lw=1.5,
            transform=ax.transAxes)

    # ── Alvarado: posición 5 ─────────────────────────────────────────────────
    y = 0.920
    ax.add_patch(FancyBboxPatch((0.0, y - 0.195), 0.99, 0.200,
                 boxstyle='round,pad=0.01', fc='#EBF5FB', ec=RED, lw=1.2,
                 transform=ax.transAxes))
    ax.text(0.01, y - 0.005,
            'H_AL = xy   →   vector (0, 0, 0, 0, 0,  1 , 0, 0, 0)   — posición 5 únicamente',
            fontsize=9.5, color=RED, fontweight='bold', transform=ax.transAxes, va='top',
            fontfamily='monospace')

    items_al = [
        ('Simetría bajo swap x↔y',
         'xy → yx = xy.  Invariante exacto.  El único monomio de grado 2 '
         'que es simétrico bajo intercambio de los dos spins.'),
        ('Simetría bajo cambio de color (x,y)→(−x,−y)',
         '(−x)(−y) = xy.  Invariante exacto.  H_AL es PAR bajo '
         'la inversión global de color B↔W.'),
        ('Vacuum-invisible',
         'H_AL(0, y) = 0 y H_AL(x, 0) = 0.  El vacío no contribuye energía.  '
         'Algebraicamente: xy tiene factor x e y, ambos se anulan con s=0.'),
        ('Rango de la matriz 3×3',
         'H_AL = v⊗vᵀ con v = (−1, 0, +1)ᵀ.  Matriz de rango 1.  '
         'Eigenvalores: {2, 0, 0}.  El "tensor de interacción" más degenerado posible.'),
    ]

    yy = y - 0.038
    for title, text in items_al:
        ax.text(0.02, yy, f'▸ {title}:', fontsize=8.5, color=RED,
                transform=ax.transAxes, va='top', fontweight='bold')
        ax.text(0.02, yy - 0.022, text, fontsize=8, color=INK,
                transform=ax.transAxes, va='top', linespacing=1.3)
        yy -= 0.048

    # ── M1: posiciones 1, 2, 6, 7 ────────────────────────────────────────────
    y = 0.700
    ax.add_patch(FancyBboxPatch((0.0, y - 0.520), 0.99, 0.525,
                 boxstyle='round,pad=0.01', fc='#EBF5FB', ec=BLUE, lw=1.2,
                 transform=ax.transAxes))
    ax.text(0.01, y - 0.005,
            'H_M1 = x + 2y − xy² − x²y   →   (0,  1 ,  2 , 0, 0, 0, −1 , −1 , 0)',
            fontsize=9.5, color=BLUE, fontweight='bold', transform=ax.transAxes, va='top',
            fontfamily='monospace')

    items_m1 = [
        ('Pos. 1: coef. +1 de x  (campo externo sobre s₀)',
         'Contribuye s₀ a la energía.  H_M1(x, 0) = x: cuando el vecino s₁ está vacío, '
         'la energía es el propio spin s₀.  Hace al vacío de s₁ VISIBLE desde s₀.'),
        ('Pos. 2: coef. +2 de y  (campo externo sobre s₁, el doble)',
         'H_M1(0, y) = 2y: cuando s₀=0, la energía del vecino s₁ vale el doble.  '
         'El vecino preexistente s₁ pesa MÁS que la piedra que se coloca s₀.  '
         'Rompe la simetría entre "quien coloca" y "quien recibe la influencia".'),
        ('Pos. 6: coef. −1 de x²y  (ocupación de s₀ modifica el campo de s₁)',
         'x² = s₀² es la indicadora de que s₀ está ocupado (vale 1 si s₀≠0, 0 si vacío).  '
         'El término −x²y = −(1 si s₀ ocupado)·s₁ reduce el campo de s₁ cuando s₀ está ocupado.  '
         'Cuando s₀ ≠ 0: campo neto sobre s₁ = 2y − y = y.'),
        ('Pos. 7: coef. −1 de xy²  (ocupación de s₁ modifica el campo de s₀)',
         'Análogamente: −xy² = −s₀·(1 si s₁ ocupado).  '
         'Cuando s₁ ≠ 0: campo neto sobre s₀ = x − x = 0.'),
        ('Caso ambos ocupados: H_M1 = s₁  (resultado exacto)',
         'Si s₀ ≠ 0 y s₁ ≠ 0, entonces s₀²=s₁²=1 y: '
         'H = s₀ + 2s₁ − s₀·1 − 1·s₁ = s₀ + 2s₁ − s₀ − s₁ = s₁.  '
         'El resultado es solo el color del vecino: el modelo mide '
         '"¿de qué color es el vecino que rodea la piedra recién colocada?"'),
    ]

    yy = y - 0.038
    for title, text in items_m1:
        ax.text(0.02, yy, f'▸ {title}:', fontsize=8, color=BLUE,
                transform=ax.transAxes, va='top', fontweight='bold')
        ax.text(0.02, yy - 0.023, text, fontsize=7.8, color=INK,
                transform=ax.transAxes, va='top', linespacing=1.3)
        yy -= 0.095

    # ── Posición 8: ausente en ambos ─────────────────────────────────────────
    y = 0.155
    ax.add_patch(FancyBboxPatch((0.0, y - 0.085), 0.99, 0.088,
                 boxstyle='round,pad=0.01', fc='#F9F9F9', ec=GRAY, lw=0.8,
                 transform=ax.transAxes))
    ax.text(0.01, y - 0.008,
            'Pos. 8: coef. 0 de x²y²  (ausente en AMBOS modelos)',
            fontsize=9, color=GRAY, fontweight='bold', transform=ax.transAxes, va='top')
    ax.text(0.02, y - 0.032,
            'x²y² = s₀²·s₁² es la indicadora conjunta de que AMBAS celdas están ocupadas.  '
            'Coeficiente 0 en ambos modelos → ninguno añade "bonus energético '
            'por densidad de piedras".  Un modelo con este término sería sensible '
            'a la densidad local independientemente del color.',
            fontsize=8, color=GRAY, transform=ax.transAxes, va='top', linespacing=1.3)

    pdf.savefig(fig, bbox_inches='tight')
    plt.close(fig)


# ─────────────────────────────────────────────────────────────────────────────
# PÁGINA 6 — SIMETRÍA, DESCOMPOSICIÓN Y NÚCLEO
# ─────────────────────────────────────────────────────────────────────────────

def page_symmetry_nullspace(pdf):
    fig = plt.figure(figsize=(8.5, 11))
    page_bg(fig)
    ax = blank_ax(fig, [0.07, 0.06, 0.86, 0.90])

    ax.text(0.0, 1.0, '5.  Simetría, Descomposición y Núcleo',
            fontsize=15, fontweight='bold', color=INK, va='top')
    ax.plot([0, 1], [0.965, 0.965], '-', color=GOLD, lw=1.5,
            transform=ax.transAxes)

    # ── §A: Acción del grupo S₂ (swap) ────────────────────────────────────────
    y = 0.915
    section_header(ax, 'A.  Acción del grupo S₂ (intercambio de spins x↔y)', y,
                   color=BLUE, size=10)
    y -= 0.042
    body(ax,
         'El swap x↔y permuta los componentes del vector: '
         '(coef_x, coef_y) → (coef_y, coef_x)  y  (coef_{x²y}, coef_{xy²}) → '
         '(coef_{xy²}, coef_{x²y}).  Los demás componentes son fijos.',
         y, size=9)

    y -= 0.050
    math(ax,
         r'H$_{AL}$: (0,0,0,0,0, 1 ,0,0,0)  $\rightarrow$  '
         r'(0,0,0,0,0, 1 ,0,0,0)    $\Rightarrow$  INVARIANTE  (simétrico)',
         0.03, y, size=8.5, color=RED)
    y -= 0.038
    math(ax,
         r'H$_{M1}$: (0, 1 , 2 ,0,0,0,−1,−1,0)  $\rightarrow$  '
         r'(0, 2 , 1 ,0,0,0,−1,−1,0)    $\Rightarrow$  CAMBIA',
         0.03, y, size=8.5, color=BLUE)

    y -= 0.045
    body(ax,
         'La parte antisimétrica de H_M1 (lo que cambia de signo bajo swap):',
         y, size=9)
    y -= 0.038
    math(ax,
         r'H$_{M1}^{antisim}$ = $\frac{1}{2}$[(0,1,2,...) − (0,2,1,...)] = '
         r'(0, −½, +½, 0,...) = $\frac{y − x}{2}$',
         0.1, y, size=9.5, color=BLUE)
    y -= 0.038
    body(ax,
         'Toda la no-simetría de M1 se reduce a un único término: (y−x)/2.  '
         'Es la perturbación mínima que eleva el género de 0 a 1.',
         y, size=8.5, color=PURPLE)

    # ── §B: Cambio de color ────────────────────────────────────────────────────
    y -= 0.052
    section_header(ax, 'B.  Cambio global de color  (x, y) → (−x, −y)', y,
                   color=BLUE, size=10)
    y -= 0.042
    body(ax,
         'La paridad de cada monomio bajo (x,y)→(−x,−y): '
         '1,x²,y²,xy,x²y² son pares (+1).  x, y, x²y, xy² son impares (−1).',
         y, size=9)

    y -= 0.042
    math(ax,
         r'H$_{AL}$: coef. en posición 5 (xy, PAR) → H$_{AL}$(−x,−y) = xy = +H$_{AL}$   '
         r'[INVARIANTE bajo B↔W]',
         0.03, y, size=8.5, color=RED)
    y -= 0.035
    math(ax,
         r'H$_{M1}$: coefs. en posiciones 1,2,6,7 (IMPARES) → H$_{M1}$(−x,−y) = −H$_{M1}$   '
         r'[ANTISIMÉTRICO bajo B↔W]',
         0.03, y, size=8.5, color=BLUE)

    y -= 0.042
    body(ax,
         'Consecuencia directa: en una partida real con igual número de piedras '
         'negras y blancas, ⟨H_M1⟩ = 0 exactamente por antisimetría.  '
         'Esto explica el hallazgo empírico T_eff → ∞: con ⟨E_M1⟩ ≈ 0, '
         'el modelo cree estar en temperatura infinita.',
         y, size=8.8, color=PURPLE)

    # ── §C: Descomposición campo + acoplamiento ────────────────────────────────
    y -= 0.058
    section_header(ax, 'C.  Descomposición Ising: campo externo + acoplamiento', y,
                   color=BLUE, size=10)
    y -= 0.038

    ax_dec = fig.add_axes([0.07, 0.295, 0.86, 0.075])
    ax_dec.set_facecolor(BG); ax_dec.axis('off')
    ax_dec.set_xlim(0, 1); ax_dec.set_ylim(0, 1)

    ax_dec.add_patch(FancyBboxPatch((0.0, 0.0), 0.30, 1.0,
                     boxstyle='round,pad=0.02', fc='#EBF5FB', ec=RED, lw=1.2))
    ax_dec.text(0.15, 0.85, 'H_AL', ha='center', fontsize=9.5, color=RED,
                fontweight='bold', va='top')
    ax_dec.text(0.15, 0.55, 'h = 0', ha='center', fontsize=9, color=GRAY, va='top')
    ax_dec.text(0.15, 0.25, 'J = xy', ha='center', fontsize=9, color=RED,
                fontweight='bold', va='top')

    ax_dec.text(0.50, 0.50, '=   h·(s₀ + s₁)  +  J(s₀, s₁)',
                ha='center', fontsize=9, color=INK, va='center')

    ax_dec.add_patch(FancyBboxPatch((0.69, 0.0), 0.30, 1.0,
                     boxstyle='round,pad=0.02', fc='#EBF5FB', ec=BLUE, lw=1.2))
    ax_dec.text(0.84, 0.85, 'H_M1', ha='center', fontsize=9.5, color=BLUE,
                fontweight='bold', va='top')
    ax_dec.text(0.84, 0.55, 'h = (1, 2)', ha='center', fontsize=9,
                color=GRAY, va='top')
    ax_dec.text(0.84, 0.25, 'J = −x²y − xy²', ha='center', fontsize=9,
                color=BLUE, fontweight='bold', va='top')

    y = 0.268
    body(ax,
         'H_AL es ACOPLAMIENTO PURO (sin campo).  '
         'H_M1 = CAMPO ASIMÉTRICO (h_x=1, h_y=2) + ACOPLAMIENTO MEDIADO POR OCUPACIÓN.  '
         'El campo asimétrico (h_y = 2h_x) hace que el vecino s₁ pese el doble que s₀.',
         y, size=8.8)

    # ── §D: Núcleo (null space) ────────────────────────────────────────────────
    y -= 0.075
    section_header(ax, 'D.  Núcleo de la matriz 3×3', y, color=BLUE, size=10)
    y -= 0.040

    rows_null = [
        ('H_AL', 'rango 1', 'dim = 2',
         'span{(1,0,1), (0,1,0)}',
         'Estado balanceado B=W  Y  estado vacío',
         RED),
        ('H_M1', 'rango 2', 'dim = 1',
         'span{(1,0,1)}',
         'Solo el estado balanceado B=W',
         BLUE),
    ]

    col_nx = [0.0, 0.10, 0.20, 0.30, 0.56]
    for model, rank, dim, null_v, meaning, color in rows_null:
        ax.add_patch(FancyBboxPatch((0.0, y-0.048), 0.99, 0.048,
                     boxstyle='round,pad=0.005', fc=BG, ec=color, lw=0.8,
                     transform=ax.transAxes))
        for v, cx in zip([model, rank, dim, null_v, meaning], col_nx):
            ax.text(cx + 0.01, y - 0.004, v, fontsize=8.2,
                    color=color if v == model else (INK if v == meaning else GRAY),
                    transform=ax.transAxes, va='top',
                    fontweight='bold' if v == model else 'normal')
        y -= 0.055

    y -= 0.005
    body(ax,
         'El estado vacío (0, 1, 0) — toda la probabilidad en s₁=0 — '
         'está en el núcleo de H_AL pero NO en el de H_M1:',
         y, size=9)
    y -= 0.038
    math(ax,
         r'H$_{AL}$ · (0, 1, 0)$^T$ = (0, 0, 0)$^T$   '
         r'[vacío invisible]',
         0.08, y, size=9, color=RED)
    y -= 0.032
    math(ax,
         r'H$_{M1}$ · (0, 1, 0)$^T$ = (−1, 0, +1)$^T$ $\neq$ 0   '
         r'[vacío activa vector B↔W]',
         0.08, y, size=9, color=BLUE)
    y -= 0.040
    body(ax,
         'Cuando s₁=0, M1 produce el vector (−1, 0, +1) en la imagen — '
         'exactamente el vector de diferencia de color.  '
         'El vacío "activa" una distinción entre negro y blanco en M1.  '
         'Esta es la manifestación algebraica exacta de la propiedad vacuum-active.',
         y, size=8.8, color=PURPLE)

    pdf.savefig(fig, bbox_inches='tight')
    plt.close(fig)


# ─────────────────────────────────────────────────────────────────────────────
# PÁGINA 7 — VARIEDADES ALGEBRAICAS
# ─────────────────────────────────────────────────────────────────────────────

def page_varieties(pdf):
    fig = plt.figure(figsize=(8.5, 11))
    page_bg(fig)
    ax = blank_ax(fig, [0.08, 0.06, 0.84, 0.90])

    ax.text(0.0, 1.0, '6.  Variedades Algebraicas de cada Modelo',
            fontsize=16, fontweight='bold', color=INK, va='top')
    ax.plot([0, 1], [0.965, 0.965], '-', color=GOLD, lw=1.5,
            transform=ax.transAxes)

    y = 0.925
    body(ax,
         'Cada Hamiltoniano H : A² → A¹ define una fibración de variedades '
         'afines.  La fibra sobre c es la curva de nivel H(x,y) = c en R².  '
         'La topología de esas curvas difiere cualitativamente entre modelos.',
         y, size=9.5)

    # Gráficas de curvas de nivel
    ax_al = fig.add_axes([0.07, 0.53, 0.38, 0.35])
    ax_m1 = fig.add_axes([0.55, 0.53, 0.38, 0.35])

    x = np.linspace(-2.5, 2.5, 600)
    X, Y = np.meshgrid(x, x)

    # Alvarado: xy = c
    Z_al = X * Y
    # M1: x + 2y - xy(x+y) = c
    Z_m1 = X + 2*Y - X*Y*(X+Y)

    levels_al = [-1.5, -1.0, -0.5, -0.1, 0, 0.1, 0.5, 1.0, 1.5]
    levels_m1 = [-3, -1.5, -0.5, 0, 0.5, 1.5, 3, 5]

    for axi, Z, levels, title, color_neg, color_pos in [
        (ax_al, Z_al, levels_al, r'H$_{AL}$ = xy  (Alvarado)',
         '#2980B9', '#C0392B'),
        (ax_m1, Z_m1, levels_m1,
         r'H$_{M1}$ = x+2y$-$xy(x+y)  (Mercado & Jiménez)',
         '#2980B9', '#C0392B'),
    ]:
        axi.set_facecolor(BG)
        axi.set_xlim(-2.5, 2.5); axi.set_ylim(-2.5, 2.5)
        neg_levels = [l for l in levels if l < 0]
        pos_levels = [l for l in levels if l > 0]
        zero_levels = [l for l in levels if l == 0]
        if neg_levels:
            axi.contour(X, Y, Z, levels=neg_levels,
                        colors=color_neg, linewidths=0.9, alpha=0.75)
        if pos_levels:
            axi.contour(X, Y, Z, levels=pos_levels,
                        colors=color_pos, linewidths=0.9, alpha=0.75)
        if zero_levels:
            axi.contour(X, Y, Z, levels=zero_levels,
                        colors=[GOLD], linewidths=1.5, alpha=0.9)
        axi.axhline(0, color=LGRAY, lw=0.4); axi.axvline(0, color=LGRAY, lw=0.4)
        axi.set_xlabel('x  (spin s₀)', fontsize=8.5)
        axi.set_ylabel('y  (spin s₁)', fontsize=8.5)
        axi.set_title(title, fontsize=8.5, color=INK, fontweight='bold', pad=5)
        axi.tick_params(labelsize=7.5)
        for sp in axi.spines.values():
            sp.set_color(LGRAY)

    y = 0.500
    body(ax,
         'Comparación topológica de las fibras H = c:',
         y, size=9.5, fontweight='bold')

    y -= 0.048
    info = [
        ('Alvarado  H_AL = c', 'xy = c',
         'Hipérbolas (c≠0) o ejes coord. (c=0)',
         'Género 0 — racionalmente parametrizable: (t, c/t)',
         RED),
        ('M1  H_M1 = c', 'x+2y−xy(x+y) = c',
         'Curva cúbica plana (grado 3)',
         'Género 1 — CURVA ELÍPTICA (toro con 3 pinchaduras)',
         BLUE),
    ]
    for name, eqn, topology, genus_str, color in info:
        ax.add_patch(FancyBboxPatch((0.0, y-0.085), 0.98, 0.080,
                     boxstyle='round,pad=0.01', fc=BG,
                     ec=color, lw=1.2, transform=ax.transAxes))
        ax.text(0.02, y-0.01, name, fontsize=9, fontweight='bold',
                color=color, transform=ax.transAxes, va='top')
        ax.text(0.02, y-0.032, eqn, fontsize=8.5,
                color=color, transform=ax.transAxes, va='top',
                fontfamily='monospace')
        ax.text(0.02, y-0.055, topology, fontsize=8,
                color=GRAY, transform=ax.transAxes, va='top')
        ax.text(0.02, y-0.073, genus_str, fontsize=8.5,
                color=INK, transform=ax.transAxes, va='top', fontstyle='italic')
        y -= 0.102

    y -= 0.01
    body(ax,
         'La fórmula de Plücker: una curva plana proyectiva lisa de grado d '
         'tiene género g = (d−1)(d−2)/2.  Para d=2 (Alvarado): g=0.  '
         'Para d=3 (M1): g=1.  El género 1 implica que las curvas de nivel de M1 '
         'son elípticas — no existe parametrización racional.  '
         'Esto refleja la no-simetría algebraica del Hamiltoniano.',
         y, size=9.5, color=PURPLE)

    pdf.savefig(fig, bbox_inches='tight')
    plt.close(fig)


# ─────────────────────────────────────────────────────────────────────────────
# PÁGINA 5 — VALORES CRÍTICOS Y CAMBIO DE TOPOLOGÍA
# ─────────────────────────────────────────────────────────────────────────────

def page_critical(pdf):
    fig = plt.figure(figsize=(8.5, 11))
    page_bg(fig)
    ax = blank_ax(fig, [0.08, 0.06, 0.84, 0.90])

    ax.text(0.0, 1.0, '7.  Valores Críticos y Topología de las Fibras',
            fontsize=16, fontweight='bold', color=INK, va='top')
    ax.plot([0, 1], [0.965, 0.965], '-', color=GOLD, lw=1.5,
            transform=ax.transAxes)

    y = 0.925
    body(ax,
         'Los puntos críticos de H_M1 (donde la fibra H=c cambia de topología) '
         'se obtienen anulando el gradiente:',
         y, size=9.5)

    y -= 0.065
    math(ax,
         r'$\partial$H/$\partial$x = 1 $-$ 2xy $-$ y$^2$ = 0',
         0.08, y, size=10, color=BLUE)
    y -= 0.042
    math(ax,
         r'$\partial$H/$\partial$y = 2 $-$ x$^2$ $-$ 2xy = 0',
         0.08, y, size=10, color=BLUE)

    y -= 0.058
    body(ax,
         'Dividiendo ambas ecuaciones (con p = x/y):',
         y, size=9.5)

    y -= 0.050
    math(ax,
         r'p(p+2)/(2p+1) = 2   $\Rightarrow$   p$^2$ $-$ 2p $-$ 2 = 0   '
         r'$\Rightarrow$   p = 1 $\pm$ $\sqrt{3}$',
         0.08, y, size=10, color=BLUE)

    y -= 0.065
    body(ax,
         'Esto da dos valores críticos c₁ < c₂ de la energía.  '
         'La topología de la fibra H_M1 = c cambia en esos valores:',
         y, size=9.5)

    # Diagrama de la fibración
    y -= 0.045
    ax_fib = fig.add_axes([0.08, 0.44, 0.84, 0.28])
    ax_fib.set_facecolor(BG)
    ax_fib.set_xlim(-0.05, 1.05); ax_fib.set_ylim(-0.05, 1.05)
    ax_fib.axis('off')

    # Línea de la "base" A¹
    ax_fib.annotate('', xy=(0.95, 0.1), xytext=(0.05, 0.1),
                    arrowprops=dict(arrowstyle='->', color=INK, lw=1.2))
    ax_fib.text(0.5, 0.02, 'valor de c  (energía)', ha='center',
                fontsize=9, color=INK)
    ax_fib.text(0.98, 0.10, r'A$^1$', fontsize=10, color=INK, va='center')

    # Valores críticos
    c1_x, c2_x = 0.32, 0.68
    ax_fib.plot(c1_x, 0.10, 'v', color=RED, ms=9, zorder=5)
    ax_fib.plot(c2_x, 0.10, 'v', color=RED, ms=9, zorder=5)
    ax_fib.text(c1_x, 0.21, 'c₁ (crítico)', ha='center', fontsize=8,
                color=RED, fontweight='bold')
    ax_fib.text(c2_x, 0.21, 'c₂ (crítico)', ha='center', fontsize=8,
                color=RED, fontweight='bold')

    # Regiones
    ax_fib.text(0.15, 0.15, 'c < c₁', ha='center', fontsize=8, color=BLUE)
    ax_fib.text(0.50, 0.15, 'c₁ < c < c₂', ha='center', fontsize=8, color=BLUE)
    ax_fib.text(0.84, 0.15, 'c > c₂', ha='center', fontsize=8, color=BLUE)

    # Fibras esquemáticas: toro pinchado / esfera nodal / toro pinchado
    for (xc, shape, label, color) in [
        (0.15, 'torus', 'Toro\ncon 3 agujeros\n(g=1)', BLUE),
        (c1_x, 'node',  'Cúbica\nsingular\n(nodo)', RED),
        (0.50, 'torus', 'Toro\ncon 3 agujeros\n(g=1)', BLUE),
        (c2_x, 'node',  'Cúbica\nsingular\n(nodo)', RED),
        (0.84, 'torus', 'Toro\ncon 3 agujeros\n(g=1)', BLUE),
    ]:
        ax_fib.plot([xc, xc], [0.10, 0.35], '--', color=LGRAY, lw=0.7)
        if shape == 'torus':
            th = np.linspace(0, 2*np.pi, 100)
            R2, r2 = 0.07, 0.03
            ax_fib.plot(xc + R2*np.cos(th), 0.60 + R2*0.45*np.sin(th),
                        '-', color=color, lw=1.0, alpha=0.8)
            ax_fib.plot(xc + r2*np.cos(th), 0.60 + r2*0.45*np.sin(th),
                        '-', color=color, lw=0.6, alpha=0.5, ls='--')
        else:
            ax_fib.plot(xc, 0.60, '*', color=color, ms=15, alpha=0.9)
        ax_fib.text(xc, 0.38, label, ha='center', va='bottom',
                    fontsize=7, color=color, linespacing=1.3)

    y = 0.40
    body(ax,
         'Esta es la fibración de Milnor del polinomio H_M1.  '
         'En los valores críticos c₁ y c₂, la curva elíptica desarrolla un nodo '
         '(una singularidad de tipo A₁ en la clasificación ADE de singularidades).  '
         'La variedad total de la fibración es una superficie en A³:',
         y, size=9.5)

    y -= 0.058
    math(ax,
         r'$\Gamma$(H$_{M1}$) = {(x, y, z) $\in$ A$^3$ : z = x + 2y $-$ xy(x+y)}',
         0.08, y, size=10, color=BLUE)

    y -= 0.055
    body(ax,
         'Esta superficie cúbica en A³ es la variedad fundamental del modelo M1.  '
         'Tiene curvatura gaussiana negativa en toda su extensión (es una '
         'hipersuperficie silla), y su topología como superficie real es '
         'equivalente a R² (contractible), aunque su estructura algebraica '
         'compleja es richer que la de la paraboloide hiperbólica de Alvarado '
         'Γ(H_AL) = {z = xy}.',
         y, size=9.5, color=PURPLE)

    y -= 0.095
    body(ax,
         'Alvarado:  Γ(H_AL) = {z = xy}  →  paraboloide hiperbólica '
         '(superficie reglada, K < 0, topológicamente R²)\n'
         'M1:        Γ(H_M1) = {z = x+2y−xy(x+y)}  →  superficie cúbica '
         'no reglada, K variable, con dos puntos de inflexión (los críticos)',
         y, size=9, color=GRAY)

    pdf.savefig(fig, bbox_inches='tight')
    plt.close(fig)


# ─────────────────────────────────────────────────────────────────────────────
# PÁGINA 6 — SÍMPLEX DE ESTADOS Y ESTADOS DE GIBBS
# ─────────────────────────────────────────────────────────────────────────────

def page_simplex(pdf):
    fig = plt.figure(figsize=(8.5, 11))
    page_bg(fig)
    ax = blank_ax(fig, [0.08, 0.06, 0.84, 0.90])

    ax.text(0.0, 1.0, '8.  El Símplex de Estados y los Estados de Gibbs',
            fontsize=16, fontweight='bold', color=INK, va='top')
    ax.plot([0, 1], [0.965, 0.965], '-', color=GOLD, lw=1.5,
            transform=ax.transAxes)

    y = 0.925
    body(ax,
         'Dual al espacio de observables R⁹ está el símplex de probabilidad — '
         'el espacio de estados del sistema (distribuciones sobre pares de spins):',
         y, size=9.5)

    y -= 0.060
    math(ax,
         r'$\Delta^8$ = { p : {$-$1,0,+1}$^2$ $\rightarrow$ R$_{\geq 0}$  '
         r'|  $\sum$ p(s$_0$, s$_1$) = 1 }',
         0.5, y, size=10.5, color=BLUE, ha='center')

    y -= 0.060
    body(ax,
         'Es un símplex estándar de dimensión 8 en R⁹.  '
         'El estado de Gibbs para el Hamiltoniano H a temperatura inversa β es:',
         y, size=9.5)

    y -= 0.060
    math(ax,
         r'p$_\beta$(s$_0$, s$_1$) = exp($-\beta$ · H(s$_0$, s$_1$)) / Z($\beta$)',
         0.5, y, size=11, color=BLUE, ha='center')

    y -= 0.050
    body(ax, 'Las funciones de partición explícitas:', y, size=9.5)

    y -= 0.050
    math(ax,
         r'Z$_{AL}$($\beta$) = 5 + 4 cosh($\beta$)',
         0.12, y, size=10, color=RED)
    y -= 0.042
    math(ax,
         r'Z$_{M1}$($\beta$) = 4 cosh$^2$($\beta$) + 6 cosh($\beta$) $-$ 1',
         0.12, y, size=10, color=BLUE)

    # Gráfica de Z(β)
    ax_z = fig.add_axes([0.12, 0.43, 0.75, 0.22])
    ax_z.set_facecolor(BG)
    betas = np.linspace(-4, 4, 500)
    Z_al = 5 + 4*np.cosh(betas)
    Z_m1 = 4*np.cosh(betas)**2 + 6*np.cosh(betas) - 1
    ax_z.plot(betas, Z_al, '-', color=RED, lw=2.0, label=r'$Z_{AL}(\beta)$')
    ax_z.plot(betas, Z_m1, '-', color=BLUE, lw=2.0, label=r'$Z_{M1}(\beta)$')
    ax_z.axvline(0, color=LGRAY, lw=0.6, ls='--')
    ax_z.set_xlabel(r'$\beta$ (temperatura inversa)', fontsize=9)
    ax_z.set_ylabel('Z(β)', fontsize=9)
    ax_z.set_title('Función de partición vs temperatura inversa', fontsize=9.5,
                   color=INK, fontweight='bold')
    ax_z.legend(fontsize=9, framealpha=0.9)
    ax_z.spines[['top','right']].set_visible(False)
    ax_z.set_facecolor(BG)
    ax_z.tick_params(labelsize=8)
    ax_z.yaxis.grid(True, color=LGRAY, lw=0.4, ls='--')
    ax_z.set_axisbelow(True)
    ax_z.text(0, 9+0.5, r'$\beta=0$: T=$\infty$', fontsize=7.5,
              color=GRAY, ha='center', va='bottom')

    y = 0.385
    body(ax,
         'La familia {p_β}_{β∈R} es una curva unidimensional en Δ⁸.  '
         'En β=0 (temperatura infinita), p_β es la distribución uniforme '
         '(máxima entropía).  Al β→±∞, p_β se concentra en los estados de '
         'energía mínima/máxima (temperatura cero).  '
         'Esta curva vive dentro de la familia exponencial canónica de 9 parámetros:',
         y, size=9.5)

    y -= 0.082
    math(ax,
         r'p$_\theta$(s) = exp($\sum_i$ $\theta_i$ f$_i$(s) $-$ A($\theta$))',
         0.5, y, size=10.5, color=PURPLE, ha='center')

    y -= 0.050
    body(ax,
         'donde {f₁,...,f₉} es la base de R⁹ y A(θ) = log Z(θ) es la '
         'log-función de partición (potencial convexa).  '
         'M1 y Alvarado definen líneas rectas en el espacio de parámetros '
         'θ ∈ R⁹:  θ(β) = β · H_M1  ó  β · H_AL.',
         y, size=9.5, color=PURPLE)

    pdf.savefig(fig, bbox_inches='tight')
    plt.close(fig)


# ─────────────────────────────────────────────────────────────────────────────
# PÁGINA 7 — DUALIDAD DE LEGENDRE
# ─────────────────────────────────────────────────────────────────────────────

def page_legendre(pdf):
    fig = plt.figure(figsize=(8.5, 11))
    page_bg(fig)
    ax = blank_ax(fig, [0.08, 0.06, 0.84, 0.90])

    ax.text(0.0, 1.0, '9.  Dualidad de Legendre: Energía ↔ Entropía',
            fontsize=16, fontweight='bold', color=INK, va='top')
    ax.plot([0, 1], [0.965, 0.965], '-', color=GOLD, lw=1.5,
            transform=ax.transAxes)

    y = 0.925
    body(ax,
         'La relación más profunda entre energía, entropía e información '
         'es la dualidad de Legendre–Fenchel.  Son la misma estructura '
         'vista desde coordenadas duales.',
         y, size=9.5)

    # Diagrama de la dualidad
    ax_d = fig.add_axes([0.05, 0.64, 0.90, 0.25])
    ax_d.set_facecolor(BG); ax_d.axis('off')
    ax_d.set_xlim(0,1); ax_d.set_ylim(0,1)

    # Bloque izquierdo
    ax_d.add_patch(FancyBboxPatch((0.02, 0.15), 0.35, 0.70,
                   boxstyle='round,pad=0.02', fc='#EBF5FB', ec=BLUE, lw=1.5))
    ax_d.text(0.195, 0.90, 'Espacio de parámetros',
              ha='center', fontsize=9, color=BLUE, fontweight='bold')
    ax_d.text(0.195, 0.72, r'$\theta$ $\in$ R$^9$', ha='center',
              fontsize=12, color=BLUE)
    ax_d.text(0.195, 0.52, r'A($\theta$) = log Z($\theta$)',
              ha='center', fontsize=9.5, color=BLUE)
    ax_d.text(0.195, 0.38, '(función convexa)', ha='center',
              fontsize=8.5, color=GRAY, fontstyle='italic')
    ax_d.text(0.195, 0.24, r'$\mu$ = $\nabla$A($\theta$) = $\langle$H$\rangle_\theta$',
              ha='center', fontsize=9, color=BLUE)

    # Bloque derecho
    ax_d.add_patch(FancyBboxPatch((0.63, 0.15), 0.35, 0.70,
                   boxstyle='round,pad=0.02', fc='#FDEDEC', ec=RED, lw=1.5))
    ax_d.text(0.805, 0.90, 'Espacio de estados',
              ha='center', fontsize=9, color=RED, fontweight='bold')
    ax_d.text(0.805, 0.72, r'$\mu$ $\in$ $\Delta^8$', ha='center',
              fontsize=12, color=RED)
    ax_d.text(0.805, 0.52, r'S($\mu$) = $-\sum_s$ p$_s$ log p$_s$',
              ha='center', fontsize=9.5, color=RED)
    ax_d.text(0.805, 0.38, '(función cóncava)', ha='center',
              fontsize=8.5, color=GRAY, fontstyle='italic')
    ax_d.text(0.805, 0.24, r'$\theta$ = $\nabla$S($\mu$) = log p$_s$ + cte',
              ha='center', fontsize=9, color=RED)

    # Flechas dobles
    ax_d.annotate('', xy=(0.61, 0.65), xytext=(0.39, 0.65),
                  arrowprops=dict(arrowstyle='<->', color=GOLD, lw=2.0))
    ax_d.text(0.50, 0.72, 'Legendre', ha='center', fontsize=9,
              color=GOLD, fontweight='bold')
    ax_d.annotate('', xy=(0.61, 0.30), xytext=(0.39, 0.30),
                  arrowprops=dict(arrowstyle='<->', color=GOLD, lw=2.0))
    ax_d.text(0.50, 0.22, r'A($\theta$) + S($\mu$) = $\langle\theta, \mu\rangle$',
              ha='center', fontsize=8.5, color=GOLD)

    y = 0.605
    body(ax,
         'Las ecuaciones fundamentales de la dualidad:',
         y, size=9.5, fontweight='bold')

    y -= 0.055
    math(ax,
         r'A($\theta$) = sup$_{\mu \in \Delta^8}$ { $\langle\theta, \mu\rangle$ $-$ S($\mu$) }',
         0.5, y, size=11, color=BLUE, ha='center')
    y -= 0.050
    math(ax,
         r'S($\mu$) = inf$_{\theta \in R^9}$ { $\langle\theta, \mu\rangle$ $-$ A($\theta$) }',
         0.5, y, size=11, color=RED, ha='center')

    y -= 0.058
    body(ax,
         'En coordenadas duales (θ, μ):',
         y, size=9.5)

    rows = [
        ('Energía libre A(θ) = log Z(θ)',
         'Potencial convexo en el espacio de parámetros'),
        ('Entropía S(μ) = −Σ p log p',
         'Transformada de Legendre de A (potencial cóncavo en Δ⁸)'),
        ('Energía esperada μ = ⟨H⟩',
         'Coordenada "primal" — lo que observamos empíricamente'),
        ('Parámetro natural θ',
         'Coordenada "dual" — la β que controla la temperatura'),
        ('Disipación: A(θ) + S(μ) − ⟨θ,μ⟩ ≥ 0',
         'Desigualdad de Young-Fenchel — cero solo en equilibrio'),
    ]

    y -= 0.042
    for concept, meaning in rows:
        ax.text(0.02, y, f'•  {concept}', fontsize=8.5,
                color=BLUE, transform=ax.transAxes, va='top', fontweight='bold')
        ax.text(0.02, y-0.025, f'   {meaning}', fontsize=8.5,
                color=INK, transform=ax.transAxes, va='top')
        y -= 0.062

    y -= 0.010
    body(ax,
         'Lo que medimos como "entropía de Shannon" de la distribución de '
         'energías de enlace es el punto μ ∈ Δ⁸ proyectado al eje de la entropía.  '
         'Lo que calculamos como T_eff es una aproximación al parámetro β.  '
         'La verdadera dualidad dice que si μ crece (más variedad de bonds), '
         'entonces θ disminuye (menor β, mayor temperatura): más energía '
         'disponible ↔ más entropía ↔ mayor temperatura efectiva.',
         y, size=9.5, color=PURPLE)

    pdf.savefig(fig, bbox_inches='tight')
    plt.close(fig)


# ─────────────────────────────────────────────────────────────────────────────
# PÁGINA 8 — GEOMETRÍA DE LA INFORMACIÓN
# ─────────────────────────────────────────────────────────────────────────────

def page_info_geometry(pdf):
    fig = plt.figure(figsize=(8.5, 11))
    page_bg(fig)
    ax = blank_ax(fig, [0.08, 0.06, 0.84, 0.90])

    ax.text(0.0, 1.0, '10. Geometría de la Información',
            fontsize=16, fontweight='bold', color=INK, va='top')
    ax.plot([0, 1], [0.965, 0.965], '-', color=GOLD, lw=1.5,
            transform=ax.transAxes)

    y = 0.925
    body(ax,
         'La dualidad de Legendre equipa al símplex Δ⁸ con una estructura '
         'Riemanniana — la métrica de Fisher–Rao de Amari–Chentsov.  '
         'Esto convierte al espacio de estados en una variedad diferenciable '
         'con geometría intrínseca.',
         y, size=9.5)

    y -= 0.065
    math(ax,
         r'g$_{ij}$(p) = $\sum_{s_0,s_1}$ (1/p(s$_0$,s$_1$)) · '
         r'($\partial$p$_i$/$\partial\theta$) · ($\partial$p$_j$/$\partial\theta$)',
         0.5, y, size=9.5, color=BLUE, ha='center')

    y -= 0.058
    body(ax,
         'También escrita como:  g(θ) = ∇²A(θ)  (Hessiana de la energía libre).',
         y, size=9.5)

    y -= 0.055
    body(ax, 'Propiedades geométricas del espacio de estados (Δ⁸, g):', y,
         size=9.5, fontweight='bold')

    items = [
        ('Curvatura', 'Cero a lo largo de las e-geodésicas (familia exponencial).  '
         'Negativa en general (el símplex es un espacio hiperbólico en la métrica de Fisher).'),
        ('Geodésicas', 'Los caminos de mínima "disipación" entre estados son geodésicas '
         'en la métrica de Fisher.  Relevantes para: actualizaciones bayesianas óptimas, '
         'gradiente natural en aprendizaje de máquina.'),
        ('Divergencia KL', r'D_KL(p||q) = Σ p log(p/q) no es simétrica pero es '
         'el "cuadrado de la distancia" en primer orden: D_KL(p||q) ≈ ½(p−q)ᵀ·g·(p−q).'),
        ('Teorema de Chentsov', 'La métrica de Fisher es la ÚNICA métrica Riemanniana '
         'en Δ⁸ invariante bajo reparametrizaciones suficientes del modelo estadístico.'),
    ]

    for title, text in items:
        y -= 0.045
        ax.text(0.02, y, f'▸  {title}:', fontsize=9.5, color=BLUE,
                transform=ax.transAxes, va='top', fontweight='bold')
        y -= 0.030
        ax.text(0.06, y, text, fontsize=8.5, color=INK,
                transform=ax.transAxes, va='top', wrap=True,
                linespacing=1.4)
        y -= 0.058

    y -= 0.010
    body(ax,
         'Conexión con el proyecto: las curvas de Gibbs de M1 y Alvarado '
         'son dos curvas distintas en la MISMA variedad Riemanniana (Δ⁸, g).  '
         'Su longitud geodésica (distancia entre el estado de alta temperatura '
         'β=0 y el estado de baja temperatura β→∞) es una medida intrínseca '
         'de "cuánta información termodinámica distingue un modelo del otro".  '
         'La correlación r=0.83 entre modelos que encontramos empíricamente '
         'corresponde, en este lenguaje, a la distancia geodésica pequeña '
         'entre las dos curvas en Δ⁸.',
         y, size=9.5, color=PURPLE)

    y -= 0.115
    math(ax,
         r'd$_{Fisher}$(p$_{M1}$, p$_{AL}$) = $\int_0^1$ '
         r'$\sqrt{(\dot\theta)^T g(\theta) \dot\theta}$  dt',
         0.5, y, size=10, color=PURPLE, ha='center')

    y -= 0.055
    body(ax,
         'Esta integral (aún no calculada en el proyecto) cuantificaría '
         'exactamente qué tan diferentes son los dos modelos desde el punto '
         'de vista de la teoría de la información.',
         y, size=9, color=GRAY, fontstyle='italic')

    pdf.savefig(fig, bbox_inches='tight')
    plt.close(fig)


# ─────────────────────────────────────────────────────────────────────────────
# PÁGINA 9 — HOMOLOGÍA PERSISTENTE
# ─────────────────────────────────────────────────────────────────────────────

def page_persistent(pdf):
    fig = plt.figure(figsize=(8.5, 11))
    page_bg(fig)
    ax = blank_ax(fig, [0.08, 0.06, 0.84, 0.90])

    ax.text(0.0, 1.0, '11. Homología Persistente de la Trayectoria',
            fontsize=16, fontweight='bold', color=INK, va='top')
    ax.plot([0, 1], [0.965, 0.965], '-', color=GOLD, lw=1.5,
            transform=ax.transAxes)

    y = 0.925
    body(ax,
         'Cada partida de Go es un camino determinista en el espacio de '
         'configuraciones Ω = {−1,0,+1}^{361} con |Ω| = 3^{361} ≈ 10^{172} estados.  '
         'El Hamiltoniano E: Ω → R es una función de Morse discreta sobre ese espacio.',
         y, size=9.5)

    y -= 0.068
    math(ax,
         r'$\sigma_0$ $\rightarrow$ $\sigma_1$ $\rightarrow$ $\cdots$ $\rightarrow$ '
         r'$\sigma_T$  $\in$  {$-$1,0,+1}$^{361}$',
         0.5, y, size=11, color=BLUE, ha='center')

    y -= 0.062
    body(ax,
         'La filtración por subniveles de energía:',
         y, size=9.5)

    y -= 0.048
    math(ax,
         r'$\Omega_c$ = { estados visitados con E($\sigma_k$) $\leq$ c }',
         0.5, y, size=10.5, color=BLUE, ha='center')

    y -= 0.060
    body(ax,
         'define, al aumentar c, una secuencia de complejos simpliciales '
         'cuya homología cambia.  El código de barras de homología persistente '
         'captura cuándo nacen y mueren componentes, ciclos y cavidades:',
         y, size=9.5)

    # Diagrama de código de barras (esquemático)
    ax_bc = fig.add_axes([0.08, 0.44, 0.84, 0.25])
    ax_bc.set_facecolor(BG)
    ax_bc.set_xlim(-3.5, 5); ax_bc.set_ylim(-0.5, 7.5)
    ax_bc.spines[['top','right']].set_visible(False)
    ax_bc.set_xlabel('c  (nivel de energía)', fontsize=9, color=INK)
    ax_bc.set_title('Código de barras esquemático (barcode) — partida ejemplo',
                    fontsize=9, color=INK, fontweight='bold')
    ax_bc.axvline(0, color=LGRAY, lw=0.6, ls='--')

    # Barras H0 (componentes conexas)
    h0_bars = [(-3, 0.5), (-2.5, 1.2), (-1.8, 3.5), (-0.5, 4.8)]
    for i, (birth, death) in enumerate(h0_bars):
        ax_bc.barh(6.5 - i*0.4, death-birth, left=birth,
                   height=0.3, color=BLUE, alpha=0.8)
    ax_bc.text(-3.4, 6.8, 'H₀ (componentes)', fontsize=8, color=BLUE, va='bottom')

    # Barras H1 (ciclos)
    h1_bars = [(-0.5, 2.0), (0.8, 3.2), (1.5, 4.0)]
    for i, (birth, death) in enumerate(h1_bars):
        ax_bc.barh(3.5 - i*0.5, death-birth, left=birth,
                   height=0.35, color=RED, alpha=0.8)
    ax_bc.text(-3.4, 4.0, 'H₁ (ciclos)', fontsize=8, color=RED, va='bottom')

    # Barra larga (rasgo topológico persistente)
    ax_bc.barh(1.0, 7.5, left=-3, height=0.5, color=GREEN, alpha=0.9)
    ax_bc.text(-3.4, 1.5, 'H₀ esencial', fontsize=8, color=GREEN, va='bottom')
    ax_bc.tick_params(labelsize=8)
    ax_bc.set_facecolor(BG)

    y = 0.390
    body(ax,
         'Interpretación de cada barra [c_birth, c_death]:',
         y, size=9.5, fontweight='bold')

    items = [
        ('H₀ (azul)', 'Componentes conexas del subconjunto de estados visitados '
         'con energía ≤ c.  Nacimiento = cuando aparece una nueva región de baja energía;  '
         'Muerte = cuando dos regiones se fusionan.'),
        ('H₁ (rojo)', 'Ciclos (agujeros 1-dimensionales) en la trayectoria.  '
         'Un ciclo persiste si la trayectoria rodea un pozo de energía sin '
         '"caer" en él.'),
        ('Barras largas', 'Rasgos topológicos robustos — no son ruido, '
         'sino estructura genuina del paisaje energético de la partida.'),
    ]

    for title, text in items:
        y -= 0.042
        ax.text(0.02, y, f'•  {title}:', fontsize=9.5,
                color=BLUE, transform=ax.transAxes, va='top', fontweight='bold')
        ax.text(0.02, y-0.030, text, fontsize=8.5,
                color=INK, transform=ax.transAxes, va='top', linespacing=1.3)
        y -= 0.072

    y -= 0.005
    body(ax,
         'Estado actual: no implementado.  Requeriría una biblioteca de '
         'homología persistente (giotto-tda o gudhi).  '
         'El input natural sería la serie temporal de energías E(σ₀),...,E(σ_T) '
         'de las 2031 partidas ya calculadas en sgf_evolution_by_move.csv.',
         y, size=9, color=GRAY, fontstyle='italic')

    pdf.savefig(fig, bbox_inches='tight')
    plt.close(fig)


# ─────────────────────────────────────────────────────────────────────────────
# PÁGINA 10 — TABLA RESUMEN
# ─────────────────────────────────────────────────────────────────────────────

def page_summary(pdf):
    fig = plt.figure(figsize=(8.5, 11))
    page_bg(fig)
    ax = blank_ax(fig, [0.04, 0.06, 0.92, 0.90])

    ax.text(0.0, 1.0, '12. Tabla Resumen — Estructura Matemática del Proyecto',
            fontsize=14, fontweight='bold', color=INK, va='top')
    ax.plot([0, 1], [0.965, 0.965], '-', color=GOLD, lw=1.5,
            transform=ax.transAxes)

    rows = [
        ('OBSERVABLE / MAGNITUD',
         'ESTRUCTURA MATEMÁTICA',
         'RELACIÓN CON EL JUEGO', True),
        ('H_M1, H_AL (por enlace)',
         'Elementos de R⁹ = R[x,y]/(x³−x, y³−y)',
         'Energía de interacción local entre piedras vecinas', False),
        ('Nivel H=c  (Alvarado)',
         'Cónica / hipérbola  —  género 0',
         'Tipo de interacción entre pares de spins', False),
        ('Nivel H=c  (M1)',
         'Curva cúbica / elíptica  —  género 1',
         'Topología más rica por la asimetría del Hamiltoniano', False),
        ('Valores críticos c₁, c₂',
         'Discriminante de la fibración de Milnor',
         'Energías donde la topología de la fibra cambia', False),
        ('Distribución de enlaces p',
         'Punto en el símplex Δ⁸ ⊂ R⁹',
         'Estado probabilístico del tablero en ese turno', False),
        ('Estado de Gibbs p_β',
         'Curva en Δ⁸ parametrizada por β ∈ R',
         'Distribución de equilibrio a temperatura 1/β', False),
        ('Función de partición Z(β)',
         'Función analítica en β (cosh polinomial)',
         'Normalizadora de la distribución de Gibbs', False),
        ('Energía libre A(θ) = log Z',
         'Potencial convexo en R⁹',
         'Coordenada dual de la entropía (Legendre)', False),
        ('Entropía Shannon S(μ)',
         'Transformada de Legendre de A  (función cóncava en Δ⁸)',
         'Diversidad de tipos de interacción en la posición', False),
        ('Asimetría dE_asym  (M1)',
         'Antisimetrizador (M−Mᵀ)/2 de la matriz de enlace',
         'Direccionalidad: cuánto importa quién "inicia" la interacción', False),
        ('Métrica de Fisher g(θ)',
         'Tensor de Riemann en Δ⁸  (=Hessiana de A)',
         'Geometría intrínseca del espacio de estados', False),
        ('Distancia entre modelos',
         'Longitud geodésica en (Δ⁸, g)',
         'Diferencia informacional profunda M1 vs Alvarado', False),
        ('Trayectoria por partida',
         'Camino en {−1,0,+1}^{361} con función de Morse E',
         'Historia energética completa de la partida', False),
        ('Integral de línea cum_E',
         'Integral ∫ dE a lo largo del camino en Ω',
         'Energía acumulada al turno T', False),
        ('Homología persistente',
         'Código de barras H₀, H₁ de la filtración por subniveles',
         'Topología del paisaje energético (no implementado)', False),
        ('D₄ en aperturas',
         'Acción del grupo diédrico sobre Ω/D₄',
         'Simetría: Q16/D4/Q4/D16 son la misma apertura', False),
        ('Proceso de ramificación',
         'Árbol de prefijos (trie) con peso = frecuencia',
         'Divergencia de aperturas turno a turno', False),
    ]

    y = 0.940
    col_x = [0.0, 0.35, 0.68]
    widths = [0.34, 0.32, 0.32]

    for i, row in enumerate(rows):
        is_header = row[3] if len(row) > 3 else False
        texts = row[:3]

        bg_color = INK if is_header else (BG if i%2==0 else '#EEE9E0')
        ax.add_patch(plt.Rectangle((col_x[0], y-0.032), 0.99, 0.034,
                     fc=bg_color, ec='none', transform=ax.transAxes, zorder=0))

        for j, (text, cx) in enumerate(zip(texts, col_x)):
            ax.text(cx + 0.005, y - 0.004, text,
                    fontsize=7.5 if not is_header else 8,
                    color='white' if is_header else (BLUE if j==1 else INK),
                    transform=ax.transAxes, va='top',
                    fontweight='bold' if is_header else 'normal',
                    clip_on=True)
        y -= 0.038
        if not is_header:
            ax.plot([0, 0.99], [y+0.004, y+0.004], '-', color=LGRAY,
                    lw=0.3, transform=ax.transAxes)

    y -= 0.015
    body(ax,
         'Las magnitudes en azul (estructuras algebraicas) son el lenguaje '
         'en que está escrito el proyecto.  La conexión más elegante: '
         'energía libre A y entropía S son duales de Legendre — '
         'la misma información en coordenadas opuestas.',
         y, size=8.5, color=PURPLE)

    pdf.savefig(fig, bbox_inches='tight')
    plt.close(fig)


# ─────────────────────────────────────────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────────────────────────────────────────

def main():
    print(f'\nGenerando: {OUT}')
    with PdfPages(OUT) as pdf:
        meta = pdf.infodict()
        meta['Title']   = ('Variedades, Topología y Geometría de la Información '
                           'en el Anillo de Spins de Go')
        meta['Author']  = 'Leonardo Jiménez Martínez  ·  Mario Mercado Sánchez'
        meta['Subject'] = ('Análisis algebraico-topológico del modelo de Ising '
                           'aplicado al juego de Go')
        meta['Keywords'] = ('Go, Ising, variedades algebraicas, curvas elípticas, '
                            'geometría de la información, homología persistente')

        page_cover(pdf)
        page_ring(pdf)
        page_matrices(pdf)
        page_vector_support(pdf)
        page_component_analysis(pdf)
        page_symmetry_nullspace(pdf)
        page_varieties(pdf)
        page_critical(pdf)
        page_simplex(pdf)
        page_legendre(pdf)
        page_info_geometry(pdf)
        page_persistent(pdf)
        page_summary(pdf)

    print(f'  Listo: {OUT}  ({13} páginas)')


if __name__ == '__main__':
    main()
