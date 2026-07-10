"""
generate_report_pdf.py
======================
Genera el reporte PDF completo del proyecto:
  - Portada
  - Indice
  - Introduccion y metodologia
  - Los dos modelos (ecuaciones, tablas de interaccion renderizadas)
  - Figuras de comparacion (todas las PNGs del proyecto)
  - Tabla de entropia por los 19 patrones
  - Hallazgos, limites y conclusiones

Salida: results/reporte_completo.pdf
"""

import os, sys
from pathlib import Path
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.gridspec as gridspec
from matplotlib.backends.backend_pdf import PdfPages
from matplotlib.patches import FancyBboxPatch, Rectangle
from matplotlib.lines import Line2D

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from compare_per_bond import (
    H_nuestro, H_alvarado, SPIN_VALS,
    all_bond_energies_nuestro, all_bond_energies_alvarado,
    bond_shannon_entropy, bond_boltzmann_entropy, bond_T_eff,
)
from analysis_patterns import PATTERNS, BOARD_SIZE
from src.go_entropy import board_from_stones

RESULTS = os.path.join(str(Path(__file__).resolve().parents[2]), 'results')
OUT     = os.path.join(RESULTS, 'reporte_completo.pdf')
os.makedirs(RESULTS, exist_ok=True)

PW, PH = 8.27, 11.69   # A4

# ── Paleta ──────────────────────────────────────────────────────────────────
C = {
    'cover_bg':   '#0D1117',
    'cover_text': '#E6EDF3',
    'cover_acc':  '#58A6FF',
    'bg':         '#FFFFFF',
    'bg_alt':     '#F8F9FA',
    'title':      '#0F2044',
    'sec_num':    '#1D4ED8',
    'sec_title':  '#1E3A5F',
    'text':       '#1F2937',
    'muted':      '#6B7280',
    'rule':       '#CBD5E1',
    'M1':         '#1D4ED8',
    'AL':         '#D97706',
    'acc':        '#7C3AED',
    'box_M1':     '#EFF6FF',
    'box_AL':     '#FFFBEB',
    'box_key':    '#F0FDF4',
    'box_warn':   '#FFF7ED',
    'border_M1':  '#BFDBFE',
    'border_AL':  '#FDE68A',
    'border_key': '#86EFAC',
    'border_warn':'#FED7AA',
    'neg2':  '#1848c4',
    'neg1':  '#5ba4f5',
    'zero':  '#D1D5DB',
    'pos1':  '#f58b5b',
    'pos2':  '#c41818',
}

SPINS  = [-1, 0, +1]
SYMB   = {-1: '●', 0: '·', +1: '○'}
ECOL   = {-2: C['neg2'], -1: C['neg1'], 0: C['zero'], 1: C['pos1'], 2: C['pos2']}


# ════════════════════════════════════════════════════════════════════════════
# HELPERS DE ESTILO
# ════════════════════════════════════════════════════════════════════════════

def new_page(bg='white'):
    return plt.figure(figsize=(PW, PH), facecolor=bg)


def hline(ax, y, x0=0.06, x1=0.94, color=None, lw=0.8, transform=None):
    color = color or C['rule']
    t = transform or ax.transAxes
    ax.plot([x0, x1], [y, y], color=color, lw=lw, transform=t, clip_on=False)


def page_header(fig, title, section_tag='', page_color=None):
    """Banda superior de pagina: tag de seccion + titulo."""
    ax = fig.add_axes([0, 0.955, 1, 0.045], facecolor=page_color or C['bg_alt'])
    ax.axis('off')
    if section_tag:
        ax.text(0.03, 0.5, section_tag, ha='left', va='center',
                fontsize=8, color=C['muted'], transform=ax.transAxes)
    ax.text(0.5, 0.5, title, ha='center', va='center',
            fontsize=9, fontweight='bold', color=C['sec_title'],
            transform=ax.transAxes)
    hline(ax, 0.02, color=C['M1'], lw=1.5)


def page_footer(fig, page_num, total):
    ax = fig.add_axes([0, 0, 1, 0.03], facecolor=C['bg_alt'])
    ax.axis('off')
    hline(ax, 0.92, color=C['rule'])
    ax.text(0.5, 0.35,
            'Jimenez Martinez & Mercado Sanchez (Ometitlan)  |  '
            'Paper: Pattern Acquisition and Comparative Analysis in the Game of Go  |  '
            'Jimenez Martinez & Sesma Gonzalez — Journal of Go Studies 2025',
            ha='center', va='center', fontsize=5.5, color=C['muted'],
            transform=ax.transAxes)
    ax.text(0.95, 0.45, f'{page_num} / {total}', ha='right', va='center',
            fontsize=7, color=C['muted'], transform=ax.transAxes)


def text_block(ax, x, y, width, text, fontsize=9, color=None, style='normal',
               weight='normal', ha='left', transform=None):
    t = transform or ax.transAxes
    ax.text(x, y, text, transform=t, ha=ha, va='top',
            fontsize=fontsize, color=color or C['text'],
            style=style, fontweight=weight,
            wrap=True, multialignment='left' if ha == 'left' else ha)


def colored_box(ax, x0, y0, w, h, text, fc, ec, fontsize=9, weight='normal',
                title=None, transform=None):
    t = transform or ax.transAxes
    box = FancyBboxPatch((x0, y0), w, h, boxstyle='round,pad=0.008',
                          fc=fc, ec=ec, lw=1.2, transform=t, clip_on=False)
    ax.add_patch(box)
    ty = y0 + h - 0.012
    if title:
        ax.text(x0 + 0.012, ty, title, transform=t, ha='left', va='top',
                fontsize=fontsize - 0.5, fontweight='bold',
                color=ec, clip_on=False)
        ty -= 0.025
    ax.text(x0 + 0.012, ty, text, transform=t, ha='left', va='top',
            fontsize=fontsize, fontweight=weight, color=C['text'],
            multialignment='left', clip_on=False)


# ════════════════════════════════════════════════════════════════════════════
# 1. PORTADA
# ════════════════════════════════════════════════════════════════════════════

