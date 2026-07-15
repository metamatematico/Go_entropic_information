#!/usr/bin/env python3
"""
animate_cubic_varieties.py
==========================
MP4 animado: una partida de Go sobre la VISIÓN 3D de la fibración de Milnor.

Panel izquierdo          : tablero 19×19.
Panel derecho (arriba)   : superficie 3D  Γ(H_M1) = {z = H_M1(x,y)} ⊂ ℝ³
                           — espacio total de la fibración —
                           Las fibras z = c se ILUMINAN cuando el juego las visita.
                           Nodos A₁ (puntos críticos) se ACTIVAN con la fibra vecina.
Panel derecho (abajo)    : timeline — evolución de qué fibra c visita cada enlace.

Uso:
    python animate_cubic_varieties.py            # 1ª partida
    python animate_cubic_varieties.py  42        # índice 42 (0-based)
    python animate_cubic_varieties.py  nombre.sgf
"""

import os, sys, re
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.animation as animation
import matplotlib.colors as _mcolors
from mpl_toolkits.mplot3d import Axes3D                     # noqa: F401
from mpl_toolkits.mplot3d.art3d import Poly3DCollection
from pathlib import Path
from collections import Counter

# ── FFmpeg via imageio-ffmpeg (sin instalación adicional) ──────────────────────
try:
    import imageio_ffmpeg as _iffmpeg
    plt.rcParams['animation.ffmpeg_path'] = _iffmpeg.get_ffmpeg_exe()
    _HAS_FFMPEG = True
except Exception:
    _HAS_FFMPEG = False

# ── Rutas ──────────────────────────────────────────────────────────────────────
BASE = str(Path(__file__).resolve().parents[2])
DATA = os.path.join(BASE, 'data', 'sgf_partidas')
RES  = os.path.join(BASE, 'results', '05_partidas_reales')

# ── Hamiltoniano ───────────────────────────────────────────────────────────────
def H_M1(x, y):
    return x + 2*y - x*(y**2) - (x**2)*y

# ── Constantes ─────────────────────────────────────────────────────────────────
SPIN_MAP   = {'B': -1.0, 'W': 1.0}
DIRS       = [(0,1),(0,-1),(1,0),(-1,0)]
VALID_P    = [(-1,-1),(-1,0),(-1,1),(1,-1),(1,0),(1,1)]
PAIR_LABEL = {(-1,-1):'B–B',(-1,0):'B–∅',(-1,1):'B–W',
              ( 1,-1):'W–B',( 1,0):'W–∅',( 1,1):'W–W'}
STAR_PTS   = [(3,3),(3,9),(3,15),(9,3),(9,9),(9,15),(15,3),(15,9),(15,15)]
TRAIL_LEN  = 5

CRIT_POS =  1.2408
CRIT_NEG = -1.2408

# Puntos críticos (nodos A₁) de H_M1: ∇H_M1=0 → 3y⁴+6y²-1=0
_y_crit = float(np.sqrt((-3 + 2*np.sqrt(3)) / 3))   # ≈ 0.3933
_x_crit = float((1 - _y_crit**2) / (2 * _y_crit))   # ≈ 1.0747
CRIT_PT_POS = ( _x_crit,  _y_crit,  CRIT_POS)   # nodo A₁ en c*₊
CRIT_PT_NEG = (-_x_crit, -_y_crit,  CRIT_NEG)   # nodo A₁ en c*₋

_CMAP_F = plt.colormaps['RdBu_r']
_NORM_F = _mcolors.Normalize(-2.3, 2.3)

def _fc(c_val):
    return _CMAP_F(_NORM_F(c_val))

_col_neg = _mcolors.to_hex(_fc(-1.))
_col_pos = _mcolors.to_hex(_fc( 1.))

_MOVE_RE = re.compile(r'(?<![A-Z]);([BW])\[([a-s]{2})\]')

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

# ── Captura ─────────────────────────────────────────────────────────────────────
def _group(board, r, c, color):
    grp, stack = set(), [(r,c)]
    while stack:
        nr, nc = stack.pop()
        if (nr,nc) in grp: continue
        if not (0<=nr<19 and 0<=nc<19): continue
        if board[nr,nc] != color: continue
        grp.add((nr,nc))
        for dr,dc in DIRS: stack.append((nr+dr, nc+dc))
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
                for gr,gc in grp: board[gr,gc] = 0

