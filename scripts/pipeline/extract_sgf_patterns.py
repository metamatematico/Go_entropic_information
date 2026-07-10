"""
extract_sgf_patterns.py
=======================
Extrae los primeros N movimientos de cada partida SGF en data/sgf_partidas/
y encuentra patrones y recurrencias reales en las aperturas.

A diferencia de analysis_patterns.py (que usa snapshots estaticos definidos
manualmente), aqui los turnos son los reales del archivo SGF: la piedra k
fue colocada en el turno k de la partida real.

Salidas:
  results/sgf_openings.csv      -- una fila por partida, primeros N movimientos
  results/sgf_patterns.csv      -- top-20 secuencias mas frecuentes por longitud
  results/sgf_heatmap.png       -- mapas de calor de frecuencia de posiciones
  results/sgf_top_openings.png  -- tableros de las aperturas mas recurrentes
"""

import os, re, csv
from collections import Counter
from pathlib import Path
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.gridspec as gridspec

BASE = str(Path(__file__).resolve().parents[2])
DATA = os.path.join(BASE, 'data', 'sgf_partidas')
RES  = os.path.join(BASE, 'results', '05_partidas_reales')
os.makedirs(RES, exist_ok=True)

SIZE    = 19
N       = 30          # movimientos a extraer por partida
COLS_19 = 'ABCDEFGHJKLMNOPQRST'
BG      = '#F5F0E8'
WOOD    = '#DEB887'

# ─────────────────────────────────────────────────────────────────────────────
# Parsing
# ─────────────────────────────────────────────────────────────────────────────

def parse(path):
    """
    Lee un .sgf y devuelve lista de (color, row, col), 0-indexed, row desde arriba.
    Devuelve None si no es 19x19 o tiene menos de 4 movimientos.
    Solo toma el primero match de ;B[xy] / ;W[xy] en orden de documento
    (linea principal, sin variaciones).
    """
    text = Path(path).read_text(encoding='utf-8', errors='ignore')
    sz = re.search(r'SZ\[(\d+)\]', text)
    if not sz or int(sz.group(1)) != SIZE:
        return None

    moves = []
    # Extraemos solo ;B[xy] y ;W[xy] ignorando setup stones (AB[]/AW[])
    for m in re.finditer(r'(?<![A-Z]);([BW])\[([a-s]{2})\]', text):
        col = ord(m.group(2)[0]) - ord('a')
        row = ord(m.group(2)[1]) - ord('a')
        if 0 <= col < SIZE and 0 <= row < SIZE:
            moves.append((m.group(1), row, col))
        if len(moves) == N:
            break
    return moves if len(moves) >= 4 else None


def go19(col, row):
    """0-indexed (col, row_desde_arriba) → notacion Go: 'Q16'."""
    return f'{COLS_19[col]}{SIZE - row}'


def mstr(c, r, col):
    return f'{c}:{go19(col, r)}'


def sstr(seq):
    return '|'.join(mstr(*m) for m in seq)


def sshort(seq):
    """Representacion corta para etiquetas: 'Q16·D4·Q4·D17'."""
    return '·'.join(go19(col, r) for _, r, col in seq)


# ─────────────────────────────────────────────────────────────────────────────
# Carga
# ─────────────────────────────────────────────────────────────────────────────

def load_games(sgf_dir):
    games = {}
    paths = sorted(Path(sgf_dir).glob('*.sgf'))
    skipped = 0
    for p in paths:
        moves = parse(p)
        if moves is None:
            skipped += 1
            continue
        games[p.stem] = moves
    print(f'  Parseados: {len(games)} juegos  |  Saltados: {skipped}')
    return games


# ─────────────────────────────────────────────────────────────────────────────
# Analisis
# ─────────────────────────────────────────────────────────────────────────────

