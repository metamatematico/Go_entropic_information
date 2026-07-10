"""
build_patterns_dataset.py
=========================
Genera el dataset de los 19 patrones base extraidos de la Tabla I del articulo:

    Sesma Gonzalez & Jimenez Martinez (2025)
    "Pattern Acquisition and Comparative Analysis in the Game of Go"

Columna 2025(b): patrones del juego moderno con IA.
Columna 2007(a): patrones historicos (inferidos de las notas del paper + teoria joseki).

Salidas:
    results/patterns_base.csv          -- tabla principal (una fila por patron)
    results/patterns_base_boards.png   -- visualizacion de los 19 tableros 2025(b)
    results/patterns_comparison.png    -- comparacion 2007(a) vs 2025(b)
"""

import os, sys
from pathlib import Path
import csv
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.gridspec as gridspec
from matplotlib.patches import Circle, FancyBboxPatch
import textwrap

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from analysis_patterns import PATTERNS, BOARD_SIZE

RESULTS = os.path.join(str(Path(__file__).resolve().parents[2]), 'results', '01_patrones')
os.makedirs(RESULTS, exist_ok=True)

# ── Notacion Go estandar (tablero 9x9) ───────────────────────────────────────
COL_LETTERS = list('ABCDEFGHJ')   # sin I

def to_go(row, col):
    return f'{COL_LETTERS[col]}{BOARD_SIZE - row}'

def stones_str(stones):
    b = [to_go(r, c) for color, r, c in stones if color == 'B']
    w = [to_go(r, c) for color, r, c in stones if color == 'W']
    parts = []
    if b: parts.append('B:' + ','.join(b))
    if w: parts.append('W:' + ','.join(w))
    return '  '.join(parts)

def board_flat(stones, size=9):
    board = np.zeros(size * size, dtype=int)
    for color, r, c in stones:
        board[r * size + c] = -1 if color == 'B' else +1
    return ','.join(str(v) for v in board)

# ── Notas textuales exactas del paper (Tabla I, columna Notes) ───────────────
PAPER_NOTES = {
    '1b':  "The 4-4 star point remains most frequent.",
    '2b':  "Komoku (3-4) also remains as second most frequent pattern.",
    '3b':  "A low approach to a 3-4 point is nowadays more urgent than both "
           "a low approach to 4-4 (pattern 3a) and a high approach to a 3-4 "
           "(pattern 4a).",
    '4b':  "A san-san invasion is more urgent than a high approach to an "
           "opponent's komoku.",
    '5b':  "This standard sequence after a san-san invasion leaves the invader "
           "in gote, suggesting the invaded stone may reply with tennuki before "
           "extending.",
    '6b':  "Once white extends, it is less likely that black will tennuki, "
           "considering the result of pattern 5b.",
    '7b':  "A low approach to the 4-4 is now less frequent than a san-san "
           "invasion, see pattern 5a.",
    '8b':  "This approach resembles the joseki pattern in 6a but is actually "
           "a low approach to the opponent's enclosure from the 4-4 point. "
           "The fact that this enclosure pattern does not appear without the "
           "approach, suggests this move follows most of the time.",
    '9b':  "A joseki continuation to pattern 5b, not as frequent.",
    '10b': "Two space jump from komoku appears as the most urgent form of "
           "enclosing a corner.",
    '11b': "A high approach to komoku descends from 4th to 11th most frequent "
           "pattern.",
    '12b': "Another continuation from pattern 5b precedes its subsequent "
           "joseki moves in patterns 14b, 15b and 17b.",
    '13b': "This move is now less frequent, see pattern 7a.",
    '14b': "This joseki pattern naturally appears after a san-san invasion, "
           "but an extension from white's stone in the third line is not always "
           "the immediate follow-up, suggesting white's tennuki.",
    '15b': "Though less frequent, this sequence from san-san invasion joseki "
           "also suggests white's tennuki, instead of following up with hane "
           "as in pattern 14b.",
    '16b': "This pattern has become less frequent, see 8a.",
    '17b': "Similarly to pattern 14b, this sequence suggests black's tennuki "
           "immediately after white's hane.",
    '18b': "This joseki pattern is less frequent in modern play, see 9a.",
    '19b': "Another continuation from pattern 9b.",
}

