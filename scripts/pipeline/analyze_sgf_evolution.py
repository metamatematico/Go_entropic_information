"""
analyze_sgf_evolution.py
========================
Analiza la evolución energética de partidas SGF reales por turnos y por
bloques de jugadas (fases: 1-10, 11-20, 21-30, ...).

Para cada movimiento, calcula la energía de Ising (M1 Mercado & Jiménez y
Alvarado) con las 4 intersecciones vecinas ocupadas.

Salidas:
  results/05_partidas_reales/sgf_evolution_by_move.csv    -- una fila por (partida, turno)
  results/05_partidas_reales/sgf_evolution_by_block.csv   -- estadisticas por bloque
  results/05_partidas_reales/sgf_phase_heatmaps.png       -- mapas de calor por fase
  results/05_partidas_reales/sgf_phase_energy.png         -- curvas de energia por bloque
  results/05_partidas_reales/sgf_phase_sequences.png      -- secuencias por fase
"""

import os, re, csv, sys
from pathlib import Path
from collections import defaultdict
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.gridspec as gridspec
from matplotlib.patches import FancyBboxPatch

BASE    = str(Path(__file__).resolve().parents[2])
DATA    = os.path.join(BASE, 'data', 'sgf_partidas')
RES     = os.path.join(BASE, 'results', '05_partidas_reales')
RES_T   = RES
RES_F   = RES
os.makedirs(RES, exist_ok=True)