def analyze(games):
    """
    Retorna:
      pos_freq[k]      : np.array(19x19) — frecuencia de la posicion en el turno k
      color_freq[c]    : np.array(19x19) — freq agregada por color
      prefix_counts[k] : Counter         — secuencias exactas de longitud k
    """
    pos_freq    = {k: np.zeros((SIZE, SIZE), dtype=int) for k in range(N)}
    color_freq  = {'B': np.zeros((SIZE, SIZE), dtype=int),
                   'W': np.zeros((SIZE, SIZE), dtype=int)}
    prefix_counts = {k: Counter() for k in range(1, N + 1)}

    for moves in games.values():
        for k, (c, r, col) in enumerate(moves):
            pos_freq[k][r, col] += 1
            color_freq[c][r, col] += 1

        for length in range(1, len(moves) + 1):
            prefix_counts[length][sstr(moves[:length])] += 1

    return {
        'pos_freq':      pos_freq,
        'color_freq':    color_freq,
        'prefix_counts': prefix_counts,
    }


# ─────────────────────────────────────────────────────────────────────────────
# CSV de aperturas
# ─────────────────────────────────────────────────────────────────────────────

def build_openings_csv(games):
    rows = []
    for gid, moves in games.items():
        row = {'game_id': gid, 'n_moves': len(moves)}
        for k, (c, r, col) in enumerate(moves, 1):
            row[f'move_{k}'] = mstr(c, r, col)
        row['sequence'] = sstr(moves)
        rows.append(row)

    fields = (['game_id', 'n_moves'] +
              [f'move_{k}' for k in range(1, N + 1)] + ['sequence'])
    path = os.path.join(RES, 'sgf_openings.csv')
    with open(path, 'w', newline='', encoding='utf-8') as f:
        w = csv.DictWriter(f, fieldnames=fields, extrasaction='ignore')
        w.writeheader()
        w.writerows(rows)
    print(f'  sgf_openings.csv  ({len(rows)} filas)')
    return path


# ─────────────────────────────────────────────────────────────────────────────
# CSV de patrones frecuentes
# ─────────────────────────────────────────────────────────────────────────────

def build_patterns_csv(prefix_counts, total):
    rows = []
    for length, counter in prefix_counts.items():
        for rank, (seq, count) in enumerate(counter.most_common(20), 1):
            rows.append({
                'length':    length,
                'rank':      rank,
                'count':     count,
                'pct':       round(100 * count / total, 2),
                'sequence':  seq,
                'short':     sshort([m.split(':') for m in seq.split('|')]
                                    if False else  # usar version parsed
                                    [(c, int(SIZE - int(pos[1:])),
                                      COLS_19.index(pos[0]))
                                     for part in seq.split('|')
                                     for c, pos in [part.split(':')]]),
            })
    path = os.path.join(RES, 'sgf_patterns.csv')
    with open(path, 'w', newline='', encoding='utf-8') as f:
        w = csv.DictWriter(f, fieldnames=['length','rank','count','pct','sequence','short'])
        w.writeheader()
        w.writerows(rows)
    print(f'  sgf_patterns.csv  ({len(rows)} filas)')
    return path


# ─────────────────────────────────────────────────────────────────────────────
# Dibujo de tablero 19x19
# ─────────────────────────────────────────────────────────────────────────────

