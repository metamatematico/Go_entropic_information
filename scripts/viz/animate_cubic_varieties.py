#!/usr/bin/env python3
"""
animate_cubic_varieties.py
==========================
GIF animado: una partida de Go evolucionando sobre las variedades cúbicas
V±1 de H_M1(x,y) = x + 2y - xy² - x²y.

Panel izquierdo : tablero 19×19 con la partida en curso.
Panel derecho   : variedad cúbica con los enlaces acumulados y destello
                  de los nuevos enlaces de cada jugada.

Uso:
    python animate_cubic_varieties.py            # usa la 1ª partida del directorio
    python animate_cubic_varieties.py  42        # usa el índice 42 (0-based)
    python animate_cubic_varieties.py  nombre.sgf

Genera:
    results/05_partidas_reales/variety_game_<nombre>.gif
"""

import os
import sys
import re
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.animation as animation
from matplotlib.colors import Normalize
from matplotlib import cm
from pathlib import Path
from collections import Counter

# ── Rutas ──────────────────────────────────────────────────────────────────────
BASE = str(Path(__file__).resolve().parents[2])
DATA = os.path.join(BASE, 'data', 'sgf_partidas')
RES  = os.path.join(BASE, 'results', '05_partidas_reales')

# ── Hamiltonianos ──────────────────────────────────────────────────────────────
def H_M1(x, y):
    return x + 2*y - x*(y**2) - (x**2)*y

# ── Constantes ─────────────────────────────────────────────────────────────────
SPIN_MAP  = {'B': -1.0, 'W': 1.0}
DIRS      = [(0,1),(0,-1),(1,0),(-1,0)]
VALID_P   = [(-1,-1),(-1,0),(-1,1),(1,-1),(1,0),(1,1)]
PAIR_LABEL = {(-1,-1):'B–B',(-1,0):'B–∅',(-1,1):'B–W',
              ( 1,-1):'W–B',( 1,0):'W–∅',( 1,1):'W–W'}

# Colores de pares en la variedad: azul para V-1, rojo para V+1
PAIR_COLOR = {(-1,-1):'#1A5276',(-1,0):'#1A5276',(-1,1):'#C0392B',
              ( 1,-1):'#1A5276',( 1,0):'#C0392B',( 1,1):'#C0392B'}

STAR_PTS  = [(3,3),(3,9),(3,15),(9,3),(9,9),(9,15),(15,3),(15,9),(15,15)]
TRAIL_LEN = 6   # jugadas que permanecen visibles como destello (decae)

_MOVE_RE  = re.compile(r'(?<![A-Z]);([BW])\[([a-s]{2})\]')

# ── SGF ────────────────────────────────────────────────────────────────────────
def parse_sgf(path):
    text = open(path, encoding='utf-8', errors='ignore').read()
    moves = []
    for m in _MOVE_RE.finditer(text):
        p, coords = m.group(1), m.group(2)
        c, r = ord(coords[0])-97, ord(coords[1])-97
        if 0 <= c < 19 and 0 <= r < 19:
            moves.append((p, c, r))
    return moves

# ── Lógica de captura ──────────────────────────────────────────────────────────
def _group(board, r, c, color):
    grp, stack = set(), [(r,c)]
    while stack:
        nr, nc = stack.pop()
        if (nr,nc) in grp: continue
        if not (0<=nr<19 and 0<=nc<19): continue
        if board[nr,nc] != color: continue
        grp.add((nr,nc))
        for dr,dc in DIRS:
            stack.append((nr+dr, nc+dc))
    return grp

def _has_lib(board, grp):
    for r,c in grp:
        for dr,dc in DIRS:
            nr,nc = r+dr, c+dc
            if 0<=nr<19 and 0<=nc<19 and board[nr,nc]==0:
                return True
    return False

def place(board, r, c, player):
    opp = -player
    board[r,c] = player
    for dr,dc in DIRS:
        nr,nc = r+dr, c+dc
        if 0<=nr<19 and 0<=nc<19 and board[nr,nc]==opp:
            grp = _group(board, nr, nc, opp)
            if not _has_lib(board, grp):
                for gr,gc in grp:
                    board[gr,gc] = 0