# ── Patrones 2007(a) — columna izquierda de la Tabla I ───────────────────────
#
# Cada entrada: desc (texto) + stones (posiciones) + rank_change (tendencia).
# Las posiciones se infieren de las notas del paper y teoria clasica de joseki.
# Las entradas sin stones se marcan como None (posicion incierta).
#
# Clave de rank_change:
#   'estable'   — misma posicion/joseki en el mismo rango ambas eras
#   'ascendio'  — ese tipo de joseki subio de rango entre 2007 y 2025
#   'descendio' — ese tipo de joseki bajo de rango
#   'nuevo'     — joseki diferente en este rango (2007 vs 2025 totalmente distintos)
#   'ampliado'  — misma joseki pero con mas jugadas mostradas en 2025 (era IA)
#
PATTERNS_2007A = {
    '1b': {
        'desc': 'Hoshi 4-4 — sin cambio, sigue siendo el mas frecuente',
        'stones': [('B', 3, 3)],         # = 1b
        'rank_change': 'estable',
    },
    '2b': {
        'desc': 'Komoku 3-4 — sin cambio, sigue siendo el 2do mas frecuente',
        'stones': [('B', 2, 3)],         # = 2b
        'rank_change': 'estable',
    },
    '3b': {
        'desc': 'Approach bajo a 4-4 hoshi (en 2025 sustituido por approach bajo a 3-4)',
        'stones': [('W', 3, 3), ('B', 3, 5)],  # W:D6 (hoshi) + B:F6 (approach 3ra linea)
        'rank_change': 'descendio',
    },
    '4b': {
        'desc': 'Approach alto a komoku — superado por invasion san-san (mismo que 11b en 2025)',
        'stones': [('W', 2, 3), ('B', 4, 4)],  # W:D7 (komoku) + B:E5 (4ta linea) = 11b
        'rank_change': 'descendio',
    },
    '5b': {
        'desc': 'Invasion san-san a hoshi (2007: solo inicio, 2025: joseki completo de 5 jugadas)',
        'stones': [('W', 3, 3), ('B', 2, 2)],  # W:D6 + B:C7 (solo la invasion, 2 piedras)
        'rank_change': 'ampliado',
    },
    '6b': {
        'desc': 'Approach a cercado 4-4 (en 2025 vease patron 8b)',
        'stones': [('B', 3, 3), ('B', 2, 5), ('W', 3, 6)],  # B:D6 + B:G7 + W:H6
        'rank_change': 'nuevo',
    },
    '7b': {
        'desc': 'Approach bajo a 4-4, keima oblicuo — permanece en rango 7, menos frecuente vs san-san',
        'stones': [('W', 3, 3), ('B', 4, 5)],  # W:D6 + B:F5 = identico a 7b
        'rank_change': 'estable',
    },
    '8b': {
        'desc': 'Patron en rango 8 (2007) — 8b actual "se asemeja al joseki 6a"',
        'stones': None,                  # posicion incierta
        'rank_change': 'nuevo',
    },
    '9b': {
        'desc': 'Joseki komoku+san-san (era rango 9 en 2007; descendio a rango 18 como 18b)',
        'stones': [('W', 2, 3), ('B', 2, 2), ('B', 1, 3), ('W', 1, 2)],  # = 18b
        'rank_change': 'nuevo',
    },
    '10b': {
        'desc': 'Salto simple desde komoku (en era IA el salto doble 10b es preferido)',
        'stones': [('B', 2, 3), ('B', 2, 4)],  # B:D7 + B:E7 (ikken-tobi)
        'rank_change': 'ascendio',
    },
    '11b': {
        'desc': 'Patron desconocido en rango 11 del 2007 (approach alto era rango 4 como 4a)',
        'stones': None,
        'rank_change': 'nuevo',
    },
    '12b': {
        'desc': 'Variante joseki en rango 12 del 2007 (incierto)',
        'stones': None,
        'rank_change': 'nuevo',
    },
    '13b': {
        'desc': 'Approach bajo 5ta linea a 4-4 (ver patron 7a) — ahora menos frecuente',
        'stones': [('W', 3, 3), ('B', 4, 5)],  # similar a 7a/7b
        'rank_change': 'descendio',
    },
    '14b': {
        'desc': 'Joseki san-san + extension (rango 14 en 2007, version menos desarrollada)',
        'stones': None,
        'rank_change': 'nuevo',
    },
    '15b': {
        'desc': 'Joseki san-san hane — rango 15 en 2007, menos frecuente que 14b',
        'stones': None,
        'rank_change': 'descendio',
    },
    '16b': {
        'desc': 'Approach a cercado alternativo (rango 16, ver patron 8a del 2007)',
        'stones': None,
        'rank_change': 'descendio',
    },
    '17b': {
        'desc': 'Hane+respuesta en joseki san-san — rango 17 en 2007',
        'stones': None,
        'rank_change': 'nuevo',
    },
    '18b': {
        'desc': 'Joseki komoku+san-san en rango 18 (era rango 9 como 9a, ahora menos frecuente)',
        'stones': [('W', 2, 3), ('B', 2, 2), ('B', 1, 3), ('W', 1, 2)],  # misma pos que 9b-row
        'rank_change': 'descendio',
    },
    '19b': {
        'desc': 'Continuacion joseki komoku+san-san — rango 19 en 2007',
        'stones': None,
        'rank_change': 'nuevo',
    },
}