def draw_board(ax, freq_map=None, stones=None, title='',
               vmax=None, stone_size=0.42, num_size=4.5):
    """
    freq_map: np.array(19x19) — heatmap de frecuencia  OR
    stones  : list[(color, row, col)] — secuencia con numeros
    """
    ax.set_facecolor(WOOD)
    ax.set_xlim(-0.5, 18.5)
    ax.set_ylim(-0.5, 18.5)
    ax.set_aspect('equal')
    ax.tick_params(left=False, bottom=False, labelleft=False, labelbottom=False)
    for sp in ax.spines.values():
        sp.set_color('#8B6914'); sp.set_linewidth(0.7)

    for k in range(SIZE):
        ax.plot([0, 18], [k, k], '-', color='#5C3D00', lw=0.25, zorder=1)
        ax.plot([k, k], [0, 18], '-', color='#5C3D00', lw=0.25, zorder=1)
    for hx in [3, 9, 15]:
        for hy in [3, 9, 15]:
            ax.plot(hx, hy, 'o', color='#5C3D00', ms=1.8, zorder=2)

    if freq_map is not None:
        if vmax is None:
            vmax = max(freq_map.max(), 1)
        for r in range(SIZE):
            for c in range(SIZE):
                v = freq_map[r, c]
                if v == 0:
                    continue
                dy = (SIZE - 1) - r
                rgba = plt.cm.YlOrRd(v / vmax)
                alpha = min(0.92, 0.12 + 0.80 * v / vmax)
                ax.add_patch(plt.Circle((c, dy), stone_size,
                                        fc=rgba[:3] + (alpha,), ec='none', zorder=3))

    if stones is not None:
        for k, (color, r, col) in enumerate(stones, 1):
            dy = (SIZE - 1) - r
            fc = '#111111' if color == 'B' else '#F5F0E8'
            ec = '#333' if color == 'B' else '#888'
            tc = '#FFF' if color == 'B' else '#000'
            ax.add_patch(plt.Circle((col, dy), stone_size,
                                    fc=fc, ec=ec, lw=0.8, zorder=5))
            ax.text(col, dy, str(k), ha='center', va='center',
                    fontsize=num_size, color=tc, fontweight='bold', zorder=6)

    ax.set_title(title, fontsize=7.5, pad=3, color='#1a1a1a')


# ─────────────────────────────────────────────────────────────────────────────
# Figura 1: mapas de calor
# ─────────────────────────────────────────────────────────────────────────────

def build_heatmap_viz(A, total):
    fig = plt.figure(figsize=(26, 18), facecolor=BG)
    fig.suptitle(
        f'Patrones de Apertura — Primeros {N} Movimientos\n'
        f'{total} partidas profesionales 19×19  ·  data/sgf_partidas/',
        fontsize=13, fontweight='bold', y=0.990, color='#1a1a1a',
    )
    outer = gridspec.GridSpec(2, 1, hspace=0.38,
                              top=0.958, bottom=0.04, left=0.04, right=0.97)

    # ── Fila 0: B, W, combinado ────────────────────────────────────────────
    row0 = gridspec.GridSpecFromSubplotSpec(1, 3, subplot_spec=outer[0],
                                             wspace=0.08)
    vmax_b = A['color_freq']['B'].max()
    vmax_w = A['color_freq']['W'].max()
    vmax_c = (A['color_freq']['B'] + A['color_freq']['W']).max()

    ax = fig.add_subplot(row0[0])
    draw_board(ax, A['color_freq']['B'],
               title=f'NEGRAS  (movimientos 1,3,5,7,9)\nmax = {vmax_b} juegos en una casilla',
               vmax=vmax_b)

    ax = fig.add_subplot(row0[1])
    draw_board(ax, A['color_freq']['W'],
               title=f'BLANCAS  (movimientos 2,4,6,8,10)\nmax = {vmax_w} juegos en una casilla',
               vmax=vmax_w)

    ax = fig.add_subplot(row0[2])
    draw_board(ax, A['color_freq']['B'] + A['color_freq']['W'],
               title=f'COMBINADO B+W\nmax = {vmax_c} jugadas en una casilla',
               vmax=vmax_c)

    # ── Fila 1: movimientos 1..N individuales (6 filas × 5 cols) ─────────
    row1 = gridspec.GridSpecFromSubplotSpec(6, 5, subplot_spec=outer[1],
                                             hspace=0.22, wspace=0.06)
    vmax_pm = max(A['pos_freq'][k].max() for k in range(N))

    for k in range(N):
        ri, ci = k // 5, k % 5
        ax = fig.add_subplot(row1[ri, ci])
        color_label = 'B' if k % 2 == 0 else 'W'
        n_unique = int((A['pos_freq'][k] > 0).sum())
        top1_pos = np.unravel_index(A['pos_freq'][k].argmax(), (SIZE, SIZE))
        top1_go  = go19(top1_pos[1], top1_pos[0])
        top1_cnt = A['pos_freq'][k].max()
        draw_board(
            ax, A['pos_freq'][k],
            title=(f'Mov {k+1}  ({color_label})  ·  {n_unique} únicas\n'
                   f'{top1_go}  ({100*top1_cnt/total:.0f}%)'),
            vmax=vmax_pm, stone_size=0.38,
        )

    out = os.path.join(RES, 'sgf_heatmap.png')
    plt.savefig(out, dpi=130, bbox_inches='tight', facecolor=BG)
    print(f'  sgf_heatmap.png')
    plt.close(fig)


