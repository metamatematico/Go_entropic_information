"""
animation_game.py
=================
Genera un GIF animado de una partida de Go mostrando:
  - Tablero con piedras apareciendo jugada a jugada
  - Mapa de energia de Ising clasico superpuesto (se actualiza en vivo)
  - Monitor de Temperatura efectiva T_eff (grafica corriendo)
  - Monitor de Entropia de Shannon S   (grafica corriendo)

Uso:
    python animation_game.py                          # primera partida disponible
    python animation_game.py data/sgf_partidas/X.sgf  # partida especifica
    python animation_game.py --step 2 --fps 6 --m 2   # opciones
    python animation_game.py --max_frames 120          # limitar duracion

Salida:
    results/<nombre_partida>_M<n>.gif
"""

import sys
from pathlib import Path
import os
import glob
import argparse
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.gridspec as gridspec
from matplotlib.patches import Circle, FancyArrowPatch
from matplotlib.lines import Line2D
from matplotlib.animation import FuncAnimation, PillowWriter

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from src.go_game_engine import GoBoard, SGFParser, _sgf_to_coords
from src.go_entropy import GoEntropyAnalyzer

RESULTS_DIR = os.path.join(str(Path(__file__).resolve().parents[2]), 'results')
os.makedirs(RESULTS_DIR, exist_ok=True)

# ─── Paleta dark-mode ────────────────────────────────────────────────────────
BG       = '#0F1117'   # fondo general
PANEL_BG = '#1A1D2E'   # fondo de paneles
BOARD_BG = '#C8A96E'   # madera del tablero
GRID_C   = '#7A5C2E'   # lineas de cuadricula
TEXT_C   = '#E2E8F0'   # texto general
ACCENT_B = '#60A5FA'   # azul para S
ACCENT_O = '#FB923C'   # naranja para T
ACCENT_R = '#F87171'   # rojo para ultima jugada
# ─────────────────────────────────────────────────────────────────────────────


def find_sgf(path=None):
    if path and os.path.isfile(path):
        return path
    for pattern in [
        os.path.join(str(Path(__file__).resolve().parents[2]), 'data', 'sgf_partidas', '*.sgf'),
        os.path.join(str(Path(__file__).resolve().parents[2]), 'data', 'sgf partidas',  '*.sgf'),
    ]:
        files = sorted(glob.glob(pattern))
        if files:
            return files[0]
    raise FileNotFoundError("No se encontraron SGFs en data/sgf_partidas/")


# ============================================================================
# PRE-COMPUTO DE FRAMES
# ============================================================================

def precompute_frames(moves, board_size, analyzer, step=1, max_frames=None):
    """
    Reproduce la partida entera y captura el estado del tablero,
    mapa de energia y metricas cada 'step' jugadas.
    """
    print(f"  Pre-computando {len(moves)} jugadas (step={step})...")
    board = GoBoard(size=board_size)
    frames = []

    def capture(move_num, last_pos, last_color):
        board_np = board.to_numpy()
        r = analyzer.analyze(board_np)
        T = r['T_eff']
        frames.append({
            'move':       move_num,
            'board':      board_np.copy(),
            'emap':       r['energy_map'].copy(),
            'S':          r['S_shannon'],
            'T':          T,
            'T_plot':     min(T, 30.0) if np.isfinite(T) else 30.0,
            'T_inf':      not np.isfinite(T),
            'E_total':    r['total_energy'],
            'dE':         r['total_energy'] - (frames[-1]['E_total'] if frames else 0.0),
            'last_pos':   last_pos,
            'last_color': last_color,
            'n_B':        int(np.sum(board_np == 'B')),
            'n_W':        int(np.sum(board_np == 'W')),
        })

    capture(0, None, None)   # tablero vacio

    actual = 0
    for i, move in enumerate(moves):
        color  = move.get('color', '')
        coords = move.get('coords', '')
        if not coords or move.get('pass', False):
            continue
        pos = _sgf_to_coords(coords)
        if pos is None:
            continue
        ok, _ = board.place_stone(color, pos)
        if not ok:
            continue
        actual += 1

        is_last = (i == len(moves) - 1)
        if actual % step == 0 or is_last:
            capture(actual, pos, color)
            if actual % 20 == 0:
                print(f"    jugada {actual}/{len(moves)}  "
                      f"S={frames[-1]['S']:.3f}  dE={frames[-1]['dE']:+.2f}")
            if max_frames and len(frames) >= max_frames:
                print(f"    Limite de {max_frames} frames alcanzado.")
                break

    print(f"  Total frames: {len(frames)}")
    return frames