# ── Relaciones entre patrones (arbol de derivacion) ──────────────────────────
DERIVED_FROM = {
    '1b':  None,
    '2b':  None,
    '3b':  None,
    '4b':  None,
    '5b':  '4b',     # joseki estandar tras san-san invasion
    '6b':  '5b',     # extension blanca
    '7b':  None,
    '8b':  None,
    '9b':  '5b',     # variante de joseki (menos frecuente)
    '10b': '2b',     # cercado desde komoku
    '11b': '2b',     # approach a komoku
    '12b': '5b',     # otra continuacion de 5b
    '13b': None,
    '14b': '12b',    # joseki con extension
    '15b': '12b',    # joseki con hane blanco
    '16b': '8b',     # approach alternativo a cercado
    '17b': '12b',    # hane + respuesta negra
    '18b': '9b',     # variante menos frecuente
    '19b': '9b',     # otra continuacion de 9b
}

# ── Clasificacion por tipo de patron ─────────────────────────────────────────
CATEGORIES = {
    '1b':  ('apertura',  'hoshi',                '4-4'),
    '2b':  ('apertura',  'komoku',               '3-4'),
    '3b':  ('approach',  'bajo a komoku',         'keima'),
    '4b':  ('invasion',  'san-san a hoshi',       '3-3'),
    '5b':  ('joseki',    'san-san gote',          '5 jugadas'),
    '6b':  ('joseki',    'extension',             '6 jugadas'),
    '7b':  ('approach',  'bajo a hoshi',          'kosumi'),
    '8b':  ('approach',  'a cercado 4-4',         '3 piedras'),
    '9b':  ('joseki',    'san-san var A',         '5 jugadas'),
    '10b': ('enclosure', 'moyo komoku',           'salto doble'),
    '11b': ('approach',  'alto a komoku',         '4ta linea'),
    '12b': ('joseki',    'san-san + kosumi',      '6 jugadas'),
    '13b': ('approach',  'bajo 5ta linea',        'a hoshi'),
    '14b': ('joseki',    'extension larga',       '7 jugadas'),
    '15b': ('joseki',    'hane blanco',           '5 jugadas'),
    '16b': ('approach',  'a cercado alt',         '3 piedras'),
    '17b': ('joseki',    'hane + respuesta',      '6 jugadas'),
    '18b': ('joseki',    'raro moderno',          '4 jugadas'),
    '19b': ('joseki',    'san-san var B',         '6 jugadas'),
}

CAT_COLORS = {
    'apertura':  '#2E6B4A',
    'approach':  '#1748A3',
    'invasion':  '#C0392B',
    'joseki':    '#7C3AED',
    'enclosure': '#D97706',
}

# ─────────────────────────────────────────────────────────────────────────────
# 1. CSV
# ─────────────────────────────────────────────────────────────────────────────