def page_cover(pdf):
    fig = new_page(C['cover_bg'])

    ax = fig.add_axes([0, 0, 1, 1], facecolor=C['cover_bg'])
    ax.axis('off')

    # Banda de color superior
    ax.add_patch(Rectangle((0, 0.88), 1, 0.12,
                            fc=C['M1'], ec='none', transform=ax.transAxes))

    # Titulo
    ax.text(0.5, 0.92,
            'Analisis de Informacion Entropica\nen el Juego de Go',
            ha='center', va='center', fontsize=22, fontweight='bold',
            color='white', transform=ax.transAxes, linespacing=1.4)

    # Subtitulo
    ax.text(0.5, 0.84,
            'Comparacion Clasica de Ising: Modelo M1 vs Atomic-Go (Alvarado 2019)',
            ha='center', va='center', fontsize=11,
            color=C['cover_acc'], transform=ax.transAxes)

    hline(ax, 0.81, color=C['cover_acc'], lw=0.8)

    # Autores
    ax.text(0.5, 0.77,
            'Leonardo Jimenez Martinez  &  Mario Mercado Sanchez',
            ha='center', va='center', fontsize=13, color=C['cover_text'],
            fontweight='bold', transform=ax.transAxes)
    ax.text(0.5, 0.73,
            'Repositorio Ometitlan  |  Universidad Nacional Autonoma de Mexico (UNAM)',
            ha='center', va='center', fontsize=9.5,
            color=C['muted'], transform=ax.transAxes)

    hline(ax, 0.70, color='#30363D')

    # Paper relacionado
    ax.text(0.5, 0.66,
            'Paper relacionado: "Pattern Acquisition and Comparative Analysis in the Game of Go"',
            ha='center', va='center', fontsize=9, color=C['cover_acc'],
            style='italic', transform=ax.transAxes)
    ax.text(0.5, 0.62,
            'Jimenez Martinez & Sesma Gonzalez — Journal of Go Studies, Vol. 19 No. 2, 2025',
            ha='center', va='center', fontsize=9,
            color=C['cover_text'], transform=ax.transAxes)

    # Modelos — cajas
    for xi, (label, eq, clr) in enumerate([
        ('Nuestro Modelo M1',
         'H(si,sj) = si + 2sj - si*sj^2 - si^2*sj',
         C['M1']),
        ('Atomic-Go  (Alvarado)',
         'H(xi,xj) = xi * xj      (mu=0)',
         C['AL']),
    ]):
        bx = 0.05 + xi * 0.50
        ax.add_patch(FancyBboxPatch((bx, 0.44), 0.42, 0.12,
                                    boxstyle='round,pad=0.008',
                                    fc='#161B22', ec=clr, lw=1.5,
                                    transform=ax.transAxes, clip_on=False))
        ax.text(bx + 0.21, 0.545, label,
                ha='center', va='center', fontsize=9.5,
                fontweight='bold', color=clr, transform=ax.transAxes)
        ax.text(bx + 0.21, 0.478, eq,
                ha='center', va='center', fontsize=8.5,
                color='#CDD9E5', transform=ax.transAxes,
                fontfamily='monospace')

    # Resumen en numeros
    stats = [
        ('19', 'patrones de apertura\ncomparados'),
        ('3',  'metricas de entropia\n(Shannon, Boltzmann, T_eff)'),
        ('164', 'jugadas analizadas\nen partida real'),
        ('4',  'representaciones\nde tabla de interaccion'),
    ]
    for ki, (num, lbl) in enumerate(stats):
        kx = 0.05 + ki * 0.235
        ax.text(kx + 0.095, 0.38, num,
                ha='center', va='center', fontsize=26,
                fontweight='bold', color=C['cover_acc'],
                transform=ax.transAxes)
        ax.text(kx + 0.095, 0.33, lbl,
                ha='center', va='center', fontsize=7.5,
                color=C['muted'], transform=ax.transAxes,
                multialignment='center')

    hline(ax, 0.28, color='#30363D')

    # Fecha y origen
    ax.text(0.5, 0.24,
            'Repositorio: github.com/ometitlan/Project-Quantum-Go',
            ha='center', va='center', fontsize=8,
            color=C['muted'], transform=ax.transAxes)
    ax.text(0.5, 0.20, 'Julio 2026',
            ha='center', va='center', fontsize=9,
            color=C['cover_text'], transform=ax.transAxes)

    # Nota al pie
    ax.text(0.5, 0.06,
            'El nombre del repositorio (QuantumGo) es historico.\n'
            'Todos los modelos y analisis de este reporte son 100% clasicos.',
            ha='center', va='center', fontsize=7.5,
            color='#8B949E', style='italic', transform=ax.transAxes,
            multialignment='center')

    pdf.savefig(fig, facecolor=C['cover_bg'])
    plt.close()


# ════════════════════════════════════════════════════════════════════════════
# 2. INDICE
# ════════════════════════════════════════════════════════════════════════════

def page_toc(pdf, page_num, total):
    fig = new_page()
    page_header(fig, 'INDICE DE CONTENIDOS')
    page_footer(fig, page_num, total)

    ax = fig.add_axes([0.07, 0.06, 0.86, 0.88], facecolor='white')
    ax.axis('off')

    ax.text(0.5, 0.97, 'Indice de Contenidos', ha='center', va='top',
            fontsize=18, fontweight='bold', color=C['title'],
            transform=ax.transAxes)
    hline(ax, 0.93, color=C['M1'], lw=2)

    sections = [
        ('1',  'Introduccion y Metodologia', 3),
        ('2',  'Nuestro Modelo M1  (Jimenez Martinez & Mercado Sanchez)', 4),
        ('2.1','  Tabla de interaccion M1 y propiedades', 4),
        ('2.2','  Mapas de energia M1 — 19 patrones', 5),
        ('2.3','  Dashboard M1 — espacio termodinamico', 6),
        ('3',  'Modelo de Referencia: Atomic-Go (Alvarado et al., 2019)', 7),
        ('3.1','  Tabla de interaccion Alvarado y propiedades', 7),
        ('3.2','  Mapas de energia Alvarado — 19 patrones', 8),
        ('3.3','  Dashboard Alvarado — espacio termodinamico', 9),
        ('4',  'Comparacion: Tabla de Interaccion Binaria', 10),
        ('4.1','  Matrices, diferencias y representaciones visuales', 11),
        ('4.2','  Grafo de nodos y flechas dirigidas', 12),
        ('5',  'Comparacion: Analisis de Entropia', 13),
        ('5.1','  Shannon, Boltzmann y T_eff — los 19 patrones', 14),
        ('5.2','  Tabla numerica: 19 patrones', 15),
        ('5.3','  Distribucion de bonos por patron', 16),
        ('6',  'Hallazgos Principales', 17),
        ('7',  'Limites del Marco Actual', 18),
        ('8',  'Conclusiones', 19),
    ]

    y = 0.88
    for num, title, pg in sections:
        is_main = len(num) == 1
        fw  = 'bold' if is_main else 'normal'
        fs  = 10.5 if is_main else 9.5
        col = C['sec_title'] if is_main else C['text']
        ax.text(0.02, y, num, transform=ax.transAxes,
                ha='left', va='top', fontsize=fs,
                fontweight=fw, color=C['M1'])
        ax.text(0.10, y, title, transform=ax.transAxes,
                ha='left', va='top', fontsize=fs,
                fontweight=fw, color=col)
        ax.text(0.94, y, str(pg), transform=ax.transAxes,
                ha='right', va='top', fontsize=fs, color=C['muted'])
        if is_main:
            ax.plot([0.02, 0.94], [y - 0.006, y - 0.006],
                    color=C['rule'], lw=0.5, transform=ax.transAxes)
        y -= 0.048 if is_main else 0.038

    pdf.savefig(fig)
    plt.close()


# ════════════════════════════════════════════════════════════════════════════
# 3. INTRODUCCION
# ════════════════════════════════════════════════════════════════════════════

def page_intro(pdf, page_num, total):
    fig = new_page()
    page_header(fig, 'INTRODUCCION Y METODOLOGIA', 'Seccion 1')
    page_footer(fig, page_num, total)

    ax = fig.add_axes([0.07, 0.06, 0.86, 0.88], facecolor='white')
    ax.axis('off')

    ax.text(0.0, 0.97, '1.  Introduccion y Metodologia',
            transform=ax.transAxes, ha='left', va='top',
            fontsize=15, fontweight='bold', color=C['title'])
    hline(ax, 0.93, color=C['M1'], lw=1.5)

    parrafos = [
        ('Contexto', 'bold', C['sec_title'], 0.90, 11),
        ('El juego de Go es un sistema de dos jugadores sobre un tablero de 19x19 '
         'intersecciones donde las piedras de dos colores (negro y blanco) compiten '
         'por territorio. Su complejidad combinatoria supera al ajedrez en varios '
         'ordenes de magnitud. El presente trabajo aplica el formalismo del modelo '
         'de Ising clasico para cuantificar la estructura energetica de posiciones '
         'de Go y comparar dos interpretaciones fisicas distintas del mismo problema.',
         'normal', C['text'], 0.86, 9),

        ('Objetivo', 'bold', C['sec_title'], 0.74, 11),
        ('Comparar cuantitativamente dos modelos de Ising aplicados al Go: el modelo '
         'propio M1 (Jimenez Martinez & Mercado Sanchez, Ometitlan) y el modelo Atomic-Go '
         '(Alvarado et al., 2019), evaluando sus diferencias en terminos de '
         'interacciones binarias, entropia de Shannon, entropia de Boltzmann y '
         'temperatura efectiva sobre 19 patrones de apertura estandar y una partida '
         'profesional completa.',
         'normal', C['text'], 0.70, 9),

        ('Nota metodologica critica: nivel de analisis por bono', 'bold',
         C['acc'], 0.58, 11),
        ('La comparacion correcta entre los dos modelos se realiza al nivel de BONO '
         'DIRIGIDO: cada par de celdas adyacentes (i -> j) se evalua como una '
         'interaccion binaria independiente. El metodo anterior (nivel de celda) '
         'agregaba los 4 vecinos en una sola cifra, lo cual impedia la comparacion '
         'directa con Alvarado. El analisis por bono revela correctamente la '
         'asimetria de M1 y la invisibilidad del vacio en Alvarado.',
         'normal', C['text'], 0.54, 9),

        ('Mapeo de spins', 'bold', C['sec_title'], 0.42, 11),
        ('Ambos modelos usan el mismo mapeo:  '
         'Negro (piedra B) = -1  |  Vacio (.) = 0  |  Blanco (piedra W) = +1\n'
         'Los 19 patrones de apertura se codifican en tableros 9x9 '
         '(esquina superior izquierda) con las piedras en posiciones estandar '
         'segun la Tabla I del articulo de referencia.',
         'normal', C['text'], 0.38, 9),
    ]

    for item in parrafos:
        txt, fw, col, y, fs = item
        ax.text(0.0, y, txt, transform=ax.transAxes, ha='left', va='top',
                fontsize=fs, fontweight=fw, color=col,
                multialignment='left', wrap=True)

    # Caja de referencia
    colored_box(ax, 0.0, 0.03, 1.0, 0.10,
                'Alvarado, Rojas-Dominguez, Barradas-Bautista (2019). '
                '"Modeling the Game of Go by Ising Hamiltonian, '
                'Deep Belief Networks and Common Fate Graphs". IEEE Access.\n'
                'Jimenez Martinez & Sesma Gonzalez (2025). '
                '"Pattern Acquisition and Comparative Analysis in the Game of Go". '
                'Journal of Go Studies, Vol. 19 No. 2.\n'
                'Repositorio Ometitlan (Jimenez Martinez & Mercado Sanchez): '
                'github.com/ometitlan/Project-Quantum-Go',
                fc='#F1F5F9', ec=C['rule'], fontsize=8,
                title='Referencias')

    pdf.savefig(fig)
    plt.close()