# ─────────────────────────────────────────────────────────────────────────────
# Figura 2: tableros de las aperturas mas recurrentes
# ─────────────────────────────────────────────────────────────────────────────

def _parse_seq(seq_str):
    """'B:Q16|W:D4|...' → lista de (color, row, col)."""
    moves = []
    for part in seq_str.split('|'):
        c, pos = part.split(':')
        col_letter = pos[0]
        row_num    = int(pos[1:])
        col_idx    = COLS_19.index(col_letter)
        row_idx    = SIZE - row_num           # 0-indexed desde arriba
        moves.append((c, row_idx, col_idx))
    return moves


def build_top_openings_viz(A, total):
    """
    Muestra los tableros de las aperturas mas recurrentes para longitudes
    de prefijo k = 4, 6, 8 movimientos.
    """
    fig = plt.figure(figsize=(28, 20), facecolor=BG)
    fig.suptitle(
        'Aperturas Mas Recurrentes — Secuencias Exactas\n'
        f'{total} partidas  ·  prefijos de 4, 6 y 8 movimientos',
        fontsize=13, fontweight='bold', y=0.992, color='#1a1a1a',
    )

    outer = gridspec.GridSpec(3, 1, hspace=0.35,
                              top=0.960, bottom=0.04, left=0.04, right=0.97)

    lengths_rows = [
        (4,  'Prefijos de 4 movimientos  (2 jugadas por color)  — alta recurrencia',  8),
        (8,  'Prefijos de 8 movimientos  (4 jugadas por color)  — divergencia media',  6),
        (16, 'Prefijos de 16 movimientos (8 jugadas por color)  — baja recurrencia',   5),
    ]

    for row_idx, (length, row_title, n_show) in enumerate(lengths_rows):
        counter = A['prefix_counts'].get(length, Counter())
        top     = counter.most_common(n_show)
        if not top:
            continue

        row_gs = gridspec.GridSpecFromSubplotSpec(
            1, n_show, subplot_spec=outer[row_idx], wspace=0.06)

        for rank, (seq_str, count) in enumerate(top):
            ax = fig.add_subplot(row_gs[rank])
            stones = _parse_seq(seq_str)
            pct    = 100 * count / total
            short  = sshort(stones)
            draw_board(
                ax, stones=stones,
                title=f'#{rank+1}  {count} juegos  ({pct:.1f}%)\n{short}',
                stone_size=0.42, num_size=4.5,
            )

        # Titulo de la fila
        fig.text(0.50, outer[row_idx].get_position(fig).y1 + 0.003,
                 row_title,
                 ha='center', va='bottom', fontsize=9,
                 fontweight='bold', color='#444',
                 transform=fig.transFigure)

    out = os.path.join(RES, 'sgf_top_openings.png')
    plt.savefig(out, dpi=150, bbox_inches='tight', facecolor=BG)
    print(f'  sgf_top_openings.png')
    plt.close(fig)


# ─────────────────────────────────────────────────────────────────────────────
# Figura 3: histograma de divergencia
# ─────────────────────────────────────────────────────────────────────────────

