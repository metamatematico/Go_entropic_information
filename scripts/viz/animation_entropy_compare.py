"""
animation_entropy_compare.py
=============================
GIF con cuatro métricas de entropía en tiempo real para ambos modelos:

  Panel izquierdo  — Tablero de Go + overlay de energía M1
  Derecha 1        — S_Shannon ponderada por |E|              ↑ crece con piedras
  Derecha 2        — S_B = ln W  (Boltzmann termodinámica)    ↑ extensiva, crece con N
  Derecha 3        — S_Gibbs a T_eff  (distribución canónica) → satura en ln(N)
  Derecha 4        — T_eff = σ²(E)/|⟨E⟩|
  Barra inferior   — Progreso de la partida

Uso:
    python animation_entropy_compare.py
    python animation_entropy_compare.py data/sgf_partidas/X.sgf
    python animation_entropy_compare.py --step 2 --fps 6 --max_frames 150

Salida: results/<nombre>_entropy_compare.gif
"""

import sys, os, glob, argparse
from pathlib import Path
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.gridspec as gridspec
from matplotlib.patches import Circle
from matplotlib.animation import FuncAnimation, PillowWriter

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from src.go_game_engine import GoBoard, SGFParser, _sgf_to_coords
from src.go_entropy      import GoEntropyAnalyzer
from compare_per_bond    import (
    all_bond_energies_nuestro, all_bond_energies_alvarado,
    bond_shannon_entropy, bond_boltzmann_entropy, bond_boltzmann_lnW, bond_T_eff,
)

RESULTS = os.path.join(str(Path(__file__).resolve().parents[2]), 'results')
os.makedirs(RESULTS, exist_ok=True)

# ── Paleta ────────────────────────────────────────────────────────────────────
BG       = '#0F1117'
PANEL_BG = '#1A1D2E'
BOARD_BG = '#C8A96E'
GRID_C   = '#7A5C2E'
TEXT_C   = '#E2E8F0'
C_M1     = '#60A5FA'   # azul  — S_Shannon M1
C_AL     = '#FB923C'   # naranja — S_Shannon Alvarado
C_BM1    = '#34D399'   # verde  — S_Boltzmann M1
C_BAL    = '#F472B6'   # rosa   — S_Boltzmann Alvarado
C_TM1    = '#A78BFA'   # violeta — T_eff M1
C_TAL    = '#FCD34D'   # amarillo — T_eff Alvarado
ACCENT_R = '#F87171'

ECOL_HIST = {-2.0:'#1848c4', -1.0:'#5ba4f5', 0.0:'#555',
             +1.0:'#f58b5b', +2.0:'#c41818'}

# ─────────────────────────────────────────────────────────────────────────────

def find_sgf(path=None):
    if path and os.path.isfile(path):
        return path
    files = sorted(glob.glob(
        os.path.join(str(Path(__file__).resolve().parents[2]), 'data', 'sgf_partidas', '*.sgf')))
    if files:
        return files[0]
    raise FileNotFoundError("No se encontraron SGFs en data/sgf_partidas/")


# ─────────────────────────────────────────────────────────────────────────────
# PRE-COMPUTO
# ─────────────────────────────────────────────────────────────────────────────