# ============================================================================
# DIBUJO DE UN FRAME
# ============================================================================

def draw_board_frame(ax, frame, size):
    """Dibuja tablero + mapa de energia en el axes dado."""
    ax.cla()
    ax.set_facecolor(BOARD_BG)
    ax.set_xlim(-0.5, size - 0.5)
    ax.set_ylim(size - 0.5, -0.5)
    ax.set_aspect('equal')
    ax.set_xticks([])
    ax.set_yticks([])
    for spine in ax.spines.values():
        spine.set_color('#5A3A1A')
        spine.set_linewidth(1.5)

    # Cuadricula
    for i in range(size):
        ax.plot([0, size-1], [i, i], '-', color=GRID_C, lw=0.7, zorder=1)
        ax.plot([i, i], [0, size-1], '-', color=GRID_C, lw=0.7, zorder=1)

    # Hoshi
    hoshi = []
    if size == 19:
        hoshi = [(3,3),(3,9),(3,15),(9,3),(9,9),(9,15),(15,3),(15,9),(15,15)]
    elif size == 13:
        hoshi = [(3,3),(3,9),(6,6),(9,3),(9,9)]
    elif size == 9:
        hoshi = [(2,2),(2,6),(4,4),(6,2),(6,6)]
    for hr, hc in hoshi:
        ax.plot(hc, hr, 'o', color='#5A3A1A', markersize=4, zorder=2)

    # Mapa de energia (overlay)
    emap = frame['emap']
    vmax = float(np.percentile(np.abs(emap), 98)) or 1.0
    ax.imshow(emap, cmap='RdBu_r', vmin=-vmax, vmax=vmax,
              origin='upper', alpha=0.50, zorder=2,
              extent=(-0.5, size-0.5, size-0.5, -0.5))

    # Piedras
    board = frame['board']
    for r in range(size):
        for c in range(size):
            s = board[r, c]
            if s == 'B':
                ax.add_patch(Circle((c, r), 0.46,
                                    fc='#111111', ec='#333333', lw=0.8, zorder=3))
            elif s == 'W':
                ax.add_patch(Circle((c, r), 0.46,
                                    fc='#F0EDE8', ec='#888888', lw=1.0, zorder=3))

    # Ultima jugada
    if frame['last_pos']:
        lr, lc = frame['last_pos']
        color_dot = '#F87171' if frame['last_color'] == 'B' else '#FBBF24'
        ax.add_patch(Circle((lc, lr), 0.16,
                             fc=color_dot, ec='none', zorder=4))


def draw_monitor(ax, history_x, history_y, current_y,
                 label, color, y_label, y_lim,
                 total_moves, has_inf=False, zero_line=False,
                 zero_labels=None, two_tone=False,
                 pos_color=None, neg_color=None):
    """Dibuja un panel de monitoreo con la grafica corriendo."""
    ax.cla()
    ax.set_facecolor(PANEL_BG)
    ax.tick_params(colors=TEXT_C, labelsize=7)
    for spine in ax.spines.values():
        spine.set_color('#2D3250')
    ax.xaxis.label.set_color(TEXT_C)
    ax.yaxis.label.set_color(TEXT_C)

    if len(history_x) > 1:
        if two_tone:
            x = np.array(history_x, dtype=float)
            y = np.array(history_y, dtype=float)
            pc = pos_color or color
            nc = neg_color or color
            ax.plot(x, y, color='#9CA3AF', lw=0.7, alpha=0.55, zorder=3)
            ax.fill_between(x, y, 0, where=(y >= 0), color=pc, alpha=0.55,
                            zorder=2, interpolate=True)
            ax.fill_between(x, y, 0, where=(y <= 0), color=nc, alpha=0.55,
                            zorder=2, interpolate=True)
        else:
            ax.plot(history_x, history_y, color=color, lw=1.4, zorder=3)
            ax.fill_between(history_x, history_y, alpha=0.15, color=color, zorder=2)

    if history_x:
        marker_color = color
        if two_tone:
            marker_color = (pos_color or color) if history_y[-1] >= 0 else (neg_color or color)
        ax.plot(history_x[-1], history_y[-1], 'o',
                color=marker_color, markersize=5, zorder=4)
        val_str = '∞' if has_inf and history_y[-1] >= y_lim[1] * 0.97 else f'{history_y[-1]:+.3f}'
        ax.text(0.97, 0.88, val_str,
                transform=ax.transAxes,
                ha='right', va='top',
                fontsize=13, fontweight='bold', color=marker_color)

    ax.set_xlim(0, max(total_moves, 1))
    ax.set_ylim(*y_lim)
    ax.set_ylabel(y_label, color=TEXT_C, fontsize=8)
    ax.set_title(label, color=color, fontsize=9, fontweight='bold', pad=3)
    ax.grid(True, alpha=0.15, color='#4A5080')

    if has_inf:
        ax.axhline(y_lim[1] * 0.97, color='#EF4444', lw=0.8,
                   ls='--', alpha=0.6, zorder=1)
        ax.text(total_moves * 0.02, y_lim[1] * 0.98, '∞',
                color='#EF4444', fontsize=8, va='top')

    if zero_line:
        ax.axhline(0, color='#94A3B8', lw=0.9, ls='-', alpha=0.6, zorder=1)
        if zero_labels:
            top_label, bottom_label = zero_labels
            ax.text(total_moves * 0.02, y_lim[1] * 0.95, top_label,
                    color='#F0EDE8', fontsize=6.5, va='top', alpha=0.8)
            ax.text(total_moves * 0.02, y_lim[0] * 0.95, bottom_label,
                    color='#9CA3AF', fontsize=6.5, va='bottom', alpha=0.8)