# ── Pre-computar frames ─────────────────────────────────────────────────────────
def precompute(moves):
    board      = np.zeros((19,19), dtype=float)
    frames     = []
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
        new_c = [H_M1(s0, s1) for (s0,s1) in new_bonds if s0 != 0]
        frames.append({
            'idx'       : idx,
            'player'    : player,
            'col'       : col,
            'row'       : row,
            'board'     : board.copy(),
            'new_bonds' : new_bonds,
            'new_c'     : new_c,
            'cum_counts': dict(cum_counts),
        })
    return frames

# ── Malla 3D de la superficie ───────────────────────────────────────────────────
_N3  = 70
_x3  = np.linspace(-1.55, 1.55, _N3)
_y3  = np.linspace(-1.55, 1.55, _N3)
_X3, _Y3 = np.meshgrid(_x3, _y3)
_Z3  = H_M1(_X3, _Y3)

# ── Pre-computar paths 2D de las fibras activas (para dibujar en 3D) ──────────
def _fiber_segs_3d(level):
    """Extrae los segmentos de la fibra H_M1=level como lista de arrays (xs,ys)."""
    fig_t, ax_t = plt.subplots()
    cs = ax_t.contour(_X3, _Y3, _Z3, levels=[level])
    result = []
    for path in cs.get_paths():
        xy, cod = path.vertices, path.codes
        segs, seg = [], []
        if cod is None:
            segs = [xy]
        else:
            for pt, c in zip(xy, cod):
                if c == 1 and seg: segs.append(np.array(seg)); seg = [pt]
                else: seg.append(pt)
            if seg: segs.append(np.array(seg))
        for s in segs:
            if len(s) > 1: result.append(s)
    plt.close(fig_t)
    return result

print('Pre-computando curvas de fibras 3D...', end=' ', flush=True)
_segs_neg    = _fiber_segs_3d(-1.)
_segs_pos    = _fiber_segs_3d( 1.)
_segs_crit_n = _fiber_segs_3d(CRIT_NEG)
_segs_crit_p = _fiber_segs_3d(CRIT_POS)
print('ok')

# ── Preludio: barrido c de −2.2 a +2.2 ────────────────────────────────────────
def _build_prologue_c():
    """c values con densidad extra en puntos topológicamente críticos."""
    base = np.linspace(-2.20, 2.20, 50)
    step = 4.40 / 49
    pts  = []
    for c in base:
        pts.append(c)
        for cspec in [CRIT_NEG, -1., 0., 1., CRIT_POS]:
            if abs(c - cspec) < step:
                pts.extend([c] * 3)   # pausa de 3 frames extra
                break
    return np.array(pts)

print('Pre-computando fibras del preludio...', end=' ', flush=True)
_PROLOGUE_C    = _build_prologue_c()
_N_PROLOGUE    = len(_PROLOGUE_C)
_prologue_segs = [_fiber_segs_3d(c) for c in _PROLOGUE_C]
print(f'ok  ({_N_PROLOGUE} frames)')

def _prologue_status(c_val):
    """Texto descriptivo del estado topológico de la fibra H_M1⁻¹(c)."""
    if abs(c_val - CRIT_NEG) < 0.10 or abs(c_val - CRIT_POS) < 0.10:
        return f'c = {c_val:.3f}   ★  NODO A₁ — fibra singular  (g → 0)'
    elif abs(c_val + 1.) < 0.07:
        return 'c = −1.000   ◆  V₋₁ — fibra del juego  (lisa, g = 1)'
    elif abs(c_val - 1.) < 0.07:
        return 'c = +1.000   ◆  V₊₁ — fibra del juego  (lisa, g = 1)'
    else:
        return f'c = {c_val:+.3f}   ─  cúbica lisa,  g = 1'

def _build_3d_glow(ax3d, segs, level, color, lw, alpha=0.0):
    """Dibuja los segmentos de la fibra en 3D como Line3D (alpha actualizable)."""
    lines = []
    for seg in segs:
        xs, ys = seg[:,0], seg[:,1]
        zs = np.full(len(xs), level)
        ln, = ax3d.plot(xs, ys, zs, color=color, lw=lw, alpha=alpha, zorder=12)
        lines.append(ln)
    return lines

def _set_lines_alpha(lines, alpha):
    for ln in lines: ln.set_alpha(alpha)

# ── Plano horizontal animado (Poly3DCollection) ────────────────────────────────
def _make_plane(ax3d, z_val, color, alpha=0.0):
    verts = [np.array([[-1.55,-1.55,z_val],[1.55,-1.55,z_val],
                        [1.55,1.55,z_val],[-1.55,1.55,z_val]])]
    poly = Poly3DCollection(verts, alpha=alpha, facecolor=color, edgecolor='none')
    ax3d.add_collection3d(poly)
    return poly