def precompute_frames(moves, board_size, analyzer, step=1, max_frames=None):
    print(f"  Pre-computando {len(moves)} jugadas (step={step})...")
    board  = GoBoard(size=board_size)
    frames = []

    def capture(move_num, last_pos, last_color):
        bnp      = board.to_numpy()
        r_ising  = analyzer.analyze(bnp)

        bonds_M1 = all_bond_energies_nuestro(bnp)
        bonds_AL = all_bond_energies_alvarado(bnp)

        S_sh_M1  = bond_shannon_entropy(bonds_M1)
        S_sh_AL  = bond_shannon_entropy(bonds_AL)

        T_M1     = bond_T_eff(bonds_M1)
        T_AL     = bond_T_eff(bonds_AL)
        T_M1_p   = min(T_M1, 20.0) if np.isfinite(T_M1) else 20.0
        T_AL_p   = min(T_AL, 20.0) if np.isfinite(T_AL) else 20.0

        S_gi_M1  = bond_boltzmann_entropy(bonds_M1)   # S_Gibbs (canónica)
        S_gi_AL  = bond_boltzmann_entropy(bonds_AL)
        S_lnW_M1 = bond_boltzmann_lnW(bonds_M1)       # S_B = ln W (Boltzmann)
        S_lnW_AL = bond_boltzmann_lnW(bonds_AL)

        frames.append({
            'move':       move_num,
            'board':      bnp.copy(),
            'emap':       r_ising['energy_map'].copy(),
            'S_sh_M1':    S_sh_M1,
            'S_sh_AL':    S_sh_AL,
            'S_gi_M1':    S_gi_M1,
            'S_gi_AL':    S_gi_AL,
            'S_lnW_M1':   S_lnW_M1,
            'S_lnW_AL':   S_lnW_AL,
            'T_M1':       T_M1_p,
            'T_AL':       T_AL_p,
            'T_M1_inf':   not np.isfinite(T_M1),
            'T_AL_inf':   not np.isfinite(T_AL),
            'last_pos':   last_pos,
            'last_color': last_color,
            'n_B':        int(np.sum(bnp == 'B')),
            'n_W':        int(np.sum(bnp == 'W')),
        })

    capture(0, None, None)

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
            if actual % 40 == 0:
                f = frames[-1]
                print(f"    j{actual:3d}  "
                      f"S_sh=({f['S_sh_M1']:.2f},{f['S_sh_AL']:.2f})  "
                      f"lnW=({f['S_lnW_M1']:.1f},{f['S_lnW_AL']:.1f})  "
                      f"T=({f['T_M1']:.2f},{f['T_AL']:.2f})")
            if max_frames and len(frames) >= max_frames:
                print(f"    Limite {max_frames} frames alcanzado.")
                break

    print(f"  Total frames: {len(frames)}")
    return frames


# ─────────────────────────────────────────────────────────────────────────────
# HELPERS DE DIBUJO
# ─────────────────────────────────────────────────────────────────────────────

def panel_style(ax):
    ax.cla()
    ax.set_facecolor(PANEL_BG)
    ax.tick_params(colors=TEXT_C, labelsize=7)
    for sp in ax.spines.values():
        sp.set_color('#2D3250')


def draw_board(ax, frame, size):
    ax.cla()
    ax.set_facecolor(BOARD_BG)
    ax.set_xlim(-0.5, size-0.5); ax.set_ylim(size-0.5, -0.5)
    ax.set_aspect('equal'); ax.set_xticks([]); ax.set_yticks([])
    for sp in ax.spines.values():
        sp.set_color('#5A3A1A'); sp.set_linewidth(1.5)
    for i in range(size):
        ax.plot([0, size-1], [i, i], '-', color=GRID_C, lw=0.7, zorder=1)
        ax.plot([i, i], [0, size-1], '-', color=GRID_C, lw=0.7, zorder=1)
    hoshi = []
    if size == 19:
        hoshi = [(3,3),(3,9),(3,15),(9,3),(9,9),(9,15),(15,3),(15,9),(15,15)]
    elif size == 13:
        hoshi = [(3,3),(3,9),(6,6),(9,3),(9,9)]
    elif size == 9:
        hoshi = [(2,2),(2,6),(4,4),(6,2),(6,6)]
    for hr, hc in hoshi:
        ax.plot(hc, hr, 'o', color='#5A3A1A', markersize=4, zorder=2)
    emap = frame['emap']
    vmax = float(np.percentile(np.abs(emap), 98)) or 1.0
    ax.imshow(emap, cmap='RdBu_r', vmin=-vmax, vmax=vmax, origin='upper',
              alpha=0.48, zorder=2, extent=(-0.5, size-0.5, size-0.5, -0.5))
    for r in range(size):
        for c in range(size):
            s = frame['board'][r, c]
            if s == 'B':
                ax.add_patch(Circle((c,r), 0.46, fc='#111', ec='#333', lw=0.8, zorder=3))
            elif s == 'W':
                ax.add_patch(Circle((c,r), 0.46, fc='#F0EDE8', ec='#888', lw=1.0, zorder=3))
    if frame['last_pos']:
        lr, lc = frame['last_pos']
        dc = ACCENT_R if frame['last_color'] == 'B' else '#FBBF24'
        ax.add_patch(Circle((lc, lr), 0.16, fc=dc, ec='none', zorder=4))