# ============================================================================
# CREAR ANIMACION
# ============================================================================

def create_animation(frames, game_info, M, fps, output_path):
    """Genera el GIF animado."""
    total_moves = max(f['move'] for f in frames)
    board_size  = frames[0]['board'].shape[0]

    # Rangos fijos para los monitores (calculados del total)
    all_S  = [f['S'] for f in frames]
    all_dE = [f['dE'] for f in frames[1:]]   # excluye frame 0 (tablero vacio, dE=0)
    S_lim = (max(0, min(all_S) - 0.1), max(all_S) + 0.2)
    dE_bound = max(abs(min(all_dE, default=1.0)), abs(max(all_dE, default=1.0)), 1.0) * 1.15
    dE_lim = (-dE_bound, dE_bound)

    # Figura con fondo oscuro
    fig = plt.figure(figsize=(16, 8), facecolor=BG)

    gs = gridspec.GridSpec(
        3, 2,
        left=0.02, right=0.98,
        top=0.91, bottom=0.08,
        wspace=0.28, hspace=0.45,
        width_ratios=[1.65, 1],
        height_ratios=[1, 1, 0.08],
    )

    ax_board  = fig.add_subplot(gs[:2, 0])
    ax_E      = fig.add_subplot(gs[0, 1])
    ax_S      = fig.add_subplot(gs[1, 1])
    ax_prog   = fig.add_subplot(gs[2, :])

    # Cabecera
    title_str = (f"{game_info.black_player} (●)  vs  "
                 f"{game_info.white_player} (○)   —   {game_info.date}")
    fig.text(0.5, 0.96, title_str,
             ha='center', va='top', fontsize=11,
             fontweight='bold', color=TEXT_C)
    fig.text(0.5, 0.925,
             f'Ising Clásico Manhattan-{M}  |  ΔE = impacto energético de la última jugada  |  '
             f'S = −Σ pᵢ ln pᵢ  (entropía de Shannon)',
             ha='center', va='top', fontsize=8, color='#94A3B8', style='italic')

    # Historial acumulado para las graficas
    hist_moves = []
    hist_S     = []
    hist_dE    = []

    def update(fi):
        frame = frames[fi]

        # ── Tablero ──────────────────────────────────────────────────
        draw_board_frame(ax_board, frame, board_size)
        move_n = frame['move']
        ax_board.set_title(
            f"Jugada {move_n} / {total_moves}   "
            f"●={frame['n_B']}  ○={frame['n_W']}",
            color=TEXT_C, fontsize=10, fontweight='bold', pad=5
        )

        # ── Actualizar historial ──────────────────────────────────────
        hist_moves.append(move_n)
        hist_S.append(frame['S'])
        hist_dE.append(frame['dE'])

        # ── Monitor dE (impacto energetico de la ultima jugada) ─────────
        draw_monitor(
            ax_E, hist_moves, hist_dE, frame['dE'],
            label='Impacto de la Última Jugada  ΔE',
            color=ACCENT_O,
            y_label='ΔE (u.a.)',
            y_lim=dE_lim,
            total_moves=total_moves,
            zero_line=True,
            zero_labels=('empuje hacia ○', 'empuje hacia ●'),
            two_tone=True,
            pos_color='#FBBF24',
            neg_color='#60A5FA',
        )

        # ── Monitor S ────────────────────────────────────────────────
        draw_monitor(
            ax_S, hist_moves, hist_S, frame['S'],
            label='Entropía de Shannon  S',
            color=ACCENT_B,
            y_label='S (nats)',
            y_lim=S_lim,
            total_moves=total_moves,
        )
        ax_S.set_xlabel('Jugada', color=TEXT_C, fontsize=8)

        # ── Barra de progreso ─────────────────────────────────────────
        ax_prog.cla()
        ax_prog.set_facecolor('#1E2235')
        ax_prog.set_xlim(0, total_moves)
        ax_prog.set_ylim(0, 1)
        ax_prog.set_yticks([])
        ax_prog.set_xlabel('Progreso de la partida', color='#64748B', fontsize=7)
        for spine in ax_prog.spines.values():
            spine.set_color('#2D3250')
        progress = move_n / max(total_moves, 1)
        ax_prog.barh(0.5, move_n, height=0.6,
                     color='#3B82F6', alpha=0.7, left=0)
        ax_prog.axvline(move_n, color='#93C5FD', lw=1.5, zorder=3)
        # Fajas de apertura / medio / final
        for label, xstart, xend in [
            ('Apertura',  0,              total_moves * 0.25),
            ('Fuseki',    total_moves*0.1, total_moves * 0.35),
            ('Medio juego', total_moves*0.35, total_moves*0.70),
            ('Final',     total_moves*0.70, total_moves),
        ]:
            mid = (xstart + xend) / 2
            ax_prog.text(mid, 0.05, label, ha='center', va='bottom',
                         fontsize=6, color='#64748B', alpha=0.7)

        return []

    print(f"  Renderizando {len(frames)} frames a {fps} fps...")
    anim = FuncAnimation(fig, update, frames=len(frames),
                         interval=1000 // fps, blit=False, repeat=False)

    writer = PillowWriter(fps=fps, metadata={'loop': 0})
    anim.save(output_path, writer=writer, dpi=100,
              savefig_kwargs={'facecolor': BG})
    plt.close(fig)

    size_mb = os.path.getsize(output_path) / 1024 / 1024
    print(f"  GIF guardado: {output_path}  ({size_mb:.1f} MB)")


# ============================================================================
# MAIN
# ============================================================================

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('sgf', nargs='?', default=None)
    parser.add_argument('--step',       type=int, default=1,
                        help='Capturar metricas cada N jugadas (default 1)')
    parser.add_argument('--fps',        type=int, default=5,
                        help='Frames por segundo del GIF (default 5)')
    parser.add_argument('--m',          type=int, default=1, choices=[1, 2],
                        help='Kernel Manhattan (default 1)')
    parser.add_argument('--max_frames', type=int, default=None,
                        help='Limitar numero de frames (default: sin limite)')
    args = parser.parse_args()

    sgf_path = find_sgf(args.sgf)
    moves, game_info = SGFParser.parse_file(sgf_path)
    total = len(moves)

    print(f"\n{'='*60}")
    print(f"  ANIMACION: {os.path.basename(sgf_path)}")
    print(f"  {game_info.black_player} vs {game_info.white_player}")
    print(f"  Jugadas: {total}  |  Tablero: {game_info.board_size}x{game_info.board_size}")
    print(f"  Kernel: Manhattan-{args.m}  |  Step: {args.step}  |  FPS: {args.fps}")
    print(f"{'='*60}")

    analyzer = GoEntropyAnalyzer(manhattan_distance=args.m)
    frames   = precompute_frames(moves, game_info.board_size,
                                 analyzer, step=args.step,
                                 max_frames=args.max_frames)

    base     = os.path.splitext(os.path.basename(sgf_path))[0]
    out_path = os.path.join(RESULTS_DIR, f'{base}_M{args.m}.gif')
    create_animation(frames, game_info, args.m, args.fps, out_path)

    print(f"\nListo: {out_path}")


if __name__ == '__main__':
    main()