# ════════════════════════════════════════════════════════════════════════════
# 4. LOS DOS MODELOS
# ════════════════════════════════════════════════════════════════════════════

def page_models(pdf, page_num, total):
    fig = new_page()
    page_header(fig, 'LOS DOS MODELOS', 'Seccion 2')
    page_footer(fig, page_num, total)

    ax = fig.add_axes([0.07, 0.06, 0.86, 0.88], facecolor='white')
    ax.axis('off')

    ax.text(0.0, 0.97, '2.  Los Dos Modelos',
            transform=ax.transAxes, ha='left', va='top',
            fontsize=15, fontweight='bold', color=C['title'])
    hline(ax, 0.93, color=C['M1'], lw=1.5)

    # Columna izquierda: M1
    colored_box(ax, 0.0, 0.71, 0.47, 0.20,
        'H(si, sj) = si + 2*sj - si*sj^2 - si^2*sj\n\n'
        'Parametros: h0=1, h1=2, K=-1, L=-1\n'
        'Coef. distancia d=1: 1.00   d=2: 0.25\n'
        'd=3: 0.111   d=4: 0.0625',
        fc=C['box_M1'], ec=C['M1'], fontsize=9,
        title='Nuestro Modelo M1 — Jimenez Martinez & Mercado Sanchez (Ometitlan)')

    props_M1 = [
        '5 valores posibles: {-2, -1, 0, +1, +2}',
        'ASIMETRICO: H(i->j) != H(j->i) para 6/9 pares',
        'VACIO ACTIVO: H(0, xj) = 2*xj != 0',
        'Mismo color (negro-negro): -1 (atraccion)',
        'Colores distintos (negro-blanco): +1 (repulsion)',
        'Kernel Manhattan N4 (4 vecinos cardinales)',
    ]
    for k, p in enumerate(props_M1):
        ax.text(0.02, 0.698 - k * 0.036, '+ ' + p,
                transform=ax.transAxes, ha='left', va='top',
                fontsize=8.5, color=C['text'])

    # Columna derecha: Alvarado
    colored_box(ax, 0.53, 0.71, 0.47, 0.20,
        'H(xi, xj) = xi * xj\n\n'
        'Parametros: wij = 1,  mu = 0\n'
        '(campo externo ausente en Atomic-Go)\n'
        'Molecular-Go usa mu = 1 + CFGs (no implementado)',
        fc=C['box_AL'], ec=C['AL'], fontsize=9,
        title='Atomic-Go — Alvarado et al. (2019)')

    props_AL = [
        '3 valores posibles: {-1, 0, +1}',
        'SIMETRICO: H(i->j) = H(j->i) siempre',
        'VACIO INVISIBLE: H(0, xj) = 0 siempre',
        'Mismo color (negro-negro): +1 (repulsion)',
        'Colores distintos (negro-blanco): -1 (atraccion)',
        'Vecindad N4 (4 vecinos cardinales)',
    ]
    for k, p in enumerate(props_AL):
        ax.text(0.55, 0.698 - k * 0.036, '+ ' + p,
                transform=ax.transAxes, ha='left', va='top',
                fontsize=8.5, color=C['text'])

    hline(ax, 0.47, lw=0.8)

    # Tabla de diferencias
    ax.text(0.0, 0.455, 'Diferencias estructurales clave',
            transform=ax.transAxes, ha='left', va='top',
            fontsize=11, fontweight='bold', color=C['sec_title'])

    headers = ['Propiedad', 'Nuestro M1', 'Alvarado', 'Impacto']
    col_x   = [0.0, 0.26, 0.50, 0.73]
    for xi, h in enumerate(headers):
        ax.text(col_x[xi], 0.422, h, transform=ax.transAxes,
                ha='left', va='top', fontsize=9,
                fontweight='bold', color=C['sec_title'])
    hline(ax, 0.413, color=C['rule'])

    filas = [
        ('Vacio',      'Activo (+-2)', 'Invisible (0)', 'M1 ve influencia,\nAlvarado no'),
        ('Simetria',   'Asimetrico',   'Simetrico',     'Orden importa en M1'),
        ('# valores',  '5',            '3',             'M1 rango mayor'),
        ('S_Shannon\ntabla', '1.465 nats',  '0.995 nats',    'M1 mayor entropia\nabsoluta'),
        ('Mismo color','Atraccion (-1)','Repulsion (+1)', 'Signos opuestos'),
        ('Influencia\nterritorial', 'Si captura', 'No captura', 'Diferencia\nconceptual clave'),
    ]

    for ki, (prop, m1v, alv, imp) in enumerate(filas):
        y = 0.400 - ki * 0.058
        bg = C['bg_alt'] if ki % 2 == 0 else 'white'
        ax.add_patch(Rectangle((0.0, y - 0.006), 1.0, 0.054,
                                fc=bg, ec='none', transform=ax.transAxes))
        ax.text(col_x[0], y, prop, transform=ax.transAxes,
                ha='left', va='top', fontsize=8.5, color=C['text'])
        ax.text(col_x[1], y, m1v, transform=ax.transAxes,
                ha='left', va='top', fontsize=8.5,
                color=C['M1'], fontweight='bold')
        ax.text(col_x[2], y, alv, transform=ax.transAxes,
                ha='left', va='top', fontsize=8.5,
                color=C['AL'], fontweight='bold')
        ax.text(col_x[3], y, imp, transform=ax.transAxes,
                ha='left', va='top', fontsize=8, color=C['muted'])

    pdf.savefig(fig)
    plt.close()


# ════════════════════════════════════════════════════════════════════════════
# 4b. PAGINA DEDICADA — NUESTRO MODELO M1
# ════════════════════════════════════════════════════════════════════════════