def draw_running_curve(ax, hx, hy1, hy2, c1, c2, lbl1, lbl2, total, ylim,
                        title, show_inf=False, cur_T1_inf=False, cur_T2_inf=False):
    panel_style(ax)
    if len(hx) > 1:
        ax.plot(hx, hy1, color=c1, lw=1.8, label=lbl1, zorder=4)
        ax.fill_between(hx, hy1, alpha=0.10, color=c1, zorder=2)
        ax.plot(hx, hy2, color=c2, lw=1.8, label=lbl2, zorder=4, ls='--')
        ax.fill_between(hx, hy2, alpha=0.10, color=c2, zorder=2)
    if hx:
        ax.plot(hx[-1], hy1[-1], 'o', color=c1, ms=5, zorder=5)
        ax.plot(hx[-1], hy2[-1], 'o', color=c2, ms=5, zorder=5)
        v1 = '∞' if (show_inf and cur_T1_inf) else f'{hy1[-1]:.3f}'
        v2 = '∞' if (show_inf and cur_T2_inf) else f'{hy2[-1]:.3f}'
        ax.text(0.97, 0.93, f'{lbl1}: {v1}', transform=ax.transAxes,
                ha='right', va='top', fontsize=10, fontweight='bold', color=c1)
        ax.text(0.97, 0.76, f'{lbl2}: {v2}', transform=ax.transAxes,
                ha='right', va='top', fontsize=10, fontweight='bold', color=c2)
    ax.set_xlim(0, max(total, 1)); ax.set_ylim(*ylim)
    ax.set_title(title, color=TEXT_C, fontsize=8.5, fontweight='bold', pad=2)
    ax.set_ylabel('nats' if 'T' not in title else 'T_eff', color=TEXT_C, fontsize=7)
    ax.legend(fontsize=7.5, loc='upper left',
              facecolor=PANEL_BG, edgecolor='#4A5080', labelcolor=TEXT_C)
    ax.grid(True, alpha=0.12, color='#4A5080')
    if show_inf:
        ax.axhline(ylim[1]*0.97, color='#EF4444', lw=0.8, ls='--', alpha=0.5)
        ax.text(total*0.02, ylim[1]*0.98, '∞', color='#EF4444', fontsize=8, va='top')


def draw_bond_hist(ax, frame):
    panel_style(ax)
    d_M1 = frame['dist_M1']; d_AL = frame['dist_AL']
    all_v = sorted(set(list(d_M1.keys()) + list(d_AL.keys())))
    xl = [f'{int(v):+d}' if v != 0 else '0' for v in all_v]
    xi = np.arange(len(all_v)); w = 0.34
    vm1 = [d_M1.get(v, 0.) for v in all_v]
    val = [d_AL.get(v, 0.)  for v in all_v]
    bc  = [ECOL_HIST.get(float(v), '#888') for v in all_v]
    ax.bar(xi-w/2, vm1, w, color=bc, ec=C_M1, lw=1.2, alpha=0.82, label='M1', zorder=3)
    ax.bar(xi+w/2, val, w, color=bc, ec=C_AL, lw=1.2, alpha=0.65, label='AL',
           hatch='///', zorder=3)
    ax.set_xticks(xi); ax.set_xticklabels(xl, fontsize=9)
    ax.set_ylim(0, 1.0); ax.set_ylabel('Fracción', color=TEXT_C, fontsize=7)
    ax.set_title('Distribución de bonos', color=TEXT_C, fontsize=8.5,
                 fontweight='bold', pad=2)
    ax.legend(fontsize=7.5, loc='upper right',
              facecolor=PANEL_BG, edgecolor='#4A5080', labelcolor=TEXT_C)
    ax.grid(axis='y', alpha=0.12, color='#4A5080')