# ── Figura ──────────────────────────────────────────────────────────────────────
def build_figure(n_moves=200):
    fig = plt.figure(figsize=(13, 6.6), facecolor='#1C1C2E')

    # ── Tablero ───────────────────────────────────────────────────────────────
    ax_b = fig.add_axes([0.01, 0.07, 0.40, 0.87])
    ax_b.set_facecolor('#C8A96E')
    ax_b.set_xlim(-0.7, 18.7); ax_b.set_ylim(-0.7, 18.7)
    ax_b.set_aspect('equal'); ax_b.axis('off')
    for i in range(19):
        ax_b.axhline(i, color='#4A2F00', lw=0.65, alpha=0.9, zorder=1)
        ax_b.axvline(i, color='#4A2F00', lw=0.65, alpha=0.9, zorder=1)
    for sc, sr in STAR_PTS:
        ax_b.plot(sc, sr, 'o', color='#4A2F00', ms=3.5, zorder=2)
    ax_b.add_patch(plt.Rectangle((-0.5,-0.5),19,19,fc='none',ec='#4A2F00',lw=2,zorder=2))
    sc_B    = ax_b.scatter([],[],s=200,c='#1A1A1A',zorder=5,edgecolors='#333333',linewidths=0.8)
    sc_W    = ax_b.scatter([],[],s=200,c='#F0F0F0',zorder=5,edgecolors='#888888',linewidths=0.8)
    sc_last = ax_b.scatter([],[],s=320,c='#FFD700',zorder=7,edgecolors='#FF8C00',linewidths=2,alpha=0.85)
    title_b = ax_b.set_title('',fontsize=10,color='#F0F0F0',fontweight='bold',pad=6)

    # ── Panel 3D: espacio total Γ(H_M1) ──────────────────────────────────────
    ax3d = fig.add_axes([0.42, 0.28, 0.57, 0.67], projection='3d')
    ax3d.set_facecolor('#0A0A18')
    ax3d.patch.set_alpha(0)

    # Superficie semitransparente (espacio total)
    ax3d.plot_surface(_X3, _Y3, _Z3, cmap='RdBu_r', alpha=0.28,
                      vmin=-2.3, vmax=2.3, linewidth=0,
                      antialiased=False, rcount=35, ccount=35)

    # Fibras estáticas de referencia (contorno en la superficie)
    for segs, lv, col, lw, ls, alp in [
        (_segs_neg,    -1.,      _col_neg, 1.5, '-',  0.50),
        (_segs_pos,     1.,      _col_pos, 1.5, '-',  0.50),
        (_segs_crit_n, CRIT_NEG,'#F39C12', 0.9, '--', 0.38),
        (_segs_crit_p, CRIT_POS,'#F39C12', 0.9, '--', 0.38),
    ]:
        for seg in segs:
            xs, ys = seg[:,0], seg[:,1]
            ax3d.plot(xs, ys, np.full(len(xs), lv),
                      color=col, lw=lw, linestyle=ls, alpha=alp, zorder=5)

    # Planos de fibra glow (inicialmente invisibles)
    plane_neg = _make_plane(ax3d, -1., _col_neg, alpha=0.0)
    plane_pos = _make_plane(ax3d,  1., _col_pos, alpha=0.0)

    # Glow: curvas gruesas en las fibras activas (alpha animado)
    glow_neg_lines = _build_3d_glow(ax3d, _segs_neg, -1., _col_neg, lw=4.5, alpha=0.0)
    glow_pos_lines = _build_3d_glow(ax3d, _segs_pos,  1., _col_pos, lw=4.5, alpha=0.0)

    # ── Preludio: fibra móvil + plano barrido ────────────────────────────────
    _N_SLOTS = 14   # suficiente para cualquier número de segmentos por fibra
    prologue_lines = []
    for _ in range(_N_SLOTS):
        ln, = ax3d.plot([], [], [], color='white', lw=2.4, alpha=0.0, zorder=13)
        prologue_lines.append(ln)
    _pv0 = np.array([[-1.55,-1.55,0.],[1.55,-1.55,0.],
                     [1.55, 1.55,0.],[-1.55, 1.55,0.]])
    prologue_plane = Poly3DCollection([_pv0], alpha=0.0,
                                      facecolor='white', edgecolor='none')
    ax3d.add_collection3d(prologue_plane)

    # ── Fibras críticas: glow secundario (activado por la fibra de juego vecina) ─
    glow_crit_neg_lines = _build_3d_glow(ax3d, _segs_crit_n, CRIT_NEG, '#F59B0A', lw=3.0, alpha=0.0)
    glow_crit_pos_lines = _build_3d_glow(ax3d, _segs_crit_p, CRIT_POS, '#F59B0A', lw=3.0, alpha=0.0)

    # ── Nodos A₁: puntos críticos de H_M1 (auto-intersección de la fibra singular) ─
    # Marcador permanente: diamante pequeño, siempre visible
    for (px, py, pz) in [CRIT_PT_POS, CRIT_PT_NEG]:
        ax3d.scatter([px], [py], [pz], s=70, c='#F59B0A', marker='D',
                     edgecolors='white', linewidths=1.0,
                     depthshade=False, zorder=24, alpha=0.88)
    # Halo animado: estrella grande que crece con el glow de la fibra vecina
    sc_node_neg = ax3d.scatter(
        [CRIT_PT_NEG[0]], [CRIT_PT_NEG[1]], [CRIT_PT_NEG[2]],
        s=0, c='#F59B0A', marker='*',
        edgecolors='#FFEEAA', linewidths=1.8,
        depthshade=False, zorder=26, alpha=0.0)
    sc_node_pos = ax3d.scatter(
        [CRIT_PT_POS[0]], [CRIT_PT_POS[1]], [CRIT_PT_POS[2]],
        s=0, c='#F59B0A', marker='*',
        edgecolors='#FFEEAA', linewidths=1.8,
        depthshade=False, zorder=26, alpha=0.0)
    # Tallos estáticos de los 6 pares (desde z=0 hasta H_M1)
    for s0, s1 in VALID_P:
        zv = H_M1(s0, s1)
        col = _mcolors.to_hex(_fc(zv))
        ax3d.plot([s0,s0],[s1,s1],[0,zv], color=col, lw=1.2, alpha=0.40, zorder=6)
        ax3d.plot([s0],[s1],[0], 'o', color='white', ms=2.5, alpha=0.35, zorder=6)

    # Scatter dinámico en la superficie (tamaño ∝ conteo acumulado)
    sc3d = []
    for s0, s1 in VALID_P:
        zv  = H_M1(s0, s1)
        col = _mcolors.to_hex(_fc(zv))
        sc  = ax3d.scatter([s0],[s1],[zv], s=0, c=col,
                           edgecolors='white', linewidths=0.8, depthshade=False, zorder=10)
        sc3d.append(sc)

    # Trail: puntos nuevos en 3D (flashes dorados)
    trail3d = []
    for t in range(TRAIL_LEN):
        alpha_t = 1.0 - t / TRAIL_LEN
        sc_t = ax3d.scatter([], [], [], s=max(30, 380-t*65), c='#FFD700',
                            edgecolors='white', linewidths=0.9,
                            alpha=alpha_t, depthshade=False, zorder=14)
        trail3d.append(sc_t)

    # Ejes
    ax3d.set_xlabel('$s_0$',   color='#AAAAAA', fontsize=9, labelpad=4)
    ax3d.set_ylabel('$s_1$',   color='#AAAAAA', fontsize=9, labelpad=4)
    ax3d.set_zlabel('$c = H_{M1}$', color='#AAAAAA', fontsize=9, labelpad=4)
    ax3d.set_xticks([-1,0,1]); ax3d.set_xticklabels(['B','∅','W'], fontsize=7.5, color='#CCCCCC')
    ax3d.set_yticks([-1,0,1]); ax3d.set_yticklabels(['B','∅','W'], fontsize=7.5, color='#CCCCCC')
    ax3d.set_zticks([-2, CRIT_NEG, -1, 0, 1, CRIT_POS, 2])
    ax3d.set_zticklabels(['-2', '$c_-^*$', '-1', '0', '+1', '$c_+^*$', '+2'],
                          fontsize=7, color='#AAAAAA')
    ax3d.set_zlim(-2.6, 2.6)
    ax3d.set_xlim(-1.6, 1.6); ax3d.set_ylim(-1.6, 1.6)
    ax3d.xaxis.pane.fill = False; ax3d.yaxis.pane.fill = False; ax3d.zaxis.pane.fill = False
    ax3d.xaxis.pane.set_edgecolor('#222244')
    ax3d.yaxis.pane.set_edgecolor('#222244')
    ax3d.zaxis.pane.set_edgecolor('#222244')
    ax3d.grid(True, color='#1A1A33', lw=0.4, alpha=0.5)
    ax3d.view_init(elev=26, azim=-52)

    title_v = ax3d.set_title('', pad=2)   # vacío — info está en franja superior

    # (sin texto flotante sobre la variedad — ver leyenda en franja inferior)

    # ── Panel timeline ────────────────────────────────────────────────────────
    ax_t = fig.add_axes([0.44, 0.05, 0.54, 0.18])
    ax_t.set_facecolor('#0E0E1A')
    ax_t.set_xlim(0, max(n_moves+5, 30))
    ax_t.set_ylim(-2.55, 2.55)
    for c_ref, col_ref, lw_ref, ls_ref, alp_ref in [
        (-1.,     _col_neg,  1.3, '-',  0.55),
        ( 1.,     _col_pos,  1.3, '-',  0.55),
        (CRIT_NEG,'#F39C12', 0.8, '--', 0.42),
        (CRIT_POS,'#F39C12', 0.8, '--', 0.42),
        ( 0.,     '#445566', 0.5, ':',  0.38),
    ]:
        ax_t.axhline(c_ref, color=col_ref, lw=lw_ref, ls=ls_ref, alpha=alp_ref, zorder=2)
    sc_timeline = ax_t.scatter([],[],s=11,zorder=5,edgecolors='none',alpha=0.85)
    sc_tcursor  = ax_t.scatter([],[],s=170,zorder=8,edgecolors='white',linewidths=1.3)
    ax_t.set_yticks([-2, CRIT_NEG, -1, 0, 1, CRIT_POS, 2])
    ax_t.set_yticklabels(['-2','$c_-^*$','$V_{-1}$','0','$V_{+1}$','$c_+^*$','+2'],
                          fontsize=7, color='#AAAAAA')
    ax_t.set_xlabel('Jugada', color='#AAAAAA', fontsize=8)
    ax_t.set_ylabel('$c$', color='#AAAAAA', fontsize=9)
    ax_t.tick_params(colors='#555577', labelsize=7)
    for sp in ax_t.spines.values(): sp.set_color('#333355')
    ax_t.set_title('Evolución: fibra $c$ visitada por cada enlace',
                   fontsize=8.0, color='#BBBBBB', pad=3)

    prog_txt = fig.text(0.44, 0.003, '', ha='left', va='bottom',
                        fontsize=7.5, color='#777777')

    # ── Título principal ──────────────────────────────────────────────────────
    fig.text(0.50, 0.999,
             '$H_{M1}(x,y)=x+2y-xy^2-x^2y$   |   '
             'Fibración de Milnor: $\\Gamma(H_{M1})\\subset\\mathbb{A}^3$',
             ha='center', va='top', fontsize=10, color='#DDDDDD')

    # ── Leyenda compacta (franja entre título y variedad, sin solapar) ────────
    # línea 1: descripción geométrica
    fig.text(0.50, 0.975,
             'Espacio total  $z=H_{M1}(s_0,s_1)$  —  '
             'cada sección horizontal $z=c$ es una fibra de la fibración',
             ha='center', va='top', fontsize=7.6, color='#9090BB')
    # línea 2: guía de color / símbolos
    fig.text(0.50, 0.959,
             '─── $V_{-1}$  ($c{=}-1$, g=1)   '
             '─── $V_{+1}$  ($c{=}+1$, g=1)   '
             '╌╌ $c^*\\!\\approx\\!\\pm1.24$  (singular, nodo $A_1$)   '
             '◆ = punto crítico  (∇$H$=0)   '
             '★ activo = fibra vecina visitada',
             ha='center', va='top', fontsize=7.5, color='#727299')

    # ── Estado dinámico: fibra activa (texto en franja entre 3D y timeline) ──
    fiber_status = fig.text(0.70, 0.248, '',
                            ha='center', va='center',
                            fontsize=8.5, color='#FFE066',
                            fontweight='bold',
                            bbox=dict(boxstyle='round,pad=0.30',
                                      fc='#08081A', ec='#333360',
                                      alpha=0.88))

    artists = dict(
        sc_B=sc_B, sc_W=sc_W, sc_last=sc_last, title_b=title_b,
        title_v=title_v,
        sc3d=sc3d, trail3d=trail3d,
        plane_neg=plane_neg, plane_pos=plane_pos,
        glow_neg=glow_neg_lines, glow_pos=glow_pos_lines,
        glow_crit_neg=glow_crit_neg_lines, glow_crit_pos=glow_crit_pos_lines,
        sc_node_neg=sc_node_neg, sc_node_pos=sc_node_pos,
        prologue_lines=prologue_lines, prologue_plane=prologue_plane,
        sc_timeline=sc_timeline, sc_tcursor=sc_tcursor,
        prog_txt=prog_txt,
        fiber_status=fiber_status,
    )
    return fig, ax_b, ax3d, ax_t, artists