def page_model_M1(pdf, page_num, total):
    fig = new_page()
    page_header(fig, 'NUESTRO MODELO M1 — JIMENEZ MARTINEZ & MERCADO SANCHEZ',
                'Seccion 2')
    page_footer(fig, page_num, total)

    ax = fig.add_axes([0.07, 0.06, 0.86, 0.88], facecolor='white')
    ax.axis('off')

    ax.text(0.0, 0.97, '2.  Nuestro Modelo M1',
            transform=ax.transAxes, ha='left', va='top',
            fontsize=15, fontweight='bold', color=C['title'])
    ax.text(0.0, 0.930, 'Jimenez Martinez & Mercado Sanchez  |  Repositorio Ometitlan',
            transform=ax.transAxes, ha='left', va='top',
            fontsize=9, color=C['muted'], style='italic')
    hline(ax, 0.916, color=C['M1'], lw=1.5)

    # Ecuacion destacada
    colored_box(ax, 0.0, 0.820, 1.0, 0.088,
        'H(si, sj)  =  si  +  2*sj  -  si*sj^2  -  si^2*sj\n'
        'Parametros: h0 = 1  |  h1 = 2  |  K = -1  |  L = -1\n'
        'Coeficientes de distancia: coef(d=1) = 1.000  |  coef(d=2) = 0.250  '
        '|  coef(d) = 1 / d^2',
        fc=C['box_M1'], ec=C['M1'], fontsize=10, weight='bold',
        title='Hamiltoniano M1 (bono dirigido si -> sj)')

    # Tabla 3x3 renderizada
    ax.text(0.0, 0.800, 'Tabla de interaccion binaria — H(si, sj):',
            transform=ax.transAxes, ha='left', va='top',
            fontsize=10, fontweight='bold', color=C['sec_title'])

    spins = [-1, 0, +1]
    symb  = {-1: '●', 0: '·', +1: '○'}
    ecol  = {-2: '#1848c4', -1: '#5ba4f5', 0: '#D1D5DB', 1: '#f58b5b', 2: '#c41818'}
    bx, by, bw, bh = 0.0, 0.570, 0.40, 0.220
    cell_w = bw / 4
    cell_h = bh / 4
    for ci, s1 in enumerate(spins):
        cx = bx + cell_w * (ci + 1) + cell_w / 2
        cy = by + bh - cell_h / 2
        ax.text(cx, cy, symb[s1], transform=ax.transAxes,
                ha='center', va='center', fontsize=16, fontweight='bold')
    for ri, s0 in enumerate(spins):
        rx = bx + cell_w / 2
        ry = by + bh - cell_h * (ri + 2) + cell_h / 2
        ax.text(rx, ry, symb[s0], transform=ax.transAxes,
                ha='center', va='center', fontsize=16, fontweight='bold')
        for ci, s1 in enumerate(spins):
            h  = H_nuestro(s0, s1)
            v  = int(round(h))
            fc = ecol.get(v, '#ccc')
            cx = bx + cell_w * (ci + 1)
            cy = by + bh - cell_h * (ri + 2)
            box = FancyBboxPatch((cx + 0.005, cy + 0.005),
                                  cell_w - 0.010, cell_h - 0.010,
                                  boxstyle='round,pad=0.005',
                                  fc=fc, ec='white', lw=1.2, alpha=0.92,
                                  transform=ax.transAxes, clip_on=False)
            ax.add_patch(box)
            tc = 'white' if v in (-2, -1) else ('#111' if v != 0 else '#999')
            ax.text(cx + cell_w / 2, cy + cell_h / 2,
                    f'{v:+d}' if v != 0 else '0',
                    transform=ax.transAxes, ha='center', va='center',
                    fontsize=14, fontweight='bold', color=tc)

    # Propiedades en columna derecha
    props = [
        ('Rango de valores', '{-2, -1, 0, +1, +2}  (5 estados)'),
        ('Simetria',         'ASIMETRICO: H(i->j) != H(j->i) en 6/9 pares'),
        ('Vacio (s=0)',      'ACTIVO: H(0,xj) = 2*xj != 0'),
        ('Negro-Negro (●●)', 'H = -1  (atraccion — piedras del mismo color se atraen)'),
        ('Blanco-Blanco (○○)','H = -1  (atraccion)'),
        ('Negro-Blanco (●○)', 'H = +1  (repulsion entre colores distintos)'),
        ('Vacio-Negro (·●)',  'H = -2  (el vacio siente la piedra negra)'),
        ('Vacio-Blanco (·○)', 'H = +2  (el vacio siente la piedra blanca)'),
        ('Negro-Vacio (●·)',  'H = 0   (piedra ignora el vacio adyacente)'),
        ('Kernel',           'Manhattan-4 (4 vecinos cardinales, d=1)'),
        ('Entropia S_Shannon\ntabla (9 pares)', '1.465 nats'),
    ]

    for k, (lbl, val) in enumerate(props):
        y = 0.790 - k * 0.072
        ax.text(0.42, y, lbl + ':', transform=ax.transAxes,
                ha='left', va='top', fontsize=8.5,
                fontweight='bold', color=C['sec_title'])
        ax.text(0.42, y - 0.028, val, transform=ax.transAxes,
                ha='left', va='top', fontsize=8.5, color=C['text'])

    # Caja de interpretacion fisica
    colored_box(ax, 0.0, 0.03, 1.0, 0.135,
        'El modelo M1 captura la INFLUENCIA TERRITORIAL: las celdas vacias adyacentes '
        'a una piedra negra reciben energia -2 (atraccion), las adyacentes a una piedra '
        'blanca reciben +2 (repulsion). Esto modela el campo de influencia que ejerce un '
        'grupo sobre el espacio circundante, concepto central en la estrategia de Go.\n'
        'La asimetria direccional (H(i->j) != H(j->i)) captura que el rol de "origen" '
        'y "destino" de la interaccion es distinto, coherente con el Hamiltoniano de campo.',
        fc=C['box_M1'], ec=C['M1'], fontsize=8.5,
        title='Interpretacion fisica')

    pdf.savefig(fig)
    plt.close()


# ════════════════════════════════════════════════════════════════════════════
# 4c. PAGINA DEDICADA — MODELO ALVARADO
# ════════════════════════════════════════════════════════════════════════════

def page_model_alvarado(pdf, page_num, total):
    fig = new_page()
    page_header(fig, 'MODELO ALVARADO — ATOMIC-GO', 'Seccion 3')
    page_footer(fig, page_num, total)

    ax = fig.add_axes([0.07, 0.06, 0.86, 0.88], facecolor='white')
    ax.axis('off')

    ax.text(0.0, 0.97, '3.  Modelo de Referencia: Atomic-Go (Alvarado et al., 2019)',
            transform=ax.transAxes, ha='left', va='top',
            fontsize=14, fontweight='bold', color=C['title'])
    ax.text(0.0, 0.930,
            'Rojas-Dominguez, Barradas-Bautista & Alvarado  |  IEEE Access, 2019',
            transform=ax.transAxes, ha='left', va='top',
            fontsize=9, color=C['muted'], style='italic')
    hline(ax, 0.916, color=C['AL'], lw=1.5)

    # Ecuacion
    colored_box(ax, 0.0, 0.820, 1.0, 0.088,
        'H(xi, xj)  =  xi * xj\n'
        'Parametros: mu = 0  (sin campo externo)  |  wij = 1  (pesos uniformes)\n'
        'Tres variantes del paper: Atomic-Go (mu=0), Generative (DBN), '
        'Molecular-Go (mu=1, CFGs)',
        fc=C['box_AL'], ec=C['AL'], fontsize=10, weight='bold',
        title='Hamiltoniano Alvarado (bono dirigido xi -> xj)')

    ax.text(0.0, 0.800, 'Tabla de interaccion binaria — H(xi, xj):',
            transform=ax.transAxes, ha='left', va='top',
            fontsize=10, fontweight='bold', color=C['sec_title'])

    # Tabla 3x3 para Alvarado
    spins = [-1, 0, +1]
    symb  = {-1: '●', 0: '·', +1: '○'}
    ecol  = {-1: '#5ba4f5', 0: '#D1D5DB', 1: '#f58b5b'}
    bx, by, bw, bh = 0.0, 0.570, 0.40, 0.220
    cell_w = bw / 4
    cell_h = bh / 4
    for ci, s1 in enumerate(spins):
        cx = bx + cell_w * (ci + 1) + cell_w / 2
        cy = by + bh - cell_h / 2
        ax.text(cx, cy, symb[s1], transform=ax.transAxes,
                ha='center', va='center', fontsize=16, fontweight='bold')
    for ri, s0 in enumerate(spins):
        rx = bx + cell_w / 2
        ry = by + bh - cell_h * (ri + 2) + cell_h / 2
        ax.text(rx, ry, symb[s0], transform=ax.transAxes,
                ha='center', va='center', fontsize=16, fontweight='bold')
        for ci, s1 in enumerate(spins):
            h  = H_alvarado(s0, s1)
            v  = int(round(h))
            fc = ecol.get(v, '#ccc')
            cx = bx + cell_w * (ci + 1)
            cy = by + bh - cell_h * (ri + 2)
            box = FancyBboxPatch((cx + 0.005, cy + 0.005),
                                  cell_w - 0.010, cell_h - 0.010,
                                  boxstyle='round,pad=0.005',
                                  fc=fc, ec='white', lw=1.2, alpha=0.92,
                                  transform=ax.transAxes, clip_on=False)
            ax.add_patch(box)
            tc = 'white' if v == -1 else ('#111' if v != 0 else '#999')
            ax.text(cx + cell_w / 2, cy + cell_h / 2,
                    f'{v:+d}' if v != 0 else '0',
                    transform=ax.transAxes, ha='center', va='center',
                    fontsize=14, fontweight='bold', color=tc)

    # Propiedades en columna derecha
    props_al = [
        ('Rango de valores',  '{-1, 0, +1}  (3 estados)'),
        ('Simetria',          'SIMETRICO: H(i->j) = H(j->i) siempre'),
        ('Vacio (x=0)',       'INVISIBLE: H(0, xj) = 0 siempre'),
        ('Negro-Negro (●●)',  'H = +1  (repulsion — mismo color se repele)'),
        ('Blanco-Blanco (○○)','H = +1  (repulsion)'),
        ('Negro-Blanco (●○)', 'H = -1  (atraccion entre colores distintos)'),
        ('Vacio con cualq.',  'H = 0   (vacio no interactua con nadie)'),
        ('Kernel',            'Manhattan-4 (4 vecinos cardinales)'),
        ('Implementado aqui', 'Solo Atomic-Go (mu=0)'),
        ('Entropia S_Shannon\ntabla (9 pares)', '0.995 nats'),
    ]

    for k, (lbl, val) in enumerate(props_al):
        y = 0.790 - k * 0.075
        ax.text(0.42, y, lbl + ':', transform=ax.transAxes,
                ha='left', va='top', fontsize=8.5,
                fontweight='bold', color=C['sec_title'])
        ax.text(0.42, y - 0.028, val, transform=ax.transAxes,
                ha='left', va='top', fontsize=8.5, color=C['text'])

    # Caja de interpretacion fisica
    colored_box(ax, 0.0, 0.03, 1.0, 0.130,
        'El modelo Atomic-Go interpreta el Go como una red de SPINS CLASICOS donde '
        'las interacciones son puramente multiplicativas. El vacio (x=0) no participa '
        'en ninguna interaccion — equivalente a no existir en la red. Esto significa '
        'que el modelo solo "ve" las piedras ya colocadas, ignorando el espacio libre '
        'que rodea a los grupos.\n'
        'La REPULSION entre piedras del mismo color (H=+1) refleja la convencion '
        'antiferromagnetica: estados de baja energia son los que mezclan colores. '
        'Esto es fisicamente opuesto al modelo M1, donde el mismo color se atrae.',
        fc=C['box_AL'], ec=C['AL'], fontsize=8.5,
        title='Interpretacion fisica')

    pdf.savefig(fig)
    plt.close()