def build_csv():
    rows = []
    for pid, desc, stones in PATTERNS:
        cat, subcat, detail = CATEGORIES.get(pid, ('?', '?', '?'))
        n  = len(stones)
        n_b = sum(1 for c, r, col in stones if c == 'B')
        n_w = n - n_b
        first_color, first_r, first_c = stones[0]
        first_go = to_go(first_r, first_c)

        sequence = '  '.join(
            f'{i+1}.{"B" if c=="B" else "W"}:{to_go(r,col)}'
            for i, (c, r, col) in enumerate(stones)
        )

        p07 = PATTERNS_2007A.get(pid, {})
        st07 = p07.get('stones') or []
        rows.append({
            'id':              pid,
            'description':     desc,
            'category':        cat,
            'subcategory':     subcat,
            'detail':          detail,
            'n_stones':        n,
            'n_black':         n_b,
            'n_white':         n_w,
            'first_point':     first_go,
            'stones_go':       stones_str(stones),
            'sequence':        sequence,
            'derived_from':    DERIVED_FROM.get(pid) or '',
            'paper_notes':     PAPER_NOTES.get(pid, ''),
            'board_flat':      board_flat(stones),
            # columnas 2007(a)
            'rank_change':     p07.get('rank_change', '?'),
            'desc_2007a':      p07.get('desc', ''),
            'stones_2007a':    stones_str(st07) if st07 else '?',
            'board_flat_2007a': board_flat(st07) if st07 else '?',
        })

    path = os.path.join(RESULTS, 'patterns_base.csv')
    fields = ['id','description','category','subcategory','detail',
              'n_stones','n_black','n_white','first_point',
              'stones_go','sequence','derived_from','paper_notes','board_flat',
              'rank_change','desc_2007a','stones_2007a','board_flat_2007a']
    with open(path, 'w', newline='', encoding='utf-8') as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        w.writerows(rows)
    print(f'CSV guardado: {path}')
    return rows

# ─────────────────────────────────────────────────────────────────────────────
# 2. Visualizacion: grilla de 19 tableros con notas del paper
# ─────────────────────────────────────────────────────────────────────────────

BG   = '#F5F0E8'
WOOD = '#DEB887'
LINE_C  = '#5C3D00'

def draw_board(ax, stones, size=9):
    ax.set_facecolor(WOOD)
    ax.set_xlim(-0.5, size - 0.5)
    ax.set_ylim(-0.5, size - 0.5)
    ax.set_aspect('equal')
    ax.tick_params(left=False, bottom=False,
                   labelleft=False, labelbottom=False)
    for sp in ax.spines.values():
        sp.set_color('#8B6914'); sp.set_linewidth(1)

    for k in range(size):
        ax.plot([0, size-1], [k, k], '-', color=LINE_C, lw=0.5, zorder=1)
        ax.plot([k, k], [0, size-1], '-', color=LINE_C, lw=0.5, zorder=1)

    for hx, hy in [(2,2),(2,6),(6,2),(6,6),(4,4)]:
        ax.plot(hx, hy, 'o', color=LINE_C, ms=2.2, zorder=2)

    r_stone = 0.42
    for color, row, col in stones:
        dy = (size - 1) - row
        dx = col
        if color == 'B':
            fc, ec = '#111111', '#333333'
        else:
            fc, ec = '#F5F0E8', '#777777'
        ax.add_patch(Circle((dx + 0.04, dy - 0.04), r_stone,
                             fc='#00000028', ec='none', zorder=4))
        ax.add_patch(Circle((dx, dy), r_stone,
                             fc=fc, ec=ec, lw=0.8, zorder=5))

    # Coordenadas Go en bordes
    for k in range(size):
        ax.text(-0.52, k, str(size - k), ha='right', va='center',
                fontsize=4, color='#7B5E00')
        ax.text(k, -0.52, COL_LETTERS[k], ha='center', va='top',
                fontsize=4, color='#7B5E00')