# ── Actualización de frame ──────────────────────────────────────────────────────
def make_update(frames, artists, game_name):
    # Pre-construir timeline completo
    tl_x, tl_y, tl_c = [], [], []
    for fd in frames:
        for c_val in fd['new_c']:
            tl_x.append(fd['idx']+1)
            tl_y.append(c_val)
            tl_c.append(c_val)
    tl_x    = np.array(tl_x)
    tl_y    = np.array(tl_y)
    tl_rgba = np.array([list(_fc(c)) for c in tl_c])

    def _hide_prologue():
        """Apaga todos los elementos del preludio."""
        for ln in artists['prologue_lines']:
            ln.set_alpha(0)
            ln.set_data_3d([], [], [])
        artists['prologue_plane'].set_alpha(0)

    def update(fi):

        # ══════════════════════════════════════════════════════════════════════
        # PRELUDIO: barrido c de −2.2 → +2.2 mostrando deformación de la fibra
        # ══════════════════════════════════════════════════════════════════════
        if fi < _N_PROLOGUE:
            c_val = float(_PROLOGUE_C[fi])
            segs  = _prologue_segs[fi]
            col_f = _mcolors.to_hex(_fc(c_val))
            is_crit = abs(c_val - CRIT_NEG) < 0.10 or abs(c_val - CRIT_POS) < 0.10
            is_game = abs(c_val + 1.) < 0.07 or abs(c_val - 1.) < 0.07

            # Tablero vacío con título de preludio
            artists['sc_B'].set_offsets(np.empty((0,2)))
            artists['sc_W'].set_offsets(np.empty((0,2)))
            artists['sc_last'].set_offsets(np.empty((0,2)))
            artists['title_b'].set_text(
                'Preludio  ·  Deformación de la fibración de Milnor')

            # Fibra barrida: actualizar Line3D slots
            lw_f = 3.0 if is_crit else (2.6 if is_game else 2.0)
            for i, ln in enumerate(artists['prologue_lines']):
                if i < len(segs) and len(segs[i]) > 1:
                    seg = segs[i]
                    ln.set_data_3d(seg[:,0], seg[:,1],
                                   np.full(len(seg), c_val))
                    ln.set_color(col_f)
                    ln.set_linewidth(lw_f)
                    ln.set_alpha(0.97)
                else:
                    ln.set_data_3d([], [], [])
                    ln.set_alpha(0)

            # Plano barrido (color + alpha dinámico)
            pv = np.array([[-1.55,-1.55,c_val],[1.55,-1.55,c_val],
                           [ 1.55, 1.55,c_val],[-1.55, 1.55,c_val]])
            artists['prologue_plane'].set_verts([pv])
            artists['prologue_plane'].set_facecolor(col_f)
            plane_a = 0.30 if is_crit else (0.22 if is_game else 0.11)
            artists['prologue_plane'].set_alpha(plane_a)

            # Nodo A₁: destacar en los momentos críticos
            if abs(c_val - CRIT_NEG) < 0.10:
                artists['sc_node_neg'].set_sizes([500])
                artists['sc_node_neg'].set_alpha(0.95)
            else:
                artists['sc_node_neg'].set_sizes([0]); artists['sc_node_neg'].set_alpha(0)
            if abs(c_val - CRIT_POS) < 0.10:
                artists['sc_node_pos'].set_sizes([500])
                artists['sc_node_pos'].set_alpha(0.95)
            else:
                artists['sc_node_pos'].set_sizes([0]); artists['sc_node_pos'].set_alpha(0)

            # Apagar glow del juego
            artists['plane_neg'].set_alpha(0); artists['plane_pos'].set_alpha(0)
            _set_lines_alpha(artists['glow_neg'], 0)
            _set_lines_alpha(artists['glow_pos'], 0)
            _set_lines_alpha(artists['glow_crit_neg'], 0)
            _set_lines_alpha(artists['glow_crit_pos'], 0)
            for sc in artists['sc3d']:     sc.set_sizes([0])
            for sc in artists['trail3d']: sc.set_offsets(np.empty((0,3)))
            artists['sc_timeline'].set_offsets(np.empty((0,2)))
            artists['sc_tcursor'].set_offsets(np.empty((0,2)))

            # Texto dinámico y barra de progreso
            artists['fiber_status'].set_text(_prologue_status(c_val))
            pct = (fi + 1) / _N_PROLOGUE * 100
            bar = '█'*int(pct/2) + '░'*(50-int(pct/2))
            artists['prog_txt'].set_text(
                f'[{bar}]  barrido  c = {c_val:+.2f}')
            return []

        # ══════════════════════════════════════════════════════════════════════
        # JUEGO: animación normal (frame desplazado por _N_PROLOGUE)
        # ══════════════════════════════════════════════════════════════════════
        _hide_prologue()

        game_fi = fi - _N_PROLOGUE
        if game_fi >= len(frames):
            game_fi = len(frames) - 1
        fd     = frames[game_fi]
        board  = fd['board']
        player = fd['player']
        col    = fd['col']
        row    = fd['row']
        new_b  = fd['new_bonds']
        new_c  = fd['new_c']
        cum    = fd['cum_counts']

        # ── Tablero ────────────────────────────────────────────────────────
        b_pos = np.argwhere(board == -1)
        w_pos = np.argwhere(board ==  1)
        artists['sc_B'].set_offsets(b_pos[:,[1,0]] if len(b_pos) else np.empty((0,2)))
        artists['sc_W'].set_offsets(w_pos[:,[1,0]] if len(w_pos) else np.empty((0,2)))
        artists['sc_last'].set_offsets([[col, row]])
        artists['sc_last'].set_facecolor('#FFD700' if player=='B' else '#FFEEAA')
        move_label = 'Negras' if player=='B' else 'Blancas'
        col_ltr = chr(ord('A') + col + (1 if col >= 8 else 0))
        artists['title_b'].set_text(
            f'Jugada {fd["idx"]+1}  ·  {move_label}  {col_ltr}{19-row}')

        # ── Scatter 3D: tamaños acumulados ────────────────────────────────
        max_c_val = max(cum.values()) if cum else 1
        for i, pair in enumerate(VALID_P):
            size = np.sqrt(cum.get(pair,0) / max_c_val) * 380
            try:
                artists['sc3d'][i].set_sizes([size])
            except Exception:
                artists['sc3d'][i]._sizes = np.array([size])

        # ── Trail 3D ───────────────────────────────────────────────────────
        valid_new = [(s0,s1) for s0,s1 in new_b if s0!=0]
        for t in range(TRAIL_LEN-1, 0, -1):
            prev = artists['trail3d'][t-1].get_offsets()
            if hasattr(prev,'_data'):    # 3D offsets stored differently
                prev_arr = prev._data
            else:
                try:
                    prev_arr = np.array(prev)
                except Exception:
                    prev_arr = np.empty((0,3))
            if len(prev_arr):
                artists['trail3d'][t].set_offsets(prev_arr)
            else:
                artists['trail3d'][t].set_offsets(np.empty((0,3)))

        if valid_new:
            pts3d = np.array([[s0, s1, H_M1(s0,s1)] for s0,s1 in valid_new])
            artists['trail3d'][0].set_offsets(pts3d)
            artists['trail3d'][0].set_facecolor(
                ['#FFD700' if H_M1(s0,s1)>0 else '#87CEEB' for s0,s1 in valid_new])
        else:
            artists['trail3d'][0].set_offsets(np.empty((0,3)))

        # ── GLOW: fibras que se iluminan ───────────────────────────────────
        glow_neg = 0.0
        glow_pos = 0.0
        for t in range(TRAIL_LEN):
            fi_prev = fi - t
            if 0 <= fi_prev < len(frames):
                decay = (1.0 - t / TRAIL_LEN) * 0.95
                prev_c = frames[fi_prev]['new_c']
                if any(c < 0 for c in prev_c): glow_neg = max(glow_neg, decay)
                if any(c > 0 for c in prev_c): glow_pos = max(glow_pos, decay)

        artists['plane_neg'].set_alpha(glow_neg * 0.22)
        artists['plane_pos'].set_alpha(glow_pos * 0.22)
        _set_lines_alpha(artists['glow_neg'], glow_neg)
        _set_lines_alpha(artists['glow_pos'], glow_pos)

        # ── Nodos A₁: activación secundaria (topológicamente vinculada) ───
        # La fibra crítica y su nodo responden cuando se visita la fibra lisa vecina
        _set_lines_alpha(artists['glow_crit_neg'], glow_neg * 0.70)
        _set_lines_alpha(artists['glow_crit_pos'], glow_pos * 0.70)
        artists['sc_node_neg'].set_sizes([glow_neg * 580])
        artists['sc_node_neg'].set_alpha(min(glow_neg * 1.2, 1.0))
        artists['sc_node_pos'].set_sizes([glow_pos * 580])
        artists['sc_node_pos'].set_alpha(min(glow_pos * 1.2, 1.0))

        # ── Texto dinámico: fibra activa ───────────────────────────────────
        if new_c:
            neg_n = sum(1 for c in new_c if c < 0)
            pos_n = sum(1 for c in new_c if c > 0)
            parts = []
            if neg_n:
                parts.append(f'{neg_n}× V₋₁ (c=−1, g=1)')
            if pos_n:
                parts.append(f'{pos_n}× V₊₁ (c=+1, g=1)')
            status = 'Fibra activa:  ' + '   +   '.join(parts)
        else:
            status = ''
        artists['fiber_status'].set_text(status)

        # ── Timeline ───────────────────────────────────────────────────────
        mask = tl_x <= (fi+1)
        if mask.any():
            artists['sc_timeline'].set_offsets(
                np.column_stack([tl_x[mask], tl_y[mask]]))
            artists['sc_timeline'].set_facecolor(tl_rgba[mask])
        else:
            artists['sc_timeline'].set_offsets(np.empty((0,2)))

        if new_c:
            mean_c = float(np.mean(new_c))
            artists['sc_tcursor'].set_offsets([[fi+1, mean_c]])
            artists['sc_tcursor'].set_facecolor([list(_fc(mean_c))])
        else:
            artists['sc_tcursor'].set_offsets(np.empty((0,2)))

        # ── Progreso ───────────────────────────────────────────────────────
        pct = (fd['idx']+1) / len(frames) * 100
        bar = '█'*int(pct/2) + '░'*(50-int(pct/2))
        artists['prog_txt'].set_text(
            f'[{bar}]  jugada {fd["idx"]+1}/{len(frames)}')
        return []

    return update