# ── Pre-computar datos de la partida ───────────────────────────────────────────
def precompute(moves):
    board  = np.zeros((19,19), dtype=float)
    frames = []
    cum_counts = Counter()

    for idx, (player, col, row) in enumerate(moves):
        s0 = SPIN_MAP[player]
        new_bonds = []
        for dr,dc in DIRS:
            nr,nc = row+dr, col+dc
            if 0<=nr<19 and 0<=nc<19:
                s1 = board[nr,nc]
                new_bonds.append((s0, s1))
                cum_counts[(s0, s1)] += 1

        place(board, row, col, int(s0))

        frames.append({
            'idx'       : idx,
            'player'    : player,
            'col'       : col,
            'row'       : row,
            'board'     : board.copy(),
            'new_bonds' : new_bonds,
            'cum_counts': dict(cum_counts),
        })
    return frames

# ── Preparar malla continua para la variedad (fija) ───────────────────────────
_N = 350
_x = np.linspace(-1.45, 1.45, _N)
_y = np.linspace(-1.45, 1.45, _N)
_X, _Y = np.meshgrid(_x, _y)
_Z = H_M1(_X, _Y)

# ── Crear figura y artistas ────────────────────────────────────────────────────
def build_figure():
    fig = plt.figure(figsize=(12, 5.8), facecolor='#1C1C2E')

    # — Tablero —
    ax_b = fig.add_axes([0.02, 0.07, 0.43, 0.86])
    ax_b.set_facecolor('#C8A96E')
    ax_b.set_xlim(-0.7, 18.7); ax_b.set_ylim(-0.7, 18.7)
    ax_b.set_aspect('equal'); ax_b.axis('off')

    # Grid
    for i in range(19):
        ax_b.axhline(i, color='#4A2F00', lw=0.65, alpha=0.9, zorder=1)
        ax_b.axvline(i, color='#4A2F00', lw=0.65, alpha=0.9, zorder=1)
    # Star points
    for sc, sr in STAR_PTS:
        ax_b.plot(sc, sr, 'o', color='#4A2F00', ms=3.5, zorder=2)
    # Borde tablero
    rect = plt.Rectangle((-0.5,-0.5), 19, 19, fc='none',
                          ec='#4A2F00', lw=2, zorder=2)
    ax_b.add_patch(rect)

    # Scatter dinámico de piedras: negras y blancas por separado
    sc_B = ax_b.scatter([], [], s=200, c='#1A1A1A', zorder=5,
                        edgecolors='#333333', linewidths=0.8)
    sc_W = ax_b.scatter([], [], s=200, c='#F0F0F0', zorder=5,
                        edgecolors='#888888', linewidths=0.8)
    # Destello de la última piedra
    sc_last = ax_b.scatter([], [], s=320, c='#FFD700', zorder=7,
                            edgecolors='#FF8C00', linewidths=2, alpha=0.85)

    title_b = ax_b.set_title('', fontsize=10, color='#F0F0F0',
                              fontweight='bold', pad=6)

    # — Variedad —
    ax_v = fig.add_axes([0.50, 0.09, 0.47, 0.83])
    ax_v.set_facecolor('#1C1C2E')

    # Fondo continuo de H_M1
    ax_v.contourf(_X, _Y, _Z, levels=35, cmap='RdBu_r', alpha=0.40,
                  vmin=-2.2, vmax=2.2)

    # Curvas fantasma (no físicas)
    ax_v.contour(_X, _Y, _Z, levels=[-2.,0.,2.],
                 colors=['#666666'], linewidths=0.7, linestyles='--', alpha=0.5)

    # Curvas activas V±1
    cs_neg = ax_v.contour(_X, _Y, _Z, levels=[-1.],
                          colors=['#5DADE2'], linewidths=2.2, alpha=0.9)
    cs_pos = ax_v.contour(_X, _Y, _Z, levels=[ 1.],
                          colors=['#EC7063'], linewidths=2.2, alpha=0.9)
    ax_v.clabel(cs_neg, fmt={-1.: '$V_{-1}$'}, fontsize=10, colors='#5DADE2')
    ax_v.clabel(cs_pos, fmt={ 1.: '$V_{+1}$'}, fontsize=10, colors='#EC7063')

    # Ejes
    ax_v.set_xlim(-1.45, 1.45); ax_v.set_ylim(-1.45, 1.45)
    ax_v.set_xticks([-1,0,1]); ax_v.set_xticklabels(['B','∅','W'],
                                                       color='#DDDDDD', fontsize=9)
    ax_v.set_yticks([-1,0,1]); ax_v.set_yticklabels(['B','∅','W'],
                                                       color='#DDDDDD', fontsize=9)
    ax_v.set_xlabel('$s_0$ (piedra colocada)', color='#AAAAAA', fontsize=9)
    ax_v.set_ylabel('$s_1$ (vecino)', color='#AAAAAA', fontsize=9)
    ax_v.tick_params(colors='#AAAAAA')
    for sp in ax_v.spines.values():
        sp.set_color('#444444')
    ax_v.axhline(0, color='#555555', lw=0.5, ls=':')
    ax_v.axvline(0, color='#555555', lw=0.5, ls=':')

    # Scatter acumulativo de los 6 pares (tamaño = √conteo acumulado)
    pair_x = np.array([p[0] for p in VALID_P], dtype=float)
    pair_y = np.array([p[1] for p in VALID_P], dtype=float)
    pair_c = [PAIR_COLOR[p] for p in VALID_P]
    sc_cum = ax_v.scatter(pair_x, pair_y, s=np.zeros(6),
                          c=pair_c, zorder=7,
                          edgecolors='white', linewidths=0.9, alpha=0.85)

    # Etiquetas fijas de pares
    for p in VALID_P:
        ax_v.text(p[0]+0.06, p[1]+0.09, PAIR_LABEL[p],
                  fontsize=7, color='#CCCCCC', zorder=8, alpha=0.7)

    # Destello de nuevos enlaces (trail de TRAIL_LEN frames)
    trail_scatters = []
    for t in range(TRAIL_LEN):
        alpha = 1.0 - t / TRAIL_LEN
        size  = max(30, 420 - t * 60)
        sc_t  = ax_v.scatter([], [], s=size, c='#FFD700', zorder=10+t,
                              edgecolors='white', linewidths=1.2, alpha=alpha)
        trail_scatters.append(sc_t)

    title_v = ax_v.set_title('Variedad cúbica activa $H_{M1} = c$',
                              fontsize=10, color='#DDDDDD', pad=5)

    # Barra de progreso (texto)
    prog_txt = fig.text(0.50, 0.01, '', ha='center', va='bottom',
                        fontsize=8.5, color='#AAAAAA')

    # Subtítulo global
    fig.text(0.50, 0.98,
             '$H_{M1}(x,y) = x + 2y - xy^2 - x^2y$   '
             '|   Partida profesional de Go',
             ha='center', va='top', fontsize=10, color='#DDDDDD')

    artists = dict(sc_B=sc_B, sc_W=sc_W, sc_last=sc_last,
                   sc_cum=sc_cum, trail=trail_scatters,
                   title_b=title_b, title_v=title_v, prog_txt=prog_txt)
    return fig, ax_b, ax_v, artists