def build_histogram_viz(A, total):
    """
    Tres paneles que muestran cómo se divergen las partidas conforme avanza
    la apertura:

    Panel A  — Secuencias únicas por longitud de prefijo
               Cuántas aperturas distintas existen al turno k?

    Panel B  — Concentración: qué % de partidas sigue la misma secuencia
               Barras apiladas: top-1 / top-2..5 / top-6..20 / resto

    Panel C  — Frecuencia del patrón #1 y #5 al turno k
               Muestra la velocidad de divergencia en curva
    """
    ks        = list(range(1, N + 1))
    n_unique  = [len(A['prefix_counts'][k]) for k in ks]
    top1_pct  = [100 * A['prefix_counts'][k].most_common(1)[0][1] / total
                 if A['prefix_counts'][k] else 0  for k in ks]

    # Concentración acumulada: top-1, top-2..5, top-6..20, resto
    def cum_pct(k, lo, hi):
        tops = A['prefix_counts'][k].most_common(hi)
        s = sum(cnt for _, cnt in tops[lo:hi])
        return 100 * s / total

    c_top1   = [cum_pct(k, 0, 1)   for k in ks]
    c_top2_5 = [cum_pct(k, 1, 5)   for k in ks]
    c_top6_20= [cum_pct(k, 5, 20)  for k in ks]
    c_rest   = [100 - c_top1[i] - c_top2_5[i] - c_top6_20[i] for i in range(N)]

    fig, axes = plt.subplots(1, 3, figsize=(22, 7), facecolor=BG)
    fig.suptitle(
        f'Divergencia de Aperturas — Primeros {N} Movimientos  ·  {total} partidas',
        fontsize=13, fontweight='bold', color='#1a1a1a', y=1.01,
    )

    clr = {'bg': BG, 'top1': '#C0392B', 'top5': '#E67E22',
           'top20': '#F1C40F', 'rest': '#BDC3C7',
           'line': '#2C3E50', 'grid': '#C8BCA8'}

    # ── Panel A: secuencias únicas ────────────────────────────────────────
    ax = axes[0]
    ax.set_facecolor(BG)
    ax.bar(ks, n_unique, color='#5D6D7E', edgecolor='none', alpha=0.85)
    ax.set_xlabel('Turno (longitud del prefijo)', fontsize=10)
    ax.set_ylabel('Secuencias únicas', fontsize=10)
    ax.set_title('¿Cuántas aperturas distintas\nexisten al turno k?', fontsize=11)
    ax.yaxis.grid(True, color=clr['grid'], linewidth=0.6, linestyle='--', zorder=0)
    ax.set_axisbelow(True)
    ax.spines[['top','right']].set_visible(False)
    ax.set_facecolor(BG)
    # Anotar saltos relevantes
    for k in [1, 2, 4, 6, 10, 20, 30]:
        if k <= N:
            ax.text(k, n_unique[k-1] + total*0.005, str(n_unique[k-1]),
                    ha='center', va='bottom', fontsize=7.5, color='#333')

    # ── Panel B: barras apiladas de concentración ─────────────────────────
    ax = axes[1]
    ax.set_facecolor(BG)
    xs = np.array(ks)
    ax.bar(xs, c_top1,   color=clr['top1'],  label='Secuencia #1',      edgecolor='none')
    ax.bar(xs, c_top2_5, bottom=c_top1,
           color=clr['top5'],  label='#2 – #5',           edgecolor='none')
    bottom2 = [a + b for a, b in zip(c_top1, c_top2_5)]
    ax.bar(xs, c_top6_20, bottom=bottom2,
           color=clr['top20'], label='#6 – #20',           edgecolor='none')
    bottom3 = [a + b for a, b in zip(bottom2, c_top6_20)]
    ax.bar(xs, c_rest,   bottom=bottom3,
           color=clr['rest'],  label='Resto',              edgecolor='none', alpha=0.7)
    ax.axhline(100, color='#888', lw=0.5, ls='--')
    ax.set_xlabel('Turno (longitud del prefijo)', fontsize=10)
    ax.set_ylabel('% de partidas', fontsize=10)
    ax.set_title('Concentración de aperturas:\n¿cuántas partidas siguen la misma secuencia?',
                 fontsize=11)
    ax.legend(loc='upper right', fontsize=8, framealpha=0.85)
    ax.set_ylim(0, 108)
    ax.yaxis.grid(True, color=clr['grid'], linewidth=0.6, linestyle='--', zorder=0)
    ax.set_axisbelow(True)
    ax.spines[['top','right']].set_visible(False)
    ax.set_facecolor(BG)

    # ── Panel C: curva de frecuencia del top-1 ───────────────────────────
    ax = axes[2]
    ax.set_facecolor(BG)
    ax.plot(ks, top1_pct, '-o', color=clr['top1'], lw=2, ms=4,
            label='Patrón #1 (más común)')

    # Añadir curva del top-5 agregado
    top5_pct = [c_top1[i] + c_top2_5[i] for i in range(N)]
    ax.plot(ks, top5_pct, '-s', color=clr['top5'], lw=1.5, ms=3.5,
            label='Top-5 combinado', alpha=0.85)

    ax.set_xlabel('Turno (longitud del prefijo)', fontsize=10)
    ax.set_ylabel('% de partidas', fontsize=10)
    ax.set_title('Velocidad de divergencia:\n% que comparte la apertura más popular',
                 fontsize=11)
    ax.yaxis.grid(True, color=clr['grid'], linewidth=0.6, linestyle='--', zorder=0)
    ax.set_axisbelow(True)
    ax.spines[['top','right']].set_visible(False)
    ax.legend(fontsize=9, framealpha=0.85)
    ax.set_facecolor(BG)

    # Anotar puntos clave
    for k in [1, 2, 4, 6, 10, 20, 30]:
        if k <= N:
            ax.annotate(f'{top1_pct[k-1]:.1f}%',
                        xy=(k, top1_pct[k-1]),
                        xytext=(4, 4), textcoords='offset points',
                        fontsize=7, color=clr['top1'])

    plt.tight_layout(rect=[0, 0, 1, 0.97])
    out = os.path.join(RES, 'sgf_histogram.png')
    plt.savefig(out, dpi=150, bbox_inches='tight', facecolor=BG)
    print(f'  sgf_histogram.png')
    plt.close(fig)