# ════════════════════════════════════════════════════════════════════════════
# 5. TABLAS DE INTERACCION RENDERIZADAS
# ════════════════════════════════════════════════════════════════════════════

def page_interaction_matrices(pdf, page_num, total):
    fig = new_page()
    page_header(fig, 'TABLA DE INTERACCION BINARIA (MATRICES)', 'Seccion 3')
    page_footer(fig, page_num, total)

    ax = fig.add_axes([0.07, 0.06, 0.86, 0.88], facecolor='white')
    ax.axis('off')

    ax.text(0.0, 0.97, '3.  Tabla de Interaccion Binaria',
            transform=ax.transAxes, ha='left', va='top',
            fontsize=15, fontweight='bold', color=C['title'])
    hline(ax, 0.93, color=C['M1'], lw=1.5)

    ax.text(0.0, 0.905,
            'Cada celda es la energia de UN bono dirigido (si -> sj) evaluado '
            'independientemente.\nLas matrices se leen: fila = origen (si), '
            'columna = destino (sj).',
            transform=ax.transAxes, ha='left', va='top',
            fontsize=9, color=C['text'])

    def draw_matrix(func, title, bx, by, bw, bh, color):
        MA = np.array([[func(s0, s1) for s1 in SPINS] for s0 in SPINS])

        # Titulo
        ax.text(bx + bw/2, by + bh + 0.018, title,
                transform=ax.transAxes, ha='center', va='bottom',
                fontsize=10, fontweight='bold', color=color)

        cell_w = bw / 4
        cell_h = bh / 4

        labels_col = [SYMB[s] for s in SPINS]
        labels_row = [SYMB[s] for s in SPINS]

        # Cabecera columnas
        for ci, lbl in enumerate(labels_col):
            cx = bx + cell_w * (ci + 1) + cell_w/2
            cy = by + bh - cell_h/2
            ax.text(cx, cy, lbl, transform=ax.transAxes,
                    ha='center', va='center', fontsize=14, fontweight='bold',
                    color='#222')

        # Cabecera filas
        for ri, lbl in enumerate(labels_row):
            rx = bx + cell_w/2
            ry = by + bh - cell_h * (ri + 2) + cell_h/2
            ax.text(rx, ry, lbl, transform=ax.transAxes,
                    ha='center', va='center', fontsize=14, fontweight='bold',
                    color='#222')

        # Celdas
        for ri, s0 in enumerate(SPINS):
            for ci, s1 in enumerate(SPINS):
                h = func(s0, s1)
                v = int(round(h))
                fc = ECOL.get(v, '#ccc')
                cx = bx + cell_w * (ci + 1)
                cy = by + bh - cell_h * (ri + 2)

                box = FancyBboxPatch((cx + 0.004, cy + 0.004),
                                     cell_w - 0.008, cell_h - 0.008,
                                     boxstyle='round,pad=0.004',
                                     fc=fc, ec='white', lw=1.0, alpha=0.9,
                                     transform=ax.transAxes, clip_on=False)
                ax.add_patch(box)
                tc = 'white' if v in (-2, -1) else ('#111' if v != 0 else '#999')
                label = f'{v:+d}' if v != 0 else '0'
                ax.text(cx + cell_w/2, cy + cell_h/2, label,
                        transform=ax.transAxes, ha='center', va='center',
                        fontsize=13, fontweight='bold', color=tc)

    # Matriz M1
    draw_matrix(H_nuestro, 'Nuestro Modelo M1', 0.02, 0.48, 0.42, 0.36, C['M1'])

    # Matriz Alvarado
    draw_matrix(H_alvarado, 'Alvarado Atomic-Go', 0.56, 0.48, 0.42, 0.36, C['AL'])

    # Matriz diferencia
    def H_diff(s0, s1):
        return H_nuestro(s0, s1) - H_alvarado(s0, s1)

    ECOL_diff = {-3:'#0a2a8c',-2:C['neg2'],-1:C['neg1'],
                  0:C['zero'], 1:C['pos1'], 2:C['pos2'], 3:'#7a0a0a'}
    old_ecol = ECOL.copy()
    ECOL.update(ECOL_diff)
    draw_matrix(H_diff, 'Diferencia  (M1 - Alvarado)', 0.28, 0.07, 0.42, 0.36, C['acc'])
    ECOL.update(old_ecol)

    # Leyenda de colores
    for k, (v, lbl) in enumerate([(-2,'Atraccion fuerte'),(-1,'Atraccion debil'),
                                    (0,'Sin interaccion'),(1,'Repulsion debil'),
                                    (2,'Repulsion fuerte')]):
        kx = 0.02 + k * 0.19
        ax.add_patch(FancyBboxPatch((kx, 0.038), 0.015, 0.018,
                                     boxstyle='round,pad=0.003',
                                     fc=ECOL[v], ec='white',
                                     transform=ax.transAxes))
        label = f'{v:+d}  {lbl}' if v != 0 else f'0  {lbl}'
        ax.text(kx + 0.019, 0.049, label, transform=ax.transAxes,
                ha='left', va='center', fontsize=7.5, color=C['text'])

    pdf.savefig(fig)
    plt.close()


# ════════════════════════════════════════════════════════════════════════════
# 6. FIGURA EXISTENTE
# ════════════════════════════════════════════════════════════════════════════