# ── Función de actualización de cada frame ─────────────────────────────────────
def make_update(frames, artists, game_name):
    def update(fi):
        if fi >= len(frames):
            fi = len(frames) - 1
        fd = frames[fi]

        board  = fd['board']
        player = fd['player']
        col    = fd['col']
        row    = fd['row']
        new_b  = fd['new_bonds']
        cum    = fd['cum_counts']

        # — Tablero —
        b_pos = np.argwhere(board == -1)   # negro
        w_pos = np.argwhere(board ==  1)   # blanco

        if len(b_pos):
            artists['sc_B'].set_offsets(b_pos[:, [1,0]])  # col, row
        else:
            artists['sc_B'].set_offsets(np.empty((0,2)))

        if len(w_pos):
            artists['sc_W'].set_offsets(w_pos[:, [1,0]])
        else:
            artists['sc_W'].set_offsets(np.empty((0,2)))

        # Destello en la última piedra
        artists['sc_last'].set_offsets([[col, row]])
        color_last = '#FFD700' if player == 'B' else '#FFEEAA'
        artists['sc_last'].set_facecolor(color_last)

        move_label = 'Negras' if player == 'B' else 'Blancas'
        col_ltr = chr(ord('A') + col + (1 if col >= 8 else 0))  # skip 'I'
        artists['title_b'].set_text(
            f'Jugada {fd["idx"]+1}  ·  {move_label}  {col_ltr}{19-row}'
        )

        # — Variedad: tamaños acumulados —
        max_c = max(cum.values()) if cum else 1
        sizes = np.array([np.sqrt(cum.get(p, 0) / max_c) * 380
                          for p in VALID_P])
        artists['sc_cum'].set_sizes(sizes)

        # — Trail de nuevos enlaces —
        # Sólo filtramos pares válidos (s0 siempre ≠0, s1 puede ser 0)
        valid_new = [(s0,s1) for s0,s1 in new_b if s0 != 0]

        # Rotate trail: frame 0 = más reciente
        for t in range(TRAIL_LEN-1, 0, -1):
            # Copiar posiciones del trail anterior
            prev = artists['trail'][t-1].get_offsets()
            if hasattr(prev, '__len__') and len(prev):
                artists['trail'][t].set_offsets(prev)
            else:
                artists['trail'][t].set_offsets(np.empty((0,2)))

        # Frame 0 del trail = nuevos enlaces de esta jugada
        if valid_new:
            trail_pts = np.array([[s0, s1] for s0,s1 in valid_new])
            artists['trail'][0].set_offsets(trail_pts)
            # Color según si son V+1 o V-1
            trail_colors = ['#FFD700' if H_M1(s0,s1) > 0 else '#87CEEB'
                            for s0,s1 in valid_new]
            artists['trail'][0].set_facecolor(trail_colors)
        else:
            artists['trail'][0].set_offsets(np.empty((0,2)))

        # — Progreso —
        pct = (fd['idx']+1) / len(frames) * 100
        bar_filled = int(pct / 2)  # 50 chars = 100%
        bar = '█' * bar_filled + '░' * (50 - bar_filled)
        artists['prog_txt'].set_text(
            f'[{bar}]  jugada {fd["idx"]+1}/{len(frames)}   '
            f'enlaces acumulados: {sum(cum.values())}'
        )

        # Tipo de retorno vacío (FuncAnimation no necesita lista)
        return []

    return update