# ── Main ────────────────────────────────────────────────────────────────────────
def main():
    files = sorted(Path(DATA).glob('*.sgf'))
    if not files:
        print(f'No se encontraron SGF en {DATA}'); return

    arg = sys.argv[1] if len(sys.argv) > 1 else None
    if arg is None:          sgf_path = files[0]
    elif arg.isdigit():      sgf_path = files[int(arg) % len(files)]
    else:
        matches = [f for f in files if arg in f.name]
        sgf_path = matches[0] if matches else files[0]

    game_name = sgf_path.stem
    print(f'Partida: {game_name}')
    moves = parse_sgf(sgf_path)
    if not moves: print('No se encontraron jugadas.'); return
    print(f'Total jugadas: {len(moves)}')

    print('Pre-computando frames...')
    frames = precompute(moves)

    print('Construyendo figura 3D...')
    fig, ax_b, ax3d, ax_t, artists = build_figure(n_moves=len(frames))

    update_fn = make_update(frames, artists, game_name)

    n_frames = _N_PROLOGUE + len(frames) + 12
    fps = 5
    print(f'Animando {n_frames} frames a {fps} fps...')
    ani = animation.FuncAnimation(
        fig, update_fn,
        frames=n_frames, interval=1000//fps,
        blit=False, repeat=False,
    )

    out_mp4 = os.path.join(RES, f'variety_game_{game_name[:50]}.mp4')
    if _HAS_FFMPEG:
        print(f'Guardando MP4: {out_mp4}')
        Writer = animation.FFMpegWriter(
            fps=fps, bitrate=3500,
            extra_args=['-vcodec', 'libx264', '-pix_fmt', 'yuv420p', '-crf', '20'])
        ani.save(out_mp4, writer=Writer, dpi=105)
        plt.close(fig)
        print(f'  Listo  ({os.path.getsize(out_mp4)//1024} KB)')
    else:
        # Fallback: GIF si ffmpeg no disponible
        out_gif = out_mp4.replace('.mp4', '.gif')
        print(f'[AVISO] ffmpeg no disponible — guardando GIF: {out_gif}')
        ani.save(out_gif, writer=animation.PillowWriter(fps=fps), dpi=105)
        plt.close(fig)
        print(f'  Listo  ({os.path.getsize(out_gif)//1024} KB)')


if __name__ == '__main__':
    main()