def page_figure(pdf, img_path, section_tag, fig_title, caption, page_num, total):
    if not os.path.exists(img_path):
        print(f"  [omitida] no encontrada: {img_path}")
        return
    img = plt.imread(img_path)

    fig = new_page()
    page_header(fig, fig_title.upper(), section_tag)
    page_footer(fig, page_num, total)

    # Area de imagen
    ih, iw = img.shape[:2]
    aspect = ih / iw
    avail_w, avail_h = 0.86, 0.82
    if aspect * avail_w <= avail_h:
        disp_w = avail_w
        disp_h = aspect * avail_w
    else:
        disp_h = avail_h
        disp_w = avail_h / aspect

    x0 = (1 - disp_w) / 2
    y0 = 0.06 + (avail_h - disp_h) / 2 + 0.04

    ax_img = fig.add_axes([x0, y0, disp_w, disp_h])
    ax_img.imshow(img, aspect='auto', interpolation='bilinear')
    ax_img.axis('off')

    # Titulo de figura
    ax_t = fig.add_axes([0.07, y0 + disp_h + 0.005, 0.86, 0.025])
    ax_t.axis('off')
    ax_t.text(0.5, 0.5, fig_title, ha='center', va='center',
              fontsize=10, fontweight='bold', color=C['sec_title'],
              transform=ax_t.transAxes)

    # Caption
    if caption:
        ax_c = fig.add_axes([0.07, 0.065, 0.86, 0.045])
        ax_c.axis('off')
        ax_c.add_patch(Rectangle((0, 0), 1, 1,
                                   fc='#F1F5F9', ec=C['rule'],
                                   transform=ax_c.transAxes, lw=0.8))
        ax_c.text(0.02, 0.5, caption, ha='left', va='center',
                  fontsize=7.5, color=C['muted'], transform=ax_c.transAxes,
                  multialignment='left')

    pdf.savefig(fig)
    plt.close()


# ════════════════════════════════════════════════════════════════════════════
# 7. TABLA NUMERICA — 19 PATRONES
# ════════════════════════════════════════════════════════════════════════════

def page_pattern_table(pdf, page_num, total):
    records = []
    for pid, desc, stones in PATTERNS:
        board = board_from_stones(BOARD_SIZE, stones)
        bM1 = all_bond_energies_nuestro(board)
        bAL = all_bond_energies_alvarado(board)
        T_M = bond_T_eff(bM1); T_A = bond_T_eff(bAL)
        records.append({
            'id': pid, 'desc': desc[:26], 'n': len(stones),
            'Ssh_M1': bond_shannon_entropy(bM1),
            'Ssh_AL': bond_shannon_entropy(bAL),
            'Sbo_M1': bond_boltzmann_entropy(bM1),
            'Sbo_AL': bond_boltzmann_entropy(bAL),
            'T_M1':  T_M if np.isfinite(T_M) else 999,
            'T_AL':  T_A if np.isfinite(T_A) else 999,
        })

    fig = new_page()
    page_header(fig, 'ENTROPIA POR LOS 19 PATRONES DE APERTURA', 'Seccion 4.3')
    page_footer(fig, page_num, total)

    ax = fig.add_axes([0.04, 0.06, 0.92, 0.88], facecolor='white')
    ax.axis('off')

    ax.text(0.0, 0.97, '4.3  Tabla numerica — 19 patrones',
            transform=ax.transAxes, ha='left', va='top',
            fontsize=14, fontweight='bold', color=C['title'])
    hline(ax, 0.930, color=C['M1'], lw=1.5)

    headers = ['ID', 'Descripcion', 'N', 'S_sh M1', 'S_sh AL',
               'DS_sh', 'S_bo M1', 'S_bo AL', 'T_eff M1', 'T_eff AL']
    cols_x  = [0.00, 0.05, 0.33, 0.39, 0.47, 0.55, 0.63, 0.71, 0.81, 0.90]

    for xi, h in zip(cols_x, headers):
        ax.text(xi, 0.912, h, transform=ax.transAxes,
                ha='left', va='top', fontsize=7.5,
                fontweight='bold', color=C['sec_title'])
    hline(ax, 0.900, color=C['M1'], lw=1.2)

    for ki, r in enumerate(records):
        y = 0.888 - ki * 0.043
        bg = C['bg_alt'] if ki % 2 == 0 else 'white'
        ax.add_patch(Rectangle((0, y - 0.002), 1.0, 0.042,
                                fc=bg, ec='none', transform=ax.transAxes))

        vals = [
            r['id'], r['desc'], str(r['n']),
            f"{r['Ssh_M1']:.3f}", f"{r['Ssh_AL']:.3f}",
            f"{r['Ssh_M1']-r['Ssh_AL']:+.3f}",
            f"{r['Sbo_M1']:.2f}", f"{r['Sbo_AL']:.2f}",
            'inf' if r['T_M1'] > 90 else f"{r['T_M1']:.2f}",
            'inf' if r['T_AL'] > 90 else f"{r['T_AL']:.2f}",
        ]
        colors = [C['text'], C['text'], C['muted'],
                  C['M1'], C['AL'],
                  C['M1'] if r['Ssh_M1'] > r['Ssh_AL'] else C['AL'],
                  C['M1'], C['AL'], C['muted'], C['muted']]

        for xi, (v, col) in zip(cols_x, zip(vals, colors)):
            ax.text(xi, y + 0.030, v, transform=ax.transAxes,
                    ha='left', va='top', fontsize=7.5, color=col)

    hline(ax, 0.888 - 19 * 0.043, color=C['rule'])

    # Resumen
    S_sh_M1 = np.array([r['Ssh_M1'] for r in records])
    S_sh_AL = np.array([r['Ssh_AL'] for r in records])
    ry = 0.888 - 19 * 0.043 - 0.04
    colored_box(ax, 0.0, ry - 0.07, 1.0, 0.07,
        f'M1 > Alvarado en 19/19 patrones  |  '
        f'Brecha media: {np.mean(S_sh_M1-S_sh_AL):.4f} nats  |  '
        f'Correlacion entre modelos: r = {np.corrcoef(S_sh_M1, S_sh_AL)[0,1]:.3f}  |  '
        f'M1 media: {S_sh_M1.mean():.4f}  |  Alvarado media: {S_sh_AL.mean():.4f}',
        fc=C['box_key'], ec=C['border_key'], fontsize=8.5,
        title='Resumen S_Shannon')

    pdf.savefig(fig)
    plt.close()


# ════════════════════════════════════════════════════════════════════════════
# 8. HALLAZGOS PRINCIPALES
# ════════════════════════════════════════════════════════════════════════════

def page_findings(pdf, page_num, total):
    fig = new_page()
    page_header(fig, 'HALLAZGOS PRINCIPALES', 'Seccion 6')
    page_footer(fig, page_num, total)

    ax = fig.add_axes([0.07, 0.06, 0.86, 0.88], facecolor='white')
    ax.axis('off')

    ax.text(0.0, 0.97, '6.  Hallazgos Principales',
            transform=ax.transAxes, ha='left', va='top',
            fontsize=15, fontweight='bold', color=C['title'])
    hline(ax, 0.930, color=C['M1'], lw=1.5)

    findings = [
        (C['box_M1'],  C['M1'],
         'H1 — M1 supera a Alvarado en entropia de Shannon (19/19 patrones)',
         'El modelo M1 asigna mayor entropia de Shannon a los 19 patrones de apertura '
         'estudiados, con una brecha media de 1.92 nats. La razon es que M1 incluye '
         'las interacciones de las celdas vacias con las piedras vecinas, aportando '
         'valores de bono +-2 que amplian la distribucion. Alvarado asigna S=0 a '
         'patrones con piedras aisladas porque todos sus bonos son cero (vacio invisible).'),
        (C['box_AL'],  C['AL'],
         'H2 — Los modelos concuerdan en complejidad relativa (r = 0.83)',
         'La correlacion de Pearson entre las entropias de Shannon de ambos modelos '
         'sobre los 19 patrones es r = 0.83. Los patrones que un modelo considera '
         'complejos tambien lo son para el otro. La diferencia es de escala y de '
         'que interacciones se cuentan, no de que patrones son mas ricos.'),
        ('#F0FDF4', '#15803D',
         'H3 — Signos invertidos en interaccion mismo-color',
         'El desacuerdo cualitativo mas importante: M1 asigna -1 (atraccion) a '
         'pares negro-negro y blanco-blanco. Alvarado asigna +1 (repulsion). '
         'Los modelos interpretan la relacion entre piedras del mismo color '
         'de manera fisicamente opuesta. En M1 las piedras del mismo color '
         'se agrupan energeticamente; en Alvarado se repelen.'),
        (C['box_warn'], '#B45309',
         'H4 — El marco de Ising no captura el enfriamiento termodinámico de Go',
         'La temperatura efectiva T_eff = sigma^2(E)/|mean(E)| permanece cercana '
         'a infinito durante toda la partida real analizada. Razon: la coexistencia '
         'obligatoria de dos colores mantiene mean(E) cerca de cero, haciendo '
         'divergir T_eff. La entropia de Shannon crece con el numero de piedras '
         '(mas bonos activos), no con la complejidad estrategica. El enfriamiento '
         'del Go existe, pero en la variable "valor del siguiente movimiento", '
         'no en la distribucion de energias de bono.'),
        ('#FAF5FF', C['acc'],
         'H5 — Los modelos convergen al llenarse el tablero',
         'La brecha delta_S = S_M1 - S_Alvarado se reduce desde ~1.7 nats al inicio '
         'de la partida hasta ~0.8 nats al final. Conforme el tablero se llena, '
         'la proporcion de bonos piedra-piedra (evaluados de forma similar por '
         'ambos modelos) crece frente a los bonos vacio-piedra (solo visibles '
         'para M1). Los modelos convergen en el yose (final de partida).'),
    ]

    y = 0.91
    for fc, ec, title, body in findings:
        h = 0.12 if len(body) < 200 else 0.145
        colored_box(ax, 0.0, y - h, 1.0, h,
                    body, fc=fc, ec=ec, fontsize=8.5, title=title)
        y -= h + 0.018

    pdf.savefig(fig)
    plt.close()