# ─────────────────────────────────────────────────────────────────────────────
# CREAR ANIMACION
# ─────────────────────────────────────────────────────────────────────────────

def create_animation(frames, game_info, fps, output_path):
    total_moves = max(f['move'] for f in frames)
    board_size  = frames[0]['board'].shape[0]

    all_S_sh_M1  = [f['S_sh_M1']  for f in frames]
    all_S_sh_AL  = [f['S_sh_AL']  for f in frames]
    all_S_gi_M1  = [f['S_gi_M1']  for f in frames]
    all_S_gi_AL  = [f['S_gi_AL']  for f in frames]
    all_S_lnW_M1 = [f['S_lnW_M1'] for f in frames]
    all_S_lnW_AL = [f['S_lnW_AL'] for f in frames]
    all_T_M1     = [f['T_M1']     for f in frames]
    all_T_AL     = [f['T_AL']     for f in frames]

    def ylim(lst, pad=0.1):
        lo, hi = min(lst), max(lst)
        rng = max(hi - lo, 0.05)
        return (max(0, lo - rng*pad), hi + rng*pad)

    lim_sh  = ylim(all_S_sh_M1  + all_S_sh_AL)
    lim_gi  = ylim(all_S_gi_M1  + all_S_gi_AL)
    lim_lnW = ylim(all_S_lnW_M1 + all_S_lnW_AL)
    lim_T   = (0, max(max(all_T_M1), max(all_T_AL)) * 1.08)

    fig = plt.figure(figsize=(18, 12), facecolor=BG)
    gs = gridspec.GridSpec(
        5, 2,
        left=0.02, right=0.98,
        top=0.91, bottom=0.05,
        wspace=0.24, hspace=0.50,
        width_ratios=[1.55, 1],
        height_ratios=[1.0, 1.0, 1.0, 1.0, 0.10],
    )

    ax_board = fig.add_subplot(gs[:4, 0])
    ax_sh    = fig.add_subplot(gs[0, 1])
    ax_lnW   = fig.add_subplot(gs[1, 1])
    ax_gi    = fig.add_subplot(gs[2, 1])
    ax_T     = fig.add_subplot(gs[3, 1])
    ax_prog  = fig.add_subplot(gs[4, :])

    fig.text(0.5, 0.966,
             f"{game_info.black_player} (●)  vs  "
             f"{game_info.white_player} (○)   —   {game_info.date}",
             ha='center', va='top', fontsize=11.5,
             fontweight='bold', color=TEXT_C)
    fig.text(0.5, 0.936,
             'S_Shannon · S_B=lnW (Boltzmann) · S_Gibbs · T_eff  —  M1 vs Alvarado Atomic-Go',
             ha='center', va='top', fontsize=8.5, color='#94A3B8', style='italic')

    hist_moves  = []
    h_sh_M1  = []; h_sh_AL  = []
    h_lnW_M1 = []; h_lnW_AL = []
    h_gi_M1  = []; h_gi_AL  = []
    h_T_M1   = []; h_T_AL   = []

    def update(fi):
        f = frames[fi]

        # ── Tablero ──────────────────────────────────────────────────
        draw_board(ax_board, f, board_size)
        ax_board.set_title(
            f"Jugada {f['move']} / {total_moves}   "
            f"●={f['n_B']}  ○={f['n_W']}",
            color=TEXT_C, fontsize=10, fontweight='bold', pad=5)

        hist_moves.append(f['move'])
        h_sh_M1.append(f['S_sh_M1']);   h_sh_AL.append(f['S_sh_AL'])
        h_lnW_M1.append(f['S_lnW_M1']); h_lnW_AL.append(f['S_lnW_AL'])
        h_gi_M1.append(f['S_gi_M1']);   h_gi_AL.append(f['S_gi_AL'])
        h_T_M1.append(f['T_M1']);       h_T_AL.append(f['T_AL'])

        # ── S Shannon ─────────────────────────────────────────────────
        draw_running_curve(ax_sh, hist_moves, h_sh_M1, h_sh_AL,
                           C_M1, C_AL, 'M1', 'Alvarado',
                           total_moves, lim_sh,
                           'S_Shannon  ↑  (ponderada |E|, intensiva)')

        # ── S_B = ln W  (Boltzmann termodinámica) ────────────────────
        draw_running_curve(ax_lnW, hist_moves, h_lnW_M1, h_lnW_AL,
                           C_BM1, C_BAL, 'M1', 'Alvarado',
                           total_moves, lim_lnW,
                           'S_B = ln W  ↑  (Boltzmann, extensiva)')

        # ── S Gibbs  (distribución canónica a T_eff) ─────────────────
        draw_running_curve(ax_gi, hist_moves, h_gi_M1, h_gi_AL,
                           '#A3E635', '#E879F9', 'M1', 'Alvarado',
                           total_moves, lim_gi,
                           'S_Gibbs  (canónica T_eff, satura en ln N)')

        # ── T_eff ────────────────────────────────────────────────────
        draw_running_curve(ax_T, hist_moves, h_T_M1, h_T_AL,
                           C_TM1, C_TAL, 'M1', 'Alvarado',
                           total_moves, lim_T,
                           'T_eff = σ²(E)/|⟨E⟩|',
                           show_inf=True,
                           cur_T1_inf=f['T_M1_inf'],
                           cur_T2_inf=f['T_AL_inf'])
        ax_T.set_xlabel('Jugada', color=TEXT_C, fontsize=7.5)

        # ── Barra de progreso ─────────────────────────────────────────
        ax_prog.cla()
        ax_prog.set_facecolor('#1E2235')
        ax_prog.set_xlim(0, total_moves); ax_prog.set_ylim(0, 1)
        ax_prog.set_yticks([])
        ax_prog.set_xlabel('Progreso de la partida', color='#64748B', fontsize=7)
        for sp in ax_prog.spines.values(): sp.set_color('#2D3250')
        ax_prog.barh(0.5, f['move'], height=0.6, color='#3B82F6', alpha=0.7)
        ax_prog.axvline(f['move'], color='#93C5FD', lw=1.5, zorder=3)
        pct = f['move'] / max(total_moves, 1) * 100
        ax_prog.text(total_moves/2, 0.5, f'{pct:.0f}%',
                     ha='center', va='center', fontsize=8,
                     color=TEXT_C, fontweight='bold')
        return []

    print(f"  Renderizando {len(frames)} frames a {fps} fps...")
    anim = FuncAnimation(fig, update, frames=len(frames),
                         interval=1000//fps, blit=False, repeat=False)
    writer = PillowWriter(fps=fps, metadata={'loop': 0})
    anim.save(output_path, writer=writer, dpi=95,
              savefig_kwargs={'facecolor': BG})
    plt.close(fig)
    mb = os.path.getsize(output_path) / 1024 / 1024
    print(f"  GIF guardado: {output_path}  ({mb:.1f} MB)")


# ─────────────────────────────────────────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('sgf',          nargs='?', default=None)
    parser.add_argument('--step',       type=int, default=1)
    parser.add_argument('--fps',        type=int, default=5)
    parser.add_argument('--max_frames', type=int, default=None)
    args = parser.parse_args()

    sgf_path = find_sgf(args.sgf)
    moves, game_info = SGFParser.parse_file(sgf_path)

    print(f"\n{'='*60}")
    print(f"  GIF ENTROPIA COMPARADA: {os.path.basename(sgf_path)}")
    print(f"  {game_info.black_player} vs {game_info.white_player}")
    print(f"  Jugadas: {len(moves)}  |  Tablero: {game_info.board_size}x{game_info.board_size}")
    print(f"  Step: {args.step}  |  FPS: {args.fps}")
    print(f"{'='*60}")

    analyzer = GoEntropyAnalyzer(manhattan_distance=1)
    frames   = precompute_frames(moves, game_info.board_size, analyzer,
                                 step=args.step, max_frames=args.max_frames)

    base     = os.path.splitext(os.path.basename(sgf_path))[0]
    out_path = os.path.join(RESULTS, f'{base}_entropy_compare.gif')
    create_animation(frames, game_info, args.fps, out_path)
    print(f"\nListo: {out_path}")


if __name__ == '__main__':
    main()