SIZE     = 19
MAX_MOVE = 60          # analizar hasta el movimiento 60
BLOCK    = 10          # tamaño de cada bloque/fase
BLOCKS   = [(i*BLOCK+1, (i+1)*BLOCK) for i in range(MAX_MOVE // BLOCK)]
# → [(1,10),(11,20),(21,30),(31,40),(41,50),(51,60)]

BG   = '#F5F0E8'
WOOD = '#DEB887'
NEIGHBORS = [(-1,0),(1,0),(0,-1),(0,1)]

SPIN = {'B': -1.0, 'W': +1.0}   # vacío = 0.0

PHASE_COLORS = [
    '#C0392B',   # Fase 1  (1-10)
    '#E67E22',   # Fase 2  (11-20)
    '#F1C40F',   # Fase 3  (21-30)
    '#27AE60',   # Fase 4  (31-40)
    '#2980B9',   # Fase 5  (41-50)
    '#8E44AD',   # Fase 6  (51-60)
]


# ─────────────────────────────────────────────────────────────────────────────
# Hamiltoniano M1 (Mercado & Jiménez)
# ─────────────────────────────────────────────────────────────────────────────

def H_M1(s0, s1):
    """H(s0,s1) = s0 + 2·s1 − s0·s1² − s0²·s1"""
    return s0 + 2*s1 - s0*(s1**2) - (s0**2)*s1


def H_AL(s0, s1):
    """Alvarado: H(xi,xj) = xi·xj"""
    return s0 * s1


# ─────────────────────────────────────────────────────────────────────────────
# Parsing SGF
# ─────────────────────────────────────────────────────────────────────────────

def parse_sgf(path, max_move=MAX_MOVE):
    """Lee .sgf → lista de (color, row, col) hasta max_move jugadas."""
    text = Path(path).read_text(encoding='utf-8', errors='ignore')
    sz = re.search(r'SZ\[(\d+)\]', text)
    if not sz or int(sz.group(1)) != SIZE:
        return None
    moves = []
    for m in re.finditer(r'(?<![A-Z]);([BW])\[([a-s]{2})\]', text):
        col = ord(m.group(2)[0]) - ord('a')
        row = ord(m.group(2)[1]) - ord('a')
        if 0 <= col < SIZE and 0 <= row < SIZE:
            moves.append((m.group(1), row, col))
        if len(moves) == max_move:
            break
    return moves if len(moves) >= BLOCK else None


def load_games(sgf_dir, max_games=3000):
    games = {}
    paths = sorted(Path(sgf_dir).glob('*.sgf'))
    for p in paths[:max_games]:
        moves = parse_sgf(p)
        if moves:
            games[p.stem] = moves
    print(f'  Cargadas: {len(games)} partidas')
    return games


# ─────────────────────────────────────────────────────────────────────────────
# Energía por movimiento
# ─────────────────────────────────────────────────────────────────────────────

def compute_move_energies(moves):
    """
    Para cada movimiento, devuelve dict con energías M1 y Alvarado
    del nuevo spin con sus 4 vecinos (ya ocupados en ese turno).
    """
    board = np.zeros((SIZE, SIZE), dtype=float)  # 0=vacío, -1=B, +1=W
    rows = []
    for turn_idx, (color, r, c) in enumerate(moves):
        s0 = SPIN[color]
        board[r, c] = s0

        # Energías con vecinos inmediatos
        e_m1 = 0.0
        e_al = 0.0
        n_occ = 0
        for dr, dc in NEIGHBORS:
            nr, nc = r+dr, c+dc
            if 0 <= nr < SIZE and 0 <= nc < SIZE:
                s1 = board[nr, nc]
                if s1 != 0:           # vecino ocupado
                    e_m1 += H_M1(s0, s1)
                    e_al  += H_AL(s0, s1)
                    n_occ += 1

        rows.append({
            'turn':   turn_idx + 1,
            'color':  color,
            'row':    r,
            'col':    c,
            'n_occ':  n_occ,
            'E_M1':   e_m1,
            'E_AL':   e_al,
        })
    return rows


# ─────────────────────────────────────────────────────────────────────────────
# Agregación por bloque
# ─────────────────────────────────────────────────────────────────────────────

def block_label(t_start, t_end):
    return f'{t_start}-{t_end}'


def aggregate_by_block(all_move_rows):
    """
    all_move_rows: lista de dicts con campos 'turn','E_M1','E_AL','row','col'
    Devuelve lista de dicts, uno por (bloque).
    """
    blocks_data = defaultdict(lambda: {'E_M1': [], 'E_AL': [], 'positions': []})

    for row in all_move_rows:
        t = row['turn']
        for t_start, t_end in BLOCKS:
            if t_start <= t <= t_end:
                lbl = block_label(t_start, t_end)
                blocks_data[lbl]['E_M1'].append(row['E_M1'])
                blocks_data[lbl]['E_AL'].append(row['E_AL'])
                blocks_data[lbl]['positions'].append((row['row'], row['col']))
                break

    result = []
    for t_start, t_end in BLOCKS:
        lbl = block_label(t_start, t_end)
        d = blocks_data[lbl]
        em1 = np.array(d['E_M1'])
        eal = np.array(d['E_AL'])
        result.append({
            'block':          lbl,
            't_start':        t_start,
            't_end':          t_end,
            'n_moves':        len(em1),
            'E_M1_mean':      em1.mean() if len(em1) else np.nan,
            'E_M1_std':       em1.std()  if len(em1) else np.nan,
            'E_M1_median':    np.median(em1) if len(em1) else np.nan,
            'E_M1_min':       em1.min()  if len(em1) else np.nan,
            'E_M1_max':       em1.max()  if len(em1) else np.nan,
            'E_AL_mean':      eal.mean() if len(eal) else np.nan,
            'E_AL_std':       eal.std()  if len(eal) else np.nan,
            'E_AL_median':    np.median(eal) if len(eal) else np.nan,
            'E_AL_min':       eal.min()  if len(eal) else np.nan,
            'E_AL_max':       eal.max()  if len(eal) else np.nan,
        })
    return result


# ─────────────────────────────────────────────────────────────────────────────
# CSVs
# ─────────────────────────────────────────────────────────────────────────────

def save_by_move_csv(all_rows, path):
    fields = ['game_id','turn','color','row','col','n_occ','E_M1','E_AL']
    with open(path, 'w', newline='', encoding='utf-8') as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        w.writerows(all_rows)
    print(f'  {Path(path).name}  ({len(all_rows)} filas)')


def save_by_block_csv(block_rows, path):
    fields = ['block','t_start','t_end','n_moves',
              'E_M1_mean','E_M1_std','E_M1_median','E_M1_min','E_M1_max',
              'E_AL_mean','E_AL_std','E_AL_median','E_AL_min','E_AL_max']
    with open(path, 'w', newline='', encoding='utf-8') as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        w.writerows(block_rows)
    print(f'  {Path(path).name}  ({len(block_rows)} filas)')


# ─────────────────────────────────────────────────────────────────────────────
# FIGURA 1: Curvas de energía por bloque
# ─────────────────────────────────────────────────────────────────────────────

def draw_phase_energy(per_turn_stats, block_rows, total_games):
    """
    per_turn_stats: dict turn → {'E_M1': array, 'E_AL': array}
    """
    turns    = sorted(per_turn_stats.keys())
    m1_mean  = [per_turn_stats[t]['E_M1'].mean()     for t in turns]
    m1_std   = [per_turn_stats[t]['E_M1'].std()      for t in turns]
    al_mean  = [per_turn_stats[t]['E_AL'].mean()     for t in turns]
    al_std   = [per_turn_stats[t]['E_AL'].std()      for t in turns]

    fig, axes = plt.subplots(2, 2, figsize=(20, 12), facecolor=BG)
    fig.suptitle(
        f'Evolución Energética por Turno y por Fase — {total_games} partidas\n'
        f'Modelos M1 (Mercado & Jiménez) y Alvarado  ·  Movimientos 1-{MAX_MOVE}',
        fontsize=13, fontweight='bold', color='#1a1a1a', y=0.998,
    )

    ta = np.array(turns)

    # ── Panel A: energía M1 por turno ────────────────────────────────────────
    ax = axes[0, 0]
    ax.set_facecolor(BG)
    ax.fill_between(ta, np.array(m1_mean)-np.array(m1_std),
                    np.array(m1_mean)+np.array(m1_std),
                    alpha=0.20, color='#C0392B', label='±1σ')
    ax.plot(ta, m1_mean, '-', color='#C0392B', lw=2, label='Media E_M1')
    ax.axhline(0, color='#888', lw=0.7, ls='--')
    # Sombrear fases
    for i, (t_start, t_end) in enumerate(BLOCKS):
        ax.axvspan(t_start-0.5, t_end+0.5, alpha=0.07,
                   color=PHASE_COLORS[i], zorder=0)
        ax.text((t_start+t_end)/2, ax.get_ylim()[0] if ax.get_ylim()[0] != 0 else -0.1,
                f'F{i+1}', ha='center', fontsize=7.5, color=PHASE_COLORS[i],
                transform=ax.get_xaxis_transform())
    ax.set_xlabel('Turno', fontsize=10); ax.set_ylabel('Energía M1', fontsize=10)
    ax.set_title('Energía M1 promedio por turno\n(Modelo Mercado & Jiménez)', fontsize=11)
    ax.legend(fontsize=9); ax.spines[['top','right']].set_visible(False)
    ax.yaxis.grid(True, color='#C8BCA8', lw=0.5, ls='--', zorder=0)
    ax.set_axisbelow(True)

    # ── Panel B: energía Alvarado por turno ──────────────────────────────────
    ax = axes[0, 1]
    ax.set_facecolor(BG)
    ax.fill_between(ta, np.array(al_mean)-np.array(al_std),
                    np.array(al_mean)+np.array(al_std),
                    alpha=0.20, color='#2980B9', label='±1σ')
    ax.plot(ta, al_mean, '-', color='#2980B9', lw=2, label='Media E_AL')
    ax.axhline(0, color='#888', lw=0.7, ls='--')
    for i, (t_start, t_end) in enumerate(BLOCKS):
        ax.axvspan(t_start-0.5, t_end+0.5, alpha=0.07,
                   color=PHASE_COLORS[i], zorder=0)
    ax.set_xlabel('Turno', fontsize=10); ax.set_ylabel('Energía Alvarado', fontsize=10)
    ax.set_title('Energía Alvarado promedio por turno\n(Modelo Atomic-Go)', fontsize=11)
    ax.legend(fontsize=9); ax.spines[['top','right']].set_visible(False)
    ax.yaxis.grid(True, color='#C8BCA8', lw=0.5, ls='--', zorder=0)
    ax.set_axisbelow(True)

    # ── Panel C: comparativa de medias por bloque (barras) ───────────────────
    ax = axes[1, 0]
    ax.set_facecolor(BG)
    labels     = [r['block'] for r in block_rows]
    m1_means_b = [r['E_M1_mean'] for r in block_rows]
    al_means_b = [r['E_AL_mean'] for r in block_rows]
    x = np.arange(len(labels))
    w = 0.35
    bars1 = ax.bar(x-w/2, m1_means_b, w, color='#C0392B', alpha=0.85,
                   label='M1', edgecolor='none')
    bars2 = ax.bar(x+w/2, al_means_b, w, color='#2980B9', alpha=0.85,
                   label='Alvarado', edgecolor='none')
    ax.axhline(0, color='#888', lw=0.7, ls='--')
    ax.set_xticks(x); ax.set_xticklabels([f'Fase {i+1}\n({l})' for i,l in enumerate(labels)],
                                          fontsize=8)
    ax.set_ylabel('Energía media de enlace', fontsize=10)
    ax.set_title('Energía media por fase de la partida\n(bloques de 10 movimientos)', fontsize=11)
    ax.legend(fontsize=9); ax.spines[['top','right']].set_visible(False)
    ax.yaxis.grid(True, color='#C8BCA8', lw=0.5, ls='--', zorder=0)
    ax.set_axisbelow(True)
    # Anotar valores
    for bar in bars1:
        h = bar.get_height()
        ax.text(bar.get_x()+bar.get_width()/2, h + (0.01 if h >= 0 else -0.05),
                f'{h:.3f}', ha='center', va='bottom', fontsize=7, color='#C0392B')
    for bar in bars2:
        h = bar.get_height()
        ax.text(bar.get_x()+bar.get_width()/2, h + (0.01 if h >= 0 else -0.05),
                f'{h:.3f}', ha='center', va='bottom', fontsize=7, color='#2980B9')

    # ── Panel D: desviación estándar por fase ────────────────────────────────
    ax = axes[1, 1]
    ax.set_facecolor(BG)
    m1_stds_b = [r['E_M1_std'] for r in block_rows]
    al_stds_b = [r['E_AL_std'] for r in block_rows]
    ax.plot(range(1, len(labels)+1), m1_stds_b, '-o', color='#C0392B',
            lw=2, ms=7, label='M1 σ')
    ax.plot(range(1, len(labels)+1), al_stds_b, '-s', color='#2980B9',
            lw=2, ms=7, label='Alvarado σ')
    for i, (sm, sa) in enumerate(zip(m1_stds_b, al_stds_b)):
        ax.text(i+1, sm+0.01, f'{sm:.3f}', ha='center', fontsize=7.5,
                color='#C0392B')
        ax.text(i+1, sa-0.03, f'{sa:.3f}', ha='center', fontsize=7.5,
                color='#2980B9', va='top')
    ax.set_xticks(range(1, len(labels)+1))
    ax.set_xticklabels([f'F{i+1}' for i in range(len(labels))], fontsize=9)
    ax.set_ylabel('Desviación estándar σ', fontsize=10)
    ax.set_title('Variabilidad energética por fase\n(dispersión entre partidas)', fontsize=11)
    ax.legend(fontsize=9); ax.spines[['top','right']].set_visible(False)
    ax.yaxis.grid(True, color='#C8BCA8', lw=0.5, ls='--', zorder=0)
    ax.set_axisbelow(True)

    plt.tight_layout(rect=[0, 0, 1, 0.97])
    out = os.path.join(RES_F, 'sgf_phase_energy.png')
    plt.savefig(out, dpi=150, bbox_inches='tight', facecolor=BG)
    print(f'  sgf_phase_energy.png')
    plt.close(fig)


# ─────────────────────────────────────────────────────────────────────────────
# FIGURA 2: Mapas de calor por fase
# ─────────────────────────────────────────────────────────────────────────────

def draw_board_heatmap(ax, freq_map, title='', vmax=None, phase_color='#333'):
    ax.set_facecolor(WOOD)
    ax.set_xlim(-0.5, 18.5); ax.set_ylim(-0.5, 18.5)
    ax.set_aspect('equal')
    ax.tick_params(left=False, bottom=False, labelleft=False, labelbottom=False)
    for sp in ax.spines.values():
        sp.set_color(phase_color); sp.set_linewidth(1.5)
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
                alpha = min(0.92, 0.15 + 0.77 * v / vmax)
                ax.add_patch(plt.Circle((c, dy), 0.40,
                             fc=rgba[:3]+(alpha,), ec='none', zorder=3))
    ax.set_title(title, fontsize=8, pad=4, color='#1a1a1a',
                 fontweight='bold')


def draw_phase_heatmaps(per_block_positions, total_games):
    n_blocks = len(BLOCKS)
    fig = plt.figure(figsize=(24, 10), facecolor=BG)
    fig.suptitle(
        f'Distribución Espacial de Jugadas por Fase\n'
        f'{total_games} partidas profesionales  ·  bloques de {BLOCK} movimientos',
        fontsize=13, fontweight='bold', y=1.01, color='#1a1a1a',
    )
    gs = gridspec.GridSpec(1, n_blocks, wspace=0.06,
                           left=0.02, right=0.98, top=0.90, bottom=0.02)

    # Calcular vmax global
    freq_maps = []
    for i, (t_start, t_end) in enumerate(BLOCKS):
        lbl = block_label(t_start, t_end)
        freq = np.zeros((SIZE, SIZE), dtype=int)
        for r, c in per_block_positions.get(lbl, []):
            freq[r, c] += 1
        freq_maps.append(freq)
    vmax = max(f.max() for f in freq_maps) or 1

    for i, ((t_start, t_end), freq) in enumerate(zip(BLOCKS, freq_maps)):
        ax = fig.add_subplot(gs[i])
        n_total_moves = freq.sum()
        n_cells = (freq > 0).sum()
        draw_board_heatmap(
            ax, freq,
            title=f'Fase {i+1}  ({t_start}-{t_end})\n{n_total_moves:,} jugadas · {n_cells} celdas',
            vmax=vmax,
            phase_color=PHASE_COLORS[i],
        )
        # Borde de color de fase
        for sp in ax.spines.values():
            sp.set_linewidth(2.0)
            sp.set_color(PHASE_COLORS[i])

    out = os.path.join(RES_F, 'sgf_phase_heatmaps.png')
    plt.savefig(out, dpi=150, bbox_inches='tight', facecolor=BG)
    print(f'  sgf_phase_heatmaps.png')
    plt.close(fig)


# ─────────────────────────────────────────────────────────────────────────────
# FIGURA 3: Secuencias de aperturas más comunes por fase
# ─────────────────────────────────────────────────────────────────────────────

COLS_19 = 'ABCDEFGHJKLMNOPQRST'

def go19(col, row):
    return f'{COLS_19[col]}{SIZE - row}'


def draw_stone_board(ax, stones, title='', phase_color='#333'):
    ax.set_facecolor(WOOD)
    ax.set_xlim(-0.5, 18.5); ax.set_ylim(-0.5, 18.5)
    ax.set_aspect('equal')
    ax.tick_params(left=False, bottom=False, labelleft=False, labelbottom=False)
    for sp in ax.spines.values():
        sp.set_color(phase_color); sp.set_linewidth(1.5)
    for k in range(SIZE):
        ax.plot([0, 18], [k, k], '-', color='#5C3D00', lw=0.25, zorder=1)
        ax.plot([k, k], [0, 18], '-', color='#5C3D00', lw=0.25, zorder=1)
    for hx in [3, 9, 15]:
        for hy in [3, 9, 15]:
            ax.plot(hx, hy, 'o', color='#5C3D00', ms=1.8, zorder=2)
    for k, (color, r, c) in enumerate(stones, 1):
        dy = (SIZE - 1) - r
        fc = '#111' if color == 'B' else '#F5F0E8'
        ec = '#333' if color == 'B' else '#888'
        tc = '#FFF' if color == 'B' else '#000'
        ax.add_patch(plt.Circle((c, dy), 0.42, fc=fc, ec=ec, lw=0.8, zorder=5))
        ax.text(c, dy, str(k), ha='center', va='center',
                fontsize=4, color=tc, fontweight='bold', zorder=6)
    ax.set_title(title, fontsize=7, pad=3, color='#1a1a1a')


def draw_phase_sequences(games, total_games):
    """Muestra los 3 primeros movimientos acumulados por fase para las partidas más largas."""
    from collections import Counter

    # Para cada fase, encontrar las secuencias de esos turnos más frecuentes
    phase_seq_counters = {i: Counter() for i in range(len(BLOCKS))}
    phase_game_stones  = {i: defaultdict(list) for i in range(len(BLOCKS))}

    for gid, moves in games.items():
        for i, (t_start, t_end) in enumerate(BLOCKS):
            # Jugadas de esta fase (turno relativo dentro del bloque)
            phase_moves = [(c, r, col) for k, (c, r, col) in enumerate(moves)
                           if t_start <= k+1 <= t_end]
            if len(phase_moves) < BLOCK:
                continue   # partida más corta, skip
            key = '|'.join(f'{c}:{go19(col, r)}' for c, r, col in phase_moves)
            phase_seq_counters[i][key] += 1

    n_blocks = len(BLOCKS)
    n_show   = 3   # top-3 secuencias por fase
    fig = plt.figure(figsize=(26, 6 * n_blocks), facecolor=BG)
    fig.suptitle(
        f'Secuencias Más Frecuentes por Fase  ·  {total_games} partidas\n'
        f'Top-{n_show} secuencias exactas de cada bloque de {BLOCK} movimientos',
        fontsize=13, fontweight='bold', y=1.005, color='#1a1a1a',
    )
    outer = gridspec.GridSpec(n_blocks, 1, hspace=0.55,
                              top=0.975, bottom=0.02, left=0.02, right=0.98)

    for i, (t_start, t_end) in enumerate(BLOCKS):
        top = phase_seq_counters[i].most_common(n_show)
        if not top:
            continue
        inner = gridspec.GridSpecFromSubplotSpec(1, n_show, subplot_spec=outer[i],
                                                  wspace=0.05)
        for rank, (seq_str, count) in enumerate(top):
            ax = fig.add_subplot(inner[rank])
            # Reconstruir stones desde la secuencia global hasta el final de esta fase
            # (necesitamos las piedras anteriores también)
            pct = 100 * count / total_games

            # Parsear sólo las jugadas de esta fase
            phase_stones = []
            for part in seq_str.split('|'):
                c_color, pos = part.split(':')
                col_letter = pos[0]
                row_num    = int(pos[1:])
                col_idx    = COLS_19.index(col_letter)
                row_idx    = SIZE - row_num
                phase_stones.append((c_color, row_idx, col_idx))

            draw_stone_board(
                ax, phase_stones,
                title=(f'Fase {i+1}  #{rank+1}  —  {count} partidas ({pct:.1f}%)\n'
                       f'Movs {t_start}-{t_end}'),
                phase_color=PHASE_COLORS[i],
            )

        # Etiqueta lateral
        fig.text(0.002, (outer[i].get_position(fig).y0 +
                         outer[i].get_position(fig).y1) / 2,
                 f'Fase {i+1}\n{t_start}-{t_end}',
                 va='center', ha='left', fontsize=9,
                 fontweight='bold', color=PHASE_COLORS[i],
                 rotation=90, transform=fig.transFigure)

    out = os.path.join(RES_F, 'sgf_phase_sequences.png')
    plt.savefig(out, dpi=140, bbox_inches='tight', facecolor=BG)
    print(f'  sgf_phase_sequences.png')
    plt.close(fig)


# ─────────────────────────────────────────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────────────────────────────────────────

def main():
    print('\n' + '='*62)
    print('  ANÁLISIS DE EVOLUCIÓN POR FASES — SGF DATA')
    print('='*62)

    games = load_games(DATA)
    total = len(games)

    print(f'\n  Analizando {total} partidas hasta el mov {MAX_MOVE}...')

    # Recopilar energías por turno
    all_move_rows       = []   # lista de dicts para CSV by-move
    per_turn_stats      = defaultdict(lambda: {'E_M1': [], 'E_AL': []})
    per_block_positions = defaultdict(list)
    all_move_rows_typed = []   # con game_id

    for gid, moves in games.items():
        move_data = compute_move_energies(moves)
        for d in move_data:
            row = {'game_id': gid, **d}
            all_move_rows_typed.append(row)
            t = d['turn']
            per_turn_stats[t]['E_M1'].append(d['E_M1'])
            per_turn_stats[t]['E_AL'].append(d['E_AL'])
            # Posiciones por bloque
            for t_start, t_end in BLOCKS:
                if t_start <= t <= t_end:
                    lbl = block_label(t_start, t_end)
                    per_block_positions[lbl].append((d['row'], d['col']))
                    break

    # Convertir listas a arrays
    for t in per_turn_stats:
        per_turn_stats[t]['E_M1'] = np.array(per_turn_stats[t]['E_M1'])
        per_turn_stats[t]['E_AL'] = np.array(per_turn_stats[t]['E_AL'])

    # Agregar por bloque (sobre todos los juegos)
    all_move_rows_flat = [{'turn': r['turn'], 'E_M1': r['E_M1'], 'E_AL': r['E_AL'],
                            'row': r['row'], 'col': r['col']}
                           for r in all_move_rows_typed]
    block_rows = aggregate_by_block(all_move_rows_flat)

    # Resumen en consola
    print('\n  Estadisticas por fase (energia M1):')
    for b in block_rows:
        print(f"    Fase {b['block']:8s}  "
              f"media={b['E_M1_mean']:+.4f}  "
              f"std={b['E_M1_std']:.4f}  "
              f"n={b['n_moves']:,}")

    # CSV
    print('\n  Guardando CSVs...')
    save_by_move_csv(
        all_move_rows_typed,
        os.path.join(RES_T, 'sgf_evolution_by_move.csv')
    )
    save_by_block_csv(
        block_rows,
        os.path.join(RES_T, 'sgf_evolution_by_block.csv')
    )

    # Figuras
    print('\n  Generando figuras...')
    draw_phase_energy(per_turn_stats, block_rows, total)
    draw_phase_heatmaps(per_block_positions, total)
    draw_phase_sequences(games, total)

    print('\n' + '='*62)
    print('  Listo.')
    print('='*62 + '\n')


if __name__ == '__main__':
    main()