# ─────────────────────────────────────────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────────────────────────────────────────

def main():
    print('\n' + '='*60)
    print('  EXTRACCION DE PATRONES — SGF DATA')
    print('='*60)

    games = load_games(DATA)
    total = len(games)
    A     = analyze(games)

    # ── Consola: top patrones por longitud ─────────────────────────────────
    print(f'\n  Total de juegos analizados: {total}')
    for length in [2, 4, 6, 10, 16, 20, 30]:
        if length > N:
            continue
        counter  = A['prefix_counts'][length]
        n_unique = len(counter)
        top3     = counter.most_common(3)
        print(f'\n  Prefijos de longitud {length:2d}  '
              f'({n_unique} secuencias unicas de {total}):')
        for rank, (seq, cnt) in enumerate(top3, 1):
            pct   = 100 * cnt / total
            short = sshort(_parse_seq(seq))
            print(f'    #{rank}  {cnt:4d} juegos  ({pct:5.1f}%)  {short}')

    # ── Posicion mas comun para cada movimiento ─────────────────────────────
    print(f'\n  Posicion mas frecuente por turno:')
    for k in range(N):
        freq  = A['pos_freq'][k]
        idx   = np.unravel_index(freq.argmax(), (SIZE, SIZE))
        pos   = go19(idx[1], idx[0])
        cnt   = freq.max()
        pct   = 100 * cnt / total
        color = 'B' if k % 2 == 0 else 'W'
        print(f'    Mov {k+1:2d} ({color})  {pos:>4}  '
              f'{cnt:4d} juegos  ({pct:5.1f}%)')

    # ── Archivos ────────────────────────────────────────────────────────────
    print('\n  Generando archivos...')
    build_openings_csv(games)
    build_patterns_csv(A['prefix_counts'], total)
    build_heatmap_viz(A, total)
    build_top_openings_viz(A, total)
    build_histogram_viz(A, total)

    print('\n' + '='*60)
    print(f'  Listo. Salidas en results/')
    print('='*60 + '\n')


if __name__ == '__main__':
    main()