# ════════════════════════════════════════════════════════════════════════════
# 9. LIMITES
# ════════════════════════════════════════════════════════════════════════════

def page_limits(pdf, page_num, total):
    fig = new_page()
    page_header(fig, 'LIMITES DEL MARCO ACTUAL', 'Seccion 7')
    page_footer(fig, page_num, total)

    ax = fig.add_axes([0.07, 0.06, 0.86, 0.88], facecolor='white')
    ax.axis('off')

    ax.text(0.0, 0.97, '7.  Limites del Marco Actual',
            transform=ax.transAxes, ha='left', va='top',
            fontsize=15, fontweight='bold', color=C['title'])
    hline(ax, 0.930, color=C['M1'], lw=1.5)

    limits = [
        ('L1', 'T_eff no captura el enfriamiento estrategico de Go',
         'La formula T_eff = sigma^2/|mean| diverge cuando los dos colores '
         'balancean las interacciones (mean aprox 0). Para capturar el enfriamiento '
         'del juego se necesitaria una variable que mida la claridad territorial: '
         'por ejemplo la entropia de la distribucion de ownership (a quien pertenece '
         'cada interseccion), que si deberia decrecer al establecerse el territorio.'),
        ('L2', 'S_Shannon crece mecanicamente con el numero de jugadas',
         'Parte del crecimiento de S_Shannon durante la partida es simplemente que '
         'hay mas bonos activos, no que la posicion sea mas compleja. Para aislar '
         'la complejidad seria necesario normalizar por el numero de bonos activos '
         'o calcular la entropia por bono en lugar de sobre todos los bonos del tablero.'),
        ('L3', 'S_Boltzmann no distingue los modelos a nivel de tabla completa',
         'Cuando T_eff -> inf, la distribucion de Gibbs se vuelve uniforme y '
         'S_Boltzmann -> ln(N). Ambos modelos dan S_Boltzmann aprox ln(9) sobre '
         'los 9 pares base porque sus promedios de energia son cero. Solo en '
         'patrones con piedras aisladas (T_eff bajo, como patron 1b con T=0.17) '
         'aparece diferenciacion entre modelos.'),
        ('L4', 'El modelo Alvarado comparado es solo Atomic-Go, no Molecular-Go',
         'El paper de Alvarado et al. describe tres variantes: Atomic-Go (mu=0), '
         'Generative Atomic-Go (+ red bayesiana profunda) y Molecular-Go (mu=1, '
         'CFGs, pesos tacticos). Solo se implemento Atomic-Go. Molecular-Go '
         'incluye evaluacion de ojos, redes y escaleras con pesos distintos, '
         'lo que cambiaria sustancialmente el espacio de valores de energia.'),
    ]

    y = 0.91
    for code, title, body in limits:
        h = 0.16
        colored_box(ax, 0.0, y - h, 1.0, h,
                    body, fc='#FFF7ED', ec='#F59E0B', fontsize=8.5,
                    title=f'{code} — {title}')
        y -= h + 0.022

    # Trabajo futuro
    hline(ax, y - 0.01, color=C['rule'])
    ax.text(0.0, y - 0.03, 'Trabajo futuro sugerido',
            transform=ax.transAxes, ha='left', va='top',
            fontsize=11, fontweight='bold', color=C['sec_title'])
    future = [
        'Calcular entropia de ownership y verificar si decrece durante la partida.',
        'Normalizar S_Shannon por log(N_bonos_activos) para comparar posiciones de diferente densidad.',
        'Implementar Molecular-Go (mu=1) e incluirlo en la comparacion.',
        'Explorar una definicion de T_eff basada en gradiente territorial en lugar de media de energia.',
    ]
    for k, f in enumerate(future):
        ax.text(0.02, y - 0.06 - k * 0.04, f'- {f}',
                transform=ax.transAxes, ha='left', va='top',
                fontsize=8.5, color=C['text'])

    pdf.savefig(fig)
    plt.close()


# ════════════════════════════════════════════════════════════════════════════
# 10. CONCLUSIONES
# ════════════════════════════════════════════════════════════════════════════

def page_conclusions(pdf, page_num, total):
    fig = new_page()
    page_header(fig, 'CONCLUSIONES', 'Seccion 8')
    page_footer(fig, page_num, total)

    ax = fig.add_axes([0.07, 0.06, 0.86, 0.88], facecolor='white')
    ax.axis('off')

    ax.text(0.0, 0.97, '8.  Conclusiones',
            transform=ax.transAxes, ha='left', va='top',
            fontsize=15, fontweight='bold', color=C['title'])
    hline(ax, 0.930, color=C['M1'], lw=1.5)

    concls = [
        ('C1', C['M1'],
         'M1 y Alvarado coinciden en complejidad relativa pero difieren en fisica.',
         'La correlacion r=0.83 entre sus entropias de Shannon indica que ambos '
         'modelos identifican correctamente que posiciones son mas ricas. Sin embargo, '
         'difieren en la magnitud (M1 siempre mayor), en que interacciones cuentan '
         '(vacio activo vs. invisible) y en el signo de las interacciones mismo-color.'),
        ('C2', C['AL'],
         'El desacuerdo de mayor impacto es el signo de la interaccion mismo-color.',
         'M1 asigna -1 (atraccion) a negro-negro y a blanco-blanco. '
         'Alvarado asigna +1 (repulsion). Esta diferencia cualitativa '
         'implica interpretaciones fisicamente opuestas sobre como interactuan '
         'las piedras del mismo color, lo cual tiene consecuencias directas '
         'en como se evalua la cohesion de un grupo.'),
        ('C3', '#15803D',
         'M1 captura la influencia territorial; Alvarado solo el contacto directo.',
         'Las intersecciones vacias adyacentes a una piedra tienen energia '
         'no nula en M1 (H(0,xj)=2xj). Esto modela el efecto de campo que '
         'ejerce un grupo sobre el espacio circundante, concepto central en '
         'la estrategia de Go. Alvarado no captura este efecto.'),
        ('C4', '#B45309',
         'El marco de Ising de dos colores no produce enfriamiento termodinámico.',
         'La coexistencia obligatoria de negro y blanco mantiene la media de '
         'energias cerca de cero durante toda la partida, haciendo divergir T_eff. '
         'El "enfriamiento" del Go (decreasing value of next move) existe, pero '
         'vive en la variable de ownership territorial, no en la distribucion '
         'de energias de bono.'),
        ('C5', C['acc'],
         'Los modelos convergen en el final de partida.',
         'La brecha delta_S disminuye de ~1.7 nats (apertura) a ~0.8 nats '
         '(yose) porque al llenarse el tablero predominan los bonos '
         'piedra-piedra, evaluados de forma similar por ambos modelos. '
         'La mayor diferencia entre los modelos ocurre en la apertura, '
         'cuando el tablero tiene mas espacio libre y la influencia territorial '
         'de M1 es mas significativa.'),
    ]

    y = 0.91
    for code, color, title, body in concls:
        h = 0.13
        colored_box(ax, 0.0, y - h, 1.0, h,
                    body, fc=C['bg_alt'], ec=color, fontsize=8.5,
                    title=f'{code} — {title}')
        y -= h + 0.015

    pdf.savefig(fig)
    plt.close()


# ════════════════════════════════════════════════════════════════════════════
# MAIN
# ════════════════════════════════════════════════════════════════════════════