def build_viz(rows):
    NCOLS = 5
    NROWS = 4

    # Figura alta para incluir notas del paper
    fig = plt.figure(figsize=(22, 20), facecolor=BG)
    fig.suptitle(
        'Patrones Base de Apertura — Tabla I\n'
        'Sesma Gonzalez & Jimenez Martinez (2025)  ·  Columna 2025(b)',
        fontsize=14, fontweight='bold', y=0.985, color='#1a1a1a'
    )

    # Leyenda de categorias
    lx = 0.01
    for cat, col in CAT_COLORS.items():
        fig.text(lx, 0.962, f'■ {cat}', fontsize=8, color=col,
                 fontweight='bold', transform=fig.transFigure)
        lx += 0.10

    # Para cada celda: tablero (arriba) + nota del paper (abajo)
    # Usamos gridspec con celdas divididas internamente
    outer = gridspec.GridSpec(NROWS, NCOLS,
                              hspace=0.62, wspace=0.18,
                              left=0.04, right=0.97,
                              top=0.945, bottom=0.02)

    for idx, row in enumerate(rows):
        ri = idx // NCOLS
        ci = idx % NCOLS

        inner = gridspec.GridSpecFromSubplotSpec(
            2, 1, subplot_spec=outer[ri, ci],
            height_ratios=[1.6, 1.0], hspace=0.08
        )

        # ── Tablero ────────────────────────────────────────────────────────
        ax_board = fig.add_subplot(inner[0])
        pid, desc, stones = PATTERNS[idx]
        draw_board(ax_board, stones)

        cat = row['category']
        col = CAT_COLORS.get(cat, '#888')

        ax_board.set_title(
            f"{pid}  —  {desc}",
            fontsize=6.8, fontweight='bold', color='#1a1a1a',
            pad=3, loc='center'
        )

        # Etiquetas bajo el tablero: categoria + notacion Go
        ax_board.text(0.5, -0.08, f'{cat} · {row["subcategory"]}',
                      ha='center', va='top', transform=ax_board.transAxes,
                      fontsize=6, color=col, fontweight='bold')
        ax_board.text(0.5, -0.16, row['stones_go'],
                      ha='center', va='top', transform=ax_board.transAxes,
                      fontsize=5.8, color='#444', family='monospace')

        # Indicador "deriva de"
        parent = DERIVED_FROM.get(pid)
        if parent:
            ax_board.text(0.5, -0.24, f'← {parent}',
                          ha='center', va='top', transform=ax_board.transAxes,
                          fontsize=5.5, color='#999', style='italic')

        # ── Nota del paper ─────────────────────────────────────────────────
        ax_note = fig.add_subplot(inner[1])
        ax_note.set_facecolor('#F0EBF8' if cat == 'joseki' else
                               '#EBF4FF' if cat == 'approach' else
                               '#EBF8EE' if cat == 'apertura' else
                               '#FEF3C7' if cat == 'enclosure' else
                               '#FEE2E2')
        for sp in ax_note.spines.values():
            sp.set_visible(False)
        ax_note.set_xticks([]); ax_note.set_yticks([])

        note = PAPER_NOTES.get(pid, '')
        wrapped = textwrap.fill(note, width=52)
        ax_note.text(0.5, 0.55, wrapped,
                     ha='center', va='center',
                     transform=ax_note.transAxes,
                     fontsize=5.5, color='#333',
                     style='italic', linespacing=1.45,
                     wrap=True)

    # Celda 20 → resumen
    inner_sum = gridspec.GridSpecFromSubplotSpec(
        1, 1, subplot_spec=outer[3, 4])
    ax_sum = fig.add_subplot(inner_sum[0])
    ax_sum.set_facecolor('#EEF3F8')
    for sp in ax_sum.spines.values(): sp.set_visible(False)
    ax_sum.set_xticks([]); ax_sum.set_yticks([])

    ax_sum.text(0.5, 0.93, '19 patrones', ha='center', va='top',
                transform=ax_sum.transAxes, fontsize=12,
                fontweight='bold', color='#1a1a1a')
    ax_sum.text(0.5, 0.80, 'Tabla I · 2025(b)',
                ha='center', va='top', transform=ax_sum.transAxes,
                fontsize=8, color='#555', style='italic')

    cat_counts = {}
    for r in rows:
        cat_counts[r['category']] = cat_counts.get(r['category'], 0) + 1

    y = 0.65
    for cat in ['apertura','approach','invasion','joseki','enclosure']:
        n = cat_counts.get(cat, 0)
        col = CAT_COLORS[cat]
        ax_sum.text(0.5, y, f'{n}  {cat}',
                    ha='center', va='top', transform=ax_sum.transAxes,
                    fontsize=8, color=col, fontweight='bold')
        y -= 0.13

    # Arbol de derivacion resumido
    ax_sum.text(0.5, 0.16,
                'Arbol: 4b->5b->{6b,9b,12b}\n'
                '12b->{14b,15b,17b}\n'
                '9b->{18b,19b}',
                ha='center', va='bottom', transform=ax_sum.transAxes,
                fontsize=6.5, color='#666', style='italic',
                linespacing=1.5)

    out = os.path.join(RESULTS, 'patterns_base_boards.png')
    plt.savefig(out, dpi=150, bbox_inches='tight', facecolor=BG)
    print(f'Imagen guardada: {out}')
    plt.close(fig)


