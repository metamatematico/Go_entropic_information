"""
analysis_game.py
================
Analiza la evolucion de entropia y temperatura en una partida
real de Go cargada desde un archivo SGF.

Toma snapshots del tablero en distintos momentos (jugadas) y
calcula para cada uno: T_eff, S_shannon, S_boltzmann.

Uso:
    python analysis_game.py                           # usa la primera partida disponible
    python analysis_game.py data/sgf_partidas/X.sgf  # partida especifica
    python analysis_game.py --step 5                  # snapshot cada 5 jugadas (default: 10)

Salidas (results/):
    entropy_over_time.png  — T_eff y S a lo largo de la partida
    board_snapshots.png    — tableros en momentos clave
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

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from src.go_game_engine import GoBoard, SGFParser
from src.go_entropy import GoEntropyAnalyzer
from src.go_visualization import plot_board, plot_energy_map

RESULTS_DIR = os.path.join(str(Path(__file__).resolve().parents[2]), 'results')
os.makedirs(RESULTS_DIR, exist_ok=True)


def find_sgf(path: str = None) -> str:
    """Busca el archivo SGF a usar."""
    if path and os.path.isfile(path):
        return path
    patterns = [
        os.path.join(str(Path(__file__).resolve().parents[2]), 'data', 'sgf_partidas', '*.sgf'),
        os.path.join(str(Path(__file__).resolve().parents[2]), 'data', 'sgf partidas', '*.sgf'),
    ]
    for p in patterns:
        files = sorted(glob.glob(p))
        if files:
            return files[0]
    raise FileNotFoundError("No se encontraron archivos SGF. "
                            "Coloca partidas en data/sgf_partidas/")


def replay_to_move(moves: list, board_size: int, n: int) -> np.ndarray:
    """Reproduce los primeros n movimientos y devuelve el tablero como numpy."""
    board = GoBoard(size=board_size)
    board.replay_moves(moves[:n])
    return board.to_numpy()


def analyze_game(sgf_path: str, step: int = 10,
                 manhattan_distance: int = 2) -> dict:
    """
    Analiza la evolucion de entropia a lo largo de una partida.

    Args:
        sgf_path:           Ruta al archivo SGF
        step:               Intervalo entre snapshots (en jugadas)
        manhattan_distance: Radio del kernel Ising (1 o 2)

    Returns:
        dict con move_numbers, boards, energy_maps, metricas
    """
    moves, game_info = SGFParser.parse_file(sgf_path)
    total_moves = len(moves)
    board_size = game_info.board_size

    print(f"\nPartida: {os.path.basename(sgf_path)}")
    print(f"  {game_info.black_player} (N) vs {game_info.white_player} (B)")
    print(f"  Fecha: {game_info.date}  |  Resultado: {game_info.result}")
    print(f"  Movimientos totales: {total_moves}  |  Tablero: {board_size}x{board_size}")

    analyzer = GoEntropyAnalyzer(manhattan_distance=manhattan_distance)

    # Snapshots en jugadas 0, step, 2*step, ... total_moves
    move_numbers = list(range(0, total_moves + 1, step))
    if move_numbers[-1] != total_moves:
        move_numbers.append(total_moves)

    boards, emaps, metrics = [], [], []

    for n in move_numbers:
        board_np = replay_to_move(moves, board_size, n)
        result = analyzer.analyze(board_np, T=1.0)
        boards.append(board_np)
        emaps.append(result['energy_map'])
        metrics.append({
            'move': n,
            'T_eff': result['T_eff'],
            'S_shannon': result['S_shannon'],
            'S_boltzmann': result['S_boltzmann'],
            'total_energy': result['total_energy'],
            'n_stones': result['stone_count']['B'] + result['stone_count']['W'],
        })
        print(f"  Jugada {n:>3}: S={result['S_shannon']:.3f}  "
              f"T={result['T_eff']:.3f}  "
              f"E_total={result['total_energy']:.2f}  "
              f"piedras={metrics[-1]['n_stones']}")

    return {
        'move_numbers': move_numbers,
        'boards': boards,
        'energy_maps': emaps,
        'metrics': metrics,
        'game_info': game_info,
        'sgf_path': sgf_path,
        'manhattan_distance': manhattan_distance,
    }


def plot_entropy_over_time(data: dict, output_path: str):
    """
    Grafico de la evolucion de T_eff, S_shannon y S_boltzmann
    a lo largo de la partida.
    """
    moves  = data['move_numbers']
    mets   = data['metrics']
    gi     = data['game_info']
    M      = data['manhattan_distance']

    t_eff  = [m['T_eff'] for m in mets]
    s_sh   = [m['S_shannon'] for m in mets]
    s_bo   = [m['S_boltzmann'] for m in mets]
    stones = [m['n_stones'] for m in mets]

    fig, axes = plt.subplots(3, 1, figsize=(11, 9), sharex=True)
    title = (f"Evolucion Energetica — {gi.black_player} vs {gi.white_player}  "
             f"({gi.date})  [Ising M{M}]")
    fig.suptitle(title, fontsize=11, fontweight='bold')

    # Entropia de Shannon
    axes[0].plot(moves, s_sh, 'b-o', markersize=4, linewidth=1.5, label='S Shannon')
    axes[0].fill_between(moves, s_sh, alpha=0.15, color='blue')
    axes[0].set_ylabel('S Shannon (nats)')
    axes[0].set_title('Entropia de Shannon  [caos de la distribucion de energia]')
    axes[0].legend(fontsize=9)
    axes[0].grid(True, alpha=0.3)

    # Temperatura efectiva
    t_cap = [min(v, 15.0) for v in t_eff]
    axes[1].plot(moves, t_cap, 'r-o', markersize=4, linewidth=1.5, label='T efectiva')
    axes[1].fill_between(moves, t_cap, alpha=0.15, color='red')
    axes[1].set_ylabel('T efectiva (u.a.)')
    axes[1].set_title('Temperatura Efectiva  [fluctuaciones de energia local]')
    axes[1].legend(fontsize=9)
    axes[1].grid(True, alpha=0.3)

    # Boltzmann + stones (eje secundario)
    ax3 = axes[2]
    ax3b = ax3.twinx()
    ax3.plot(moves, s_bo, 'g-o', markersize=4, linewidth=1.5, label='S Boltzmann (T=1)')
    ax3b.plot(moves, stones, 'k--', markersize=3, linewidth=1, alpha=0.5, label='N piedras')
    ax3.set_ylabel('S Boltzmann (nats)', color='g')
    ax3b.set_ylabel('N piedras', color='gray')
    ax3.set_xlabel('Jugada')
    ax3.set_title('Entropia de Boltzmann a T=1  +  cantidad de piedras')
    ax3.tick_params(axis='y', labelcolor='g')
    ax3b.tick_params(axis='y', labelcolor='gray')
    lines1, labels1 = ax3.get_legend_handles_labels()
    lines2, labels2 = ax3b.get_legend_handles_labels()
    ax3.legend(lines1 + lines2, labels1 + labels2, fontsize=9, loc='upper left')
    ax3.grid(True, alpha=0.3)

    plt.tight_layout()
    fig.savefig(output_path, dpi=150, bbox_inches='tight')
    print(f"Guardado: {output_path}")
    plt.close(fig)


def plot_board_snapshots(data: dict, n_snapshots: int = 6, output_path: str = None):
    """
    Grilla de tableros en momentos clave de la partida.
    Toma los n_snapshots igualmente espaciados.
    """
    all_moves  = data['move_numbers']
    all_boards = data['boards']
    all_emaps  = data['energy_maps']
    all_mets   = data['metrics']
    M          = data['manhattan_distance']

    # Seleccionar indices igualmente espaciados
    if len(all_moves) <= n_snapshots:
        indices = list(range(len(all_moves)))
    else:
        indices = [int(round(i * (len(all_moves) - 1) / (n_snapshots - 1)))
                   for i in range(n_snapshots)]

    selected = [(all_moves[i], all_boards[i], all_emaps[i], all_mets[i])
                for i in indices]

    cols = min(3, n_snapshots)
    rows = int(np.ceil(n_snapshots / cols))
    fig, axes = plt.subplots(rows, cols, figsize=(cols * 4, rows * 4))
    axes = np.array(axes).flatten()

    for k, (move, board, emap, met) in enumerate(selected):
        ax = axes[k]
        vmax = max(abs(emap.min()), abs(emap.max())) or 1.0
        ax.set_facecolor('#DEB887')
        size = board.shape[0]
        ax.set_xlim(-0.5, size - 0.5)
        ax.set_ylim(-0.5, size - 0.5)
        ax.set_aspect('equal')
        ax.invert_yaxis()
        for i in range(size):
            ax.plot([0, size-1], [i, i], 'k-', lw=0.4, zorder=1)
            ax.plot([i, i], [0, size-1], 'k-', lw=0.4, zorder=1)
        ax.imshow(emap, cmap='RdBu_r', vmin=-vmax, vmax=vmax,
                  origin='upper', alpha=0.5, zorder=2,
                  extent=(-0.5, size-0.5, size-0.5, -0.5))
        from matplotlib.patches import Circle
        for r in range(size):
            for c in range(size):
                s = board[r, c]
                if s == 'B':
                    ax.add_patch(Circle((c, r), 0.45, fc='#111', ec='k', lw=0.7, zorder=3))
                elif s == 'W':
                    ax.add_patch(Circle((c, r), 0.45, fc='white', ec='#333', lw=1, zorder=3))
        ax.set_title(f"Jug. {move}\nS={met['S_shannon']:.2f}  T={met['T_eff']:.2f}",
                     fontsize=9, pad=3)
        ax.set_xticks([])
        ax.set_yticks([])

    for j in range(len(selected), len(axes)):
        axes[j].set_visible(False)

    plt.suptitle(f"Snapshots de la Partida (Mapa Energia Ising M{M})",
                 fontsize=11, fontweight='bold')
    plt.tight_layout()
    if output_path:
        fig.savefig(output_path, dpi=150, bbox_inches='tight')
        print(f"Guardado: {output_path}")
    plt.close(fig)


# ============================================================================
# MAIN
# ============================================================================

def main():
    parser = argparse.ArgumentParser(description='Analisis Ising de una partida SGF')
    parser.add_argument('sgf', nargs='?', default=None, help='Ruta al archivo SGF')
    parser.add_argument('--step', type=int, default=10, help='Snapshot cada N jugadas')
    parser.add_argument('--manhattan', type=int, default=2, choices=[1, 2],
                        help='Radio del kernel Ising (1 o 2)')
    args = parser.parse_args()

    try:
        sgf_path = find_sgf(args.sgf)
    except FileNotFoundError as e:
        print(f"Error: {e}")
        sys.exit(1)

    print("\n" + "="*62)
    print("  ANALISIS ISING + ENTROPIA — PARTIDA DE GO")
    print("="*62)

    data = analyze_game(sgf_path, step=args.step, manhattan_distance=args.manhattan)

    base = os.path.splitext(os.path.basename(sgf_path))[0]
    M = args.manhattan

    # Evolucion temporal
    time_path = os.path.join(RESULTS_DIR, f'{base}_entropy_M{M}.png')
    plot_entropy_over_time(data, time_path)

    # Snapshots
    snap_path = os.path.join(RESULTS_DIR, f'{base}_snapshots_M{M}.png')
    plot_board_snapshots(data, n_snapshots=6, output_path=snap_path)

    print(f"\nListo. Resultados en: {RESULTS_DIR}")


if __name__ == '__main__':
    main()