def main():
    R = RESULTS
    # ── Orden correcto: nuestro modelo primero, luego Alvarado, luego comparacion ──
    pages = [
        # ── Portada e indice ──────────────────────────────────────────────
        ('cover',   {}),
        ('toc',     {}),
        ('intro',   {}),

        # ── Seccion 2: Nuestro Modelo M1 (el modelo principal) ───────────
        ('model_M1', {}),
        ('figure', dict(
            img_path=os.path.join(R, 'energy_grid_M1.png'),
            section_tag='Seccion 2.2 — Nuestro Modelo M1',
            fig_title='Figura 1 — Mapas de Energia M1 para los 19 Patrones de Apertura',
            caption='Cuadricula de 19 tableros con overlay de energia bajo nuestro modelo M1. '
                    'Azul = energia negativa (atraccion, celdas vacias cercanas a negro). '
                    'Rojo = energia positiva (repulsion, celdas vacias cercanas a blanco). '
                    'Ordenados por ID de patron (Tabla I del paper).')),
        ('figure', dict(
            img_path=os.path.join(R, 'dashboard_M1.png'),
            section_tag='Seccion 2.3 — Nuestro Modelo M1',
            fig_title='Figura 2 — Dashboard Modelo M1: Espacio Termodinamico y Ranking',
            caption='Mini tableros ordenados por S_Shannon (izquierda = mas ordenado, '
                    'derecha = mas caotico). Scatter T_eff vs S_Shannon muestra el espacio '
                    'termodinamico. Ranking completo con descripcion de cada patron. '
                    'Barras coloreadas segun entropia (azul=bajo, rojo=alto).')),

        # ── Seccion 3: Modelo Alvarado ────────────────────────────────────
        ('model_alvarado', {}),
        ('figure', dict(
            img_path=os.path.join(R, 'energy_grid_alvarado.png'),
            section_tag='Seccion 3.2 — Modelo Alvarado',
            fig_title='Figura 3 — Mapas de Energia Alvarado (Atomic-Go) para 19 Patrones',
            caption='Cuadricula de 19 tableros con overlay de energia bajo el modelo Alvarado. '
                    'El vacio (x=0) es invisible: solo las celdas con piedras tienen energia no nula. '
                    'Notar que los patrones con una sola piedra (1b, 2b, 7b...) dan S=0 '
                    'porque todos sus bonos valen 0 (la piedra no tiene vecinos del otro color).')),
        ('figure', dict(
            img_path=os.path.join(R, 'dashboard_alvarado.png'),
            section_tag='Seccion 3.3 — Modelo Alvarado',
            fig_title='Figura 4 — Dashboard Alvarado: Espacio Termodinamico y Ranking',
            caption='Mismo formato que el Dashboard M1 pero bajo la metrica de Alvarado. '
                    'Muchos patrones de apertura dan S_Shannon=0 porque sus piedras estan '
                    'aisladas (sin vecinos de otro color). Solo los patrones con contacto '
                    'directo entre colores distintos producen energia no nula.')),

        # ── Seccion 4: Comparacion tabla de interaccion ───────────────────
        ('matrices', {}),
        ('figure', dict(
            img_path=os.path.join(R, 'interaction_comparison.png'),
            section_tag='Seccion 4.1 — Comparacion',
            fig_title='Figura 5 — Cuatro Representaciones de la Tabla de Interaccion',
            caption='Heatmaps 3x3 (M1, Alvarado, diferencia M1-Alvarado), grafico de barras '
                    'comparativo para los 9 pares dirigidos, y grafos de nodos con flechas '
                    'coloreadas por energia. El heatmap de diferencia revela que M1 ve el '
                    'doble de energia en casi todos los pares que involucran el vacio.')),
        ('figure', dict(
            img_path=os.path.join(R, 'bond_interaction_graph.png'),
            section_tag='Seccion 4.2 — Comparacion',
            fig_title='Figura 6 — Grafo de Nodos y Flechas Dirigidas',
            caption='Tres nodos (Negro, Vacio, Blanco) conectados con flechas cuyo grosor '
                    'y color codifican la energia del bono dirigido. Los lazos son '
                    'auto-interacciones (mismo-color). La asimetria de M1 se hace visible '
                    'en las flechas de distinto grosor entre el mismo par de nodos.')),

        # ── Seccion 5: Comparacion entropia ──────────────────────────────
        ('figure', dict(
            img_path=os.path.join(R, 'entropy_comparison.png'),
            section_tag='Seccion 5.1 — Comparacion Entropia',
            fig_title='Figura 7 — Comparacion Completa: Shannon, Boltzmann y T_eff',
            caption='Fila 1: distribucion de valores en la tabla de interaccion con S_Shannon, '
                    'S_Boltzmann y T_eff para cada modelo. Fila 2: barras de S_Shannon para '
                    'los 19 patrones. Fila 3: S_Boltzmann y T_eff. '
                    'Fila 4: diagramas de dispersion — M1 vs Alvarado y Shannon vs Boltzmann.')),
        ('figure', dict(
            img_path=os.path.join(R, 'bond_entropy_compare.png'),
            section_tag='Seccion 5.1 — Comparacion Entropia',
            fig_title='Figura 8 — Entropia de Shannon: M1 vs Alvarado por los 19 Patrones',
            caption='Panel superior: barras S_Shannon M1 (azul) vs Alvarado (naranja) '
                    'para cada patron. Panel inferior: diferencia S_M1 - S_Alvarado. '
                    'M1 supera a Alvarado en 19/19 patrones con brecha media de 1.92 nats. '
                    'La brecha es maxima en patrones con piedras aisladas (vacio invisible).')),
        ('pattern_table', {}),
        ('figure', dict(
            img_path=os.path.join(R, 'bond_distribution.png'),
            section_tag='Seccion 5.3 — Distribucion de Bonos',
            fig_title='Figura 9 — Distribucion de Energias de Bono por Patron',
            caption='Histogramas de frecuencia de valores de bono para 6 patrones '
                    'representativos. Fila superior: M1 (5 valores posibles, distribucion rica). '
                    'Fila inferior: Alvarado (3 valores posibles, concentrado en 0). '
                    'La diferencia de riqueza distributiva explica la brecha de entropia.')),

        # ── Secciones finales ─────────────────────────────────────────────
        ('findings',    {}),
        ('limits',      {}),
        ('conclusions', {}),
    ]

    total = len(pages)
    print(f"\nGenerando PDF: {total} paginas...")

    page_funcs = {
        'cover':          lambda pdf, n, t: page_cover(pdf),
        'toc':            lambda pdf, n, t: page_toc(pdf, n, t),
        'intro':          lambda pdf, n, t: page_intro(pdf, n, t),
        'models':         lambda pdf, n, t: page_models(pdf, n, t),
        'model_M1':       lambda pdf, n, t: page_model_M1(pdf, n, t),
        'model_alvarado': lambda pdf, n, t: page_model_alvarado(pdf, n, t),
        'matrices':       lambda pdf, n, t: page_interaction_matrices(pdf, n, t),
        'pattern_table':  lambda pdf, n, t: page_pattern_table(pdf, n, t),
        'findings':       lambda pdf, n, t: page_findings(pdf, n, t),
        'limits':         lambda pdf, n, t: page_limits(pdf, n, t),
        'conclusions':    lambda pdf, n, t: page_conclusions(pdf, n, t),
    }

    with PdfPages(OUT) as pdf:
        # Metadatos
        d = pdf.infodict()
        d['Title']   = 'Analisis de Informacion Entropica en el Juego de Go'
        d['Author']  = 'Jimenez Martinez, L. & Mercado Sanchez, M. (Ometitlan). Paper: Jimenez Martinez & Sesma Gonzalez (2025)'
        d['Subject'] = 'Comparacion de modelos de Ising: M1 vs Atomic-Go (Alvarado 2019)'
        d['Keywords']= 'Go, Ising, Entropia, Shannon, Boltzmann, Patrones de apertura'

        for page_num, (ptype, kwargs) in enumerate(pages, start=1):
            print(f"  [{page_num:2d}/{total}] {ptype} ...", end=' ')
            if ptype == 'figure':
                page_figure(pdf, page_num=page_num, total=total, **kwargs)
            else:
                page_funcs[ptype](pdf, page_num, total)
            print('OK')

    size_mb = os.path.getsize(OUT) / 1024 / 1024
    print(f"\nReporte generado: {OUT}  ({size_mb:.1f} MB)")


if __name__ == '__main__':
    main()