# ─────────────────────────────────────────────────────────────────────────────
# 3. Visualizacion comparativa 2007(a) vs 2025(b)
# ─────────────────────────────────────────────────────────────────────────────

CHANGE_COLOR = {
    'estable':   '#15803D',
    'ascendio':  '#1D4ED8',
    'descendio': '#DC2626',
    'ampliado':  '#7C3AED',
    'nuevo':     '#D97706',
    '?':         '#888888',
}
CHANGE_LABEL = {
    'estable':   'ESTABLE',
    'ascendio':  'ASCENDIO',
    'descendio': 'DESCENDIO',
    'ampliado':  'AMPLIADO',
    'nuevo':     'NUEVO JOSEKI',
    '?':         '?',
}


def build_comparison_viz():
    """Grilla 19x1: cada celda muestra 2007(a) | flecha | 2025(b)."""
    NCOLS = 5
    NROWS = 4

    fig = plt.figure(figsize=(26, 22), facecolor=BG)
    fig.suptitle(
        'Comparacion Historica de Patrones  ·  2007(a)  vs  2025(b)\n'
        'Sesma Gonzalez & Jimenez Martinez (2025) — Tabla I',
        fontsize=13, fontweight='bold', y=0.988, color='#1a1a1a'
    )

    # Leyenda de tendencias
    lx = 0.01
    for key, col in CHANGE_COLOR.items():
        if key == '?': continue
        fig.text(lx, 0.966, f'  {CHANGE_LABEL[key]}',
                 fontsize=7.5, color=col, fontweight='bold',
                 transform=fig.transFigure)
        lx += 0.135

    outer = gridspec.GridSpec(NROWS, NCOLS,
                              hspace=0.55, wspace=0.18,
                              left=0.03, right=0.98,
                              top=0.955, bottom=0.02)

    for idx, (pid, desc, stones_2025) in enumerate(PATTERNS):
        ri = idx // NCOLS
        ci = idx % NCOLS

        p07 = PATTERNS_2007A.get(pid, {})
        stones_07 = p07.get('stones') or []
        change = p07.get('rank_change', '?')
        col_change = CHANGE_COLOR[change]
        label_change = CHANGE_LABEL[change]

        # Cada celda tiene 3 columnas: tablero-2007 | central | tablero-2025
        inner = gridspec.GridSpecFromSubplotSpec(
            2, 3, subplot_spec=outer[ri, ci],
            height_ratios=[1.4, 0.5], hspace=0.05,
            width_ratios=[1, 0.22, 1], wspace=0.04
        )

        # ── Tablero 2007(a) ───────────────────────────────────────────────
        ax_07 = fig.add_subplot(inner[0, 0])
        if stones_07:
            draw_board(ax_07, stones_07)
        else:
            ax_07.set_facecolor('#E8E8E8')
            for sp in ax_07.spines.values(): sp.set_visible(False)
            ax_07.set_xticks([]); ax_07.set_yticks([])
            ax_07.text(0.5, 0.5, '?', ha='center', va='center',
                       fontsize=22, color='#AAAAAA',
                       transform=ax_07.transAxes, fontweight='bold')
        ax_07.set_title('2007(a)', fontsize=6, color='#555', pad=2)

        # ── Panel central (flecha + etiqueta de cambio) ───────────────────
        ax_mid = fig.add_subplot(inner[0, 1])
        ax_mid.set_facecolor(BG)
        for sp in ax_mid.spines.values(): sp.set_visible(False)
        ax_mid.set_xticks([]); ax_mid.set_yticks([])
        ax_mid.set_xlim(0, 1); ax_mid.set_ylim(0, 1)
        ax_mid.annotate('', xy=(0.85, 0.5), xytext=(0.15, 0.5),
                        xycoords='axes fraction', textcoords='axes fraction',
                        arrowprops=dict(arrowstyle='->', color=col_change,
                                        lw=1.8, mutation_scale=14))
        ax_mid.text(0.5, 0.26, label_change,
                    ha='center', va='center', fontsize=4.8,
                    color=col_change, fontweight='bold',
                    transform=ax_mid.transAxes, rotation=90)

        # ── Tablero 2025(b) ───────────────────────────────────────────────
        ax_25 = fig.add_subplot(inner[0, 2])
        draw_board(ax_25, stones_2025)
        ax_25.set_title('2025(b)', fontsize=6, color='#555', pad=2)

        # ── Panel inferior: id + descripcion ─────────────────────────────
        ax_desc = fig.add_subplot(inner[1, :])
        cat = CATEGORIES.get(pid, ('?',))[0]
        ax_desc.set_facecolor(CAT_COLORS.get(cat, '#888') + '18')  # 10% opacity
        for sp in ax_desc.spines.values(): sp.set_visible(False)
        ax_desc.set_xticks([]); ax_desc.set_yticks([])

        short_desc_07 = (p07.get('desc', '') or '')[:60]
        ax_desc.text(0.5, 0.78, f'{pid}  —  {desc}',
                     ha='center', va='top', fontsize=6.5, fontweight='bold',
                     color='#111', transform=ax_desc.transAxes)
        ax_desc.text(0.5, 0.38, short_desc_07,
                     ha='center', va='top', fontsize=5.3, color='#555',
                     style='italic', transform=ax_desc.transAxes,
                     wrap=True)
        # n_stones comparison
        n07 = len(stones_07) if stones_07 else '?'
        n25 = len(stones_2025)
        ax_desc.text(0.5, 0.0, f'piedras: {n07} → {n25}',
                     ha='center', va='bottom', fontsize=5, color='#888',
                     transform=ax_desc.transAxes)

    # Celda 20 → leyenda ampliada
    inner_leg = gridspec.GridSpecFromSubplotSpec(
        1, 1, subplot_spec=outer[3, 4])
    ax_leg = fig.add_subplot(inner_leg[0])
    ax_leg.set_facecolor('#EEF3F8')
    for sp in ax_leg.spines.values(): sp.set_visible(False)
    ax_leg.set_xticks([]); ax_leg.set_yticks([])

    ax_leg.text(0.5, 0.96, 'Leyenda', ha='center', va='top',
                fontsize=10, fontweight='bold', color='#1a1a1a',
                transform=ax_leg.transAxes)

    yl = 0.82
    for key in ['estable', 'ascendio', 'descendio', 'ampliado', 'nuevo']:
        col = CHANGE_COLOR[key]
        lbl = CHANGE_LABEL[key]
        expl = {
            'estable':   'Mismo joseki, mismo rango',
            'ascendio':  'Joseki mas frecuente en 2025',
            'descendio': 'Joseki menos frecuente en 2025',
            'ampliado':  'Mismo joseki, mas jugadas en 2025',
            'nuevo':     'Joseki diferente en este rango',
        }[key]
        ax_leg.text(0.12, yl, f'■ {lbl}', ha='left', va='top', fontsize=7.5,
                    fontweight='bold', color=col, transform=ax_leg.transAxes)
        ax_leg.text(0.12, yl - 0.06, expl, ha='left', va='top', fontsize=6,
                    color='#555', transform=ax_leg.transAxes)
        yl -= 0.17

    ax_leg.text(0.5, 0.02, '? = posicion incierta', ha='center', va='bottom',
                fontsize=6, color='#999', style='italic',
                transform=ax_leg.transAxes)

    out = os.path.join(RESULTS, 'patterns_comparison.png')
    plt.savefig(out, dpi=150, bbox_inches='tight', facecolor=BG)
    print(f'Imagen guardada: {out}')
    plt.close(fig)


# ─────────────────────────────────────────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────────────────────────────────────────

def main():
    print('\n' + '='*60)
    print('  DATASET PATRONES BASE — Sesma & Jimenez (2025)')
    print('='*60)

    rows = build_csv()

    print('\nResumen:')
    for r in rows:
        parent = r['derived_from'] or '—'
        print(f"  {r['id']:<5}  n={r['n_stones']}  "
              f"B:{r['n_black']} W:{r['n_white']}  "
              f"[{r['category']:<10}]  from:{parent:<5}  "
              f"{r['stones_go']}")

    build_viz(rows)
    build_comparison_viz()
    print('\nListo.')


if __name__ == '__main__':
    main()