# ── Main ───────────────────────────────────────────────────────────────────────
def main():
    files = sorted(Path(DATA).glob('*.sgf'))
    if not files:
        print(f'No se encontraron SGF en {DATA}'); return

    # Seleccionar partida
    arg = sys.argv[1] if len(sys.argv) > 1 else None
    if arg is None:
        sgf_path = files[0]
    elif arg.isdigit():
        sgf_path = files[int(arg) % len(files)]
    else:
        matches = [f for f in files if arg in f.name]
        sgf_path = matches[0] if matches else files[0]

    game_name = sgf_path.stem
    print(f'Partida: {game_name}')

    moves = parse_sgf(sgf_path)
    if not moves:
        print('No se encontraron jugadas.'); return
    print(f'Total jugadas: {len(moves)}')

    print('Pre-computando...')
    frames = precompute(moves)

    print('Construyendo figura...')
    fig, ax_b, ax_v, artists = build_figure()

    update_fn = make_update(frames, artists, game_name)

    # Agregar frames extra al final para "pausar" en el resultado final
    n_frames = len(frames) + 12

    print(f'Animando {n_frames} frames...')
    ani = animation.FuncAnimation(
        fig, update_fn,
        frames=n_frames,
        interval=280,    # ms por frame ≈ 3.6 fps
        blit=False,
        repeat=True,
        repeat_delay=2000,
    )

    out_path = os.path.join(RES, f'variety_game_{game_name[:40]}.gif')
    print(f'Guardando GIF: {out_path}')
    ani.save(out_path,
             writer=animation.PillowWriter(fps=4),
             dpi=110)
    plt.close(fig)
    print(f'  Listo  ({os.path.getsize(out_path)//1024} KB)')


if __name__ == '__main__':
    main()
