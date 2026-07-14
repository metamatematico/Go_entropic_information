#!/usr/bin/env python3
"""
visualize_cubic_varieties.py
============================
Visualiza las variedades cúbicas H_M1(x,y) = c y cómo los enlaces del juego
de Go real las pueblan al avanzar la partida bloque a bloque.

Clave matemática:
  Para pares válidos (s0 ∈ {-1,+1}), H_M1 solo toma valores ±1:
    H_M1 = +1  para  (+1,+1), (+1,0), (-1,+1)
    H_M1 = -1  para  (+1,-1), (-1,-1), (-1,0)
  La variedad que evoluciona NO es el nivel c sino la distribución
  de probabilidad sobre los 6 pares físicos que viven en las dos curvas.

Genera:
  results/05_partidas_reales/varieties_2d_blocks.png   — panel 2×3 bloque a bloque
  results/05_partidas_reales/varieties_3d_surface.png  — superficie 3D con planos ±1
  results/05_partidas_reales/varieties_bond_evolution.png — evolución del tipo de enlace
"""

import os
import re
import json
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.gridspec as gridspec
import matplotlib.colors as mcolors
from matplotlib import cm
from pathlib import Path
from collections import Counter

# ── Rutas ──────────────────────────────────────────────────────────────────────
BASE = str(Path(__file__).resolve().parents[2])
DATA = os.path.join(BASE, 'data', 'sgf_partidas')
RES  = os.path.join(BASE, 'results', '05_partidas_reales')

# ── Hamiltonianos (dominio continuo) ───────────────────────────────────────────
def H_M1(x, y):
    return x + 2*y - x*(y**2) - (x**2)*y

def H_AL(x, y):
    return x * y

# ── Constantes ─────────────────────────────────────────────────────────────────
SPIN = {'B': -1.0, 'W': 1.0}
BLOCKS = [(1,10),(11,20),(21,30),(31,40),(41,50),(51,60)]
LABELS = ['Fase 1\nJugadas 1–10', 'Fase 2\nJugadas 11–20', 'Fase 3\nJugadas 21–30',
          'Fase 4\nJugadas 31–40', 'Fase 5\nJugadas 41–50', 'Fase 6\nJugadas 51–60']
DIRS = [(0, 1), (0, -1), (1, 0), (-1, 0)]

# Paleta cromática de evolución (rojo → morado)
BCOLORS = ['#C0392B', '#E67E22', '#D4AC0D', '#27AE60', '#2980B9', '#8E44AD']

# Pares físicos válidos: s0 ∈ {-1,+1}, s1 ∈ {-1,0,+1}
VALID_PAIRS = [(-1,-1),(-1,0),(-1,1),(1,-1),(1,0),(1,1)]

# ── SGF parser ──────────────────────────────────────────────────────────────────
_MOVE_RE = re.compile(r'(?<![A-Z]);([BW])\[([a-s]{2})\]')

def parse_sgf(path):
    text = open(path, encoding='utf-8', errors='ignore').read()
    moves = []
    for m in _MOVE_RE.finditer(text):
        p, coords = m.group(1), m.group(2)
        c, r = ord(coords[0]) - 97, ord(coords[1]) - 97
        if 0 <= c < 19 and 0 <= r < 19:
            moves.append((p, c, r))
    return moves

# ── Colectar conteos de pares de enlace por bloque ─────────────────────────────
def collect_bond_counts(max_games=3000):
    cache = os.path.join(RES, '_bond_counts_cache.json')
    if os.path.exists(cache):
        data = json.load(open(cache))
        result = []
        for bd in data:
            c = Counter()
            for k, v in bd.items():
                s0, s1 = map(float, k.split(','))
                c[(s0, s1)] = v
            result.append(c)
        return result

    files = sorted(Path(DATA).glob('*.sgf'))[:max_games]
    print(f'  Procesando {len(files)} partidas SGF...')
    bond_counts = [Counter() for _ in BLOCKS]

    for i, path in enumerate(files):
        if i % 500 == 0:
            print(f'  {i}/{len(files)}', end='\r')
        moves = parse_sgf(path)
        board = np.zeros((19, 19))
        for move_idx, (player, col, row) in enumerate(moves[:60]):
            bi = move_idx // 10
            s0 = SPIN[player]
            for dr, dc in DIRS:
                nr, nc = row + dr, col + dc
                if 0 <= nr < 19 and 0 <= nc < 19:
                    s1 = board[nr, nc]
                    bond_counts[bi][(s0, s1)] += 1
            board[row, col] = s0

    serializable = [{f'{k[0]},{k[1]}': v for k, v in c.items()} for c in bond_counts]
    json.dump(serializable, open(cache, 'w'), indent=2)
    print(f'\n  Cache guardado: {cache}')
    return bond_counts


def compute_stats(bond_counts):
    stats = []
    for counts in bond_counts:
        total = sum(counts.values()) or 1
        prob = {p: counts.get(p, 0) / total for p in VALID_PAIRS}
        # Frecuencia de tipos: campo (s1=0) vs acoplamiento (s1≠0)
        p_field    = sum(counts.get((s0, 0), 0) for s0 in [-1,1]) / total
        p_coupling = sum(counts.get((s0, s1), 0)
                         for s0 in [-1,1] for s1 in [-1,1]) / total
        mean_M1 = sum(H_M1(s0, s1) * prob[(s0,s1)] for s0,s1 in VALID_PAIRS)
        mean_AL  = sum(H_AL(s0, s1) * prob[(s0,s1)] for s0,s1 in VALID_PAIRS)
        stats.append({
            'prob': prob, 'total': total,
            'p_field': p_field, 'p_coupling': p_coupling,
            'mean_M1': mean_M1, 'mean_AL': mean_AL,
        })
    return stats


# ── FIGURA 1: Panel 2×3 — variedades cúbicas por bloque ───────────────────────
def fig_2d_blocks(stats, out_path):
    # Malla continua
    N = 600
    x = np.linspace(-1.45, 1.45, N)
    y = np.linspace(-1.45, 1.45, N)
    X, Y = np.meshgrid(x, y)
    Z = H_M1(X, Y)

    # Colormap para el fondo: azul (negativo) → blanco → rojo (positivo)
    cmap_bg = plt.cm.RdBu_r

    fig, axes = plt.subplots(2, 3, figsize=(15, 10.5),
                             facecolor='#F8F5EE')
    fig.suptitle(
        'Variedades cúbicas de $H_{M1}(x,y) = x + 2y - xy^2 - x^2y$\n'
        'y distribución de enlaces en partidas de Go profesional',
        fontsize=14, fontweight='bold', color='#1A1A2E', y=0.98
    )

    # Niveles de las curvas de nivel
    levels_ghost  = [-2.0, 0.0, 2.0]     # matemáticamente válidos, no físicos
    levels_active = [-1.0, 1.0]           # únicos valores realizados en juego

    # Etiquetas de los pares físicos
    pair_labels = {
        (-1,-1): 'B–B', (-1, 0): 'B–∅', (-1, 1): 'B–W',
        ( 1,-1): 'W–B', ( 1, 0): 'W–∅', ( 1, 1): 'W–W',
    }

    for bi, (ax, st, label) in enumerate(zip(axes.flat, stats, LABELS)):
        ax.set_facecolor('#F0EDE6')

        # Fondo: mapa de calor continuo de H_M1
        im = ax.contourf(X, Y, Z, levels=40, cmap=cmap_bg, alpha=0.55,
                         vmin=-2.2, vmax=2.2)

        # Curvas "fantasma" (c ∈ {-2,0,2}): físicamente inaccesibles
        cs_ghost = ax.contour(X, Y, Z, levels=levels_ghost,
                              colors=['#888888'], linewidths=0.8,
                              linestyles='--', alpha=0.5)
        ax.clabel(cs_ghost, fmt={-2.0: 'c=−2', 0.0: 'c=0', 2.0: 'c=+2'},
                  fontsize=6.5, colors='#888888')

        # Curvas activas (c ∈ {-1,+1}): realizadas en el juego
        cs_neg = ax.contour(X, Y, Z, levels=[-1.0],
                            colors=['#1A5276'], linewidths=2.2)
        cs_pos = ax.contour(X, Y, Z, levels=[1.0],
                            colors=['#C0392B'], linewidths=2.2)
        ax.clabel(cs_neg, fmt={-1.0: '$V_{-1}$'}, fontsize=9, colors='#1A5276')
        ax.clabel(cs_pos, fmt={ 1.0: '$V_{+1}$'}, fontsize=9, colors='#C0392B')

        # Puntos discretos: 6 pares físicos
        for (s0, s1) in VALID_PAIRS:
            p = st['prob'][(s0, s1)]
            h = H_M1(s0, s1)
            color  = '#C0392B' if h > 0 else '#1A5276'
            size   = 60 + p * 3500
            ax.scatter(s0, s1, s=size, c=color, zorder=8,
                       edgecolors='white', linewidths=1.2, alpha=0.88)
            if p > 0.015:
                lbl = f'{pair_labels[(s0,s1)]}\n{p:.2f}'
                ax.annotate(lbl, (s0, s1),
                            textcoords='offset points', xytext=(6, 4),
                            fontsize=6.5, color='#1A1A2E', zorder=9,
                            bbox=dict(boxstyle='round,pad=0.15', fc='white',
                                      alpha=0.6, ec='none'))

        # Marco con el color del bloque
        for sp in ax.spines.values():
            sp.set_color(BCOLORS[bi])
            sp.set_linewidth(2.5)

        # Barra horizontal: distribución campo vs acoplamiento
        ax_bar = ax.inset_axes([0.0, -0.10, 1.0, 0.07],
                                transform=ax.transAxes)
        ax_bar.barh(0, st['p_field'],    height=0.8, color='#F0B27A',
                    label='campo (s₁=0)')
        ax_bar.barh(0, st['p_coupling'], height=0.8, left=st['p_field'],
                    color='#7FB3D3', label='acopl. (s₁≠0)')
        ax_bar.set_xlim(0, 1)
        ax_bar.axis('off')
        ax_bar.text(st['p_field']/2, 0, f"{st['p_field']:.0%}",
                    ha='center', va='center', fontsize=7, color='#784212')
        ax_bar.text(st['p_field'] + st['p_coupling']/2, 0,
                    f"{st['p_coupling']:.0%}",
                    ha='center', va='center', fontsize=7, color='#1A5276')

        ax.set_xlim(-1.45, 1.45)
        ax.set_ylim(-1.45, 1.45)
        ax.set_xlabel('$s_0$ (piedra colocada)', fontsize=8.5)
        ax.set_ylabel('$s_1$ (vecino)', fontsize=8.5)
        ax.set_xticks([-1, 0, 1])
        ax.set_yticks([-1, 0, 1])
        ax.set_xticklabels(['B', '∅', 'W'], fontsize=8)
        ax.set_yticklabels(['B', '∅', 'W'], fontsize=8)
        ax.tick_params(length=3)
        ax.set_title(label + f'\n⟨H_M1⟩={st["mean_M1"]:+.3f}  '
                              f'⟨H_AL⟩={st["mean_AL"]:+.3f}',
                     fontsize=9, color=BCOLORS[bi], fontweight='bold', pad=4)
        ax.axhline(0, color='gray', lw=0.4, ls=':')
        ax.axvline(0, color='gray', lw=0.4, ls=':')

    # Colorbar compartida
    cbar_ax = fig.add_axes([0.92, 0.15, 0.015, 0.70])
    sm = plt.cm.ScalarMappable(cmap=cmap_bg, norm=mcolors.Normalize(-2.2, 2.2))
    sm.set_array([])
    cb = fig.colorbar(sm, cax=cbar_ax)
    cb.set_label('$H_{M1}(x,y)$', fontsize=9)
    cb.set_ticks([-2, -1, 0, 1, 2])

    # Leyenda global
    from matplotlib.lines import Line2D
    from matplotlib.patches import Patch
    handles = [
        Line2D([0],[0], color='#C0392B', lw=2.2, label='$V_{+1}$: variedad activa H=+1'),
        Line2D([0],[0], color='#1A5276', lw=2.2, label='$V_{-1}$: variedad activa H=−1'),
        Line2D([0],[0], color='#888888', lw=0.8, ls='--', label='variedades no físicas (c=−2,0,+2)'),
        Patch(color='#F0B27A', label='enlace de campo: s₁=0'),
        Patch(color='#7FB3D3', label='enlace de acoplamiento: s₁≠0'),
    ]
    fig.legend(handles=handles, loc='lower center', ncol=5,
               fontsize=8, bbox_to_anchor=(0.45, 0.01),
               framealpha=0.9, edgecolor='#CCCCCC')

    plt.subplots_adjust(left=0.06, right=0.91, top=0.93, bottom=0.12,
                        hspace=0.45, wspace=0.30)
    fig.savefig(out_path, dpi=160, bbox_inches='tight')
    plt.close(fig)
    print(f'  2D blocks: {out_path}')


# ── FIGURA 2: Superficie 3D con planos activos ─────────────────────────────────
def fig_3d_surface(stats, out_path):
    N = 120
    x = np.linspace(-1.45, 1.45, N)
    y = np.linspace(-1.45, 1.45, N)
    X, Y = np.meshgrid(x, y)
    Z = H_M1(X, Y)

    fig = plt.figure(figsize=(18, 7.5), facecolor='#F8F5EE')
    fig.suptitle(
        'Superficie $z = H_{M1}(x,y)$  y variedades cúbicas activas en el juego de Go',
        fontsize=13, fontweight='bold', color='#1A1A2E', y=0.99
    )

    gs = gridspec.GridSpec(1, 2, width_ratios=[1.5, 1.0],
                           left=0.02, right=0.97, top=0.93, bottom=0.05,
                           wspace=0.05)

    # ── Subplot 3D ──────────────────────────────────────────────────────────────
    ax3 = fig.add_subplot(gs[0], projection='3d')
    ax3.set_facecolor('#F8F5EE')

    # Superficie semitransparente coloreada por H_M1
    surf = ax3.plot_surface(X, Y, Z, cmap='RdBu_r', alpha=0.55,
                            vmin=-2.2, vmax=2.2, linewidth=0,
                            antialiased=True, rcount=60, ccount=60)

    # Planos activos z = ±1 (semitransparentes)
    Xp = np.array([[-1.45, 1.45], [-1.45, 1.45]])
    Yp = np.array([[-1.45, -1.45], [1.45, 1.45]])
    ax3.plot_surface(Xp, Yp, np.ones_like(Xp) *  1.0,
                     alpha=0.18, color='#C0392B', linewidth=0)
    ax3.plot_surface(Xp, Yp, np.ones_like(Xp) * -1.0,
                     alpha=0.18, color='#1A5276', linewidth=0)

    # Curvas de nivel proyectadas en los planos z=±1
    for c_val, col in [(-1.0, '#1A5276'), (1.0, '#C0392B')]:
        ax3.contour(X, Y, Z, levels=[c_val], zdir='z', offset=c_val,
                    colors=[col], linewidths=2.0, alpha=0.9)

    # Curvas fantasma
    for c_val in [-2.0, 0.0, 2.0]:
        ax3.contour(X, Y, Z, levels=[c_val], zdir='z', offset=c_val,
                    colors=['#AAAAAA'], linewidths=0.8, linestyles='--', alpha=0.5)

    # 6 pares físicos: tallos verticales + puntos por bloque
    pair_labels_3d = {
        (-1,-1):'B–B',(-1,0):'B–∅',(-1,1):'B–W',
        ( 1,-1):'W–B',( 1,0):'W–∅',( 1,1):'W–W'
    }
    for (s0, s1) in VALID_PAIRS:
        zval = H_M1(s0, s1)
        col_base = '#C0392B' if zval > 0 else '#1A5276'
        # Tallo vertical desde z=0 hasta zval
        ax3.plot([s0, s0], [s1, s1], [0, zval], '-', color=col_base,
                 lw=1.5, alpha=0.6)
        # Marcador base
        ax3.scatter([s0], [s1], [0], c='white', s=30, zorder=5,
                    edgecolors=col_base, linewidths=1.2)
        # Un punto por bloque, coloreado por fase
        for bi, st in enumerate(stats):
            p = st['prob'][(s0, s1)]
            ax3.scatter([s0], [s1], [zval], c=[BCOLORS[bi]],
                        s=max(10, p * 1800), alpha=0.85,
                        edgecolors='white', linewidths=0.6, zorder=7)
        # Etiqueta
        ax3.text(s0 + 0.06, s1 + 0.06, zval + 0.15,
                 pair_labels_3d[(s0, s1)], fontsize=7.5,
                 color=col_base, fontweight='bold')

    ax3.set_xlabel('$s_0$ (colocada)', fontsize=9, labelpad=6)
    ax3.set_ylabel('$s_1$ (vecino)',   fontsize=9, labelpad=6)
    ax3.set_zlabel('$H_{M1}$',         fontsize=9, labelpad=5)
    ax3.set_xlim(-1.45, 1.45); ax3.set_ylim(-1.45, 1.45)
    ax3.set_zlim(-2.5, 2.5)
    ax3.set_xticks([-1, 0, 1]); ax3.set_xticklabels(['B','∅','W'])
    ax3.set_yticks([-1, 0, 1]); ax3.set_yticklabels(['B','∅','W'])
    ax3.set_zticks([-2,-1,0,1,2])
    ax3.view_init(elev=22, azim=-55)
    ax3.set_title('Vista 3D: superficie $H_{M1}$ y\nplanos activos $z=\\pm 1$',
                  fontsize=10, color='#1A1A2E', pad=8)

    # ── Subgráfica derecha: evolución por bloque ──────────────────────────────
    gs_right = gridspec.GridSpecFromSubplotSpec(4, 1, subplot_spec=gs[1],
                                                hspace=0.55)

    # Panel A: distribución de pares por bloque (stacked bar)
    ax_bar = fig.add_subplot(gs_right[0:2])
    ax_bar.set_facecolor('#F0EDE6')

    pair_order  = [(-1,-1),(-1,0),(-1,1),(1,-1),(1,0),(1,1)]
    pair_colors = ['#2471A3','#85C1E9','#AED6F1',
                   '#E74C3C','#F1948A','#FADBD8']
    pair_names  = ['B–B','B–∅','B–W','W–B','W–∅','W–W']

    bottom = np.zeros(6)
    bars_x = np.arange(6)
    for (s0, s1), pcolor, pname in zip(pair_order, pair_colors, pair_names):
        vals = [st['prob'][(s0,s1)] for st in stats]
        ax_bar.bar(bars_x, vals, bottom=bottom, color=pcolor,
                   label=pname, width=0.75, edgecolor='white', linewidth=0.4)
        bottom += np.array(vals)

    ax_bar.set_xticks(bars_x)
    ax_bar.set_xticklabels([f'F{i+1}' for i in range(6)], fontsize=8)
    ax_bar.set_ylim(0, 1)
    ax_bar.set_ylabel('Fracción de enlaces', fontsize=8)
    ax_bar.set_title('Distribución de pares (s₀, s₁)', fontsize=9,
                     color='#1A1A2E', pad=3)
    ax_bar.legend(loc='upper right', fontsize=6.5, ncol=2,
                  framealpha=0.8, edgecolor='#CCCCCC')
    for sp in ax_bar.spines.values():
        sp.set_color('#CCCCCC')

    # Colores de fases en los ticks
    for tick, color in zip(ax_bar.get_xticklabels(), BCOLORS):
        tick.set_color(color)
        tick.set_fontweight('bold')

    # Panel B: campo vs acoplamiento
    ax_fc = fig.add_subplot(gs_right[2])
    ax_fc.set_facecolor('#F0EDE6')

    p_field    = [st['p_field']    for st in stats]
    p_coupling = [st['p_coupling'] for st in stats]

    ax_fc.fill_between(bars_x, 0, p_field,    alpha=0.7,
                       color='#F0B27A', label='campo (s₁=0)')
    ax_fc.fill_between(bars_x, p_field,
                       [f+c for f,c in zip(p_field,p_coupling)],
                       alpha=0.7, color='#7FB3D3', label='acopl. (s₁≠0)')
    ax_fc.set_xticks(bars_x)
    ax_fc.set_xticklabels([f'F{i+1}' for i in range(6)], fontsize=8)
    ax_fc.set_ylim(0, 1)
    ax_fc.set_ylabel('Fracción', fontsize=8)
    ax_fc.set_title('Campo vs Acoplamiento', fontsize=9, color='#1A1A2E', pad=3)
    ax_fc.legend(loc='upper right', fontsize=7, framealpha=0.8)
    for sp in ax_fc.spines.values():
        sp.set_color('#CCCCCC')
    for tick, color in zip(ax_fc.get_xticklabels(), BCOLORS):
        tick.set_color(color)
        tick.set_fontweight('bold')

    # Panel C: Energía media de enlace por bloque
    ax_en = fig.add_subplot(gs_right[3])
    ax_en.set_facecolor('#F0EDE6')

    mean_M1 = [st['mean_M1'] for st in stats]
    mean_AL  = [st['mean_AL'] for st in stats]

    ax_en.plot(bars_x, mean_M1, 'o-', color='#2980B9', lw=1.8,
               ms=6, label='$\\langle H_{M1}\\rangle$')
    ax_en.plot(bars_x, mean_AL,  's--', color='#C0392B', lw=1.8,
               ms=6, label='$\\langle H_{AL}\\rangle$')
    ax_en.axhline(0, color='gray', lw=0.6, ls=':')
    ax_en.set_xticks(bars_x)
    ax_en.set_xticklabels([f'F{i+1}' for i in range(6)], fontsize=8)
    ax_en.set_ylabel('⟨H⟩ por enlace', fontsize=8)
    ax_en.set_title('Energía media de enlace', fontsize=9, color='#1A1A2E', pad=3)
    ax_en.legend(loc='lower left', fontsize=7, framealpha=0.8)
    for sp in ax_en.spines.values():
        sp.set_color('#CCCCCC')
    for tick, color in zip(ax_en.get_xticklabels(), BCOLORS):
        tick.set_color(color)
        tick.set_fontweight('bold')

    # Leyenda de bloques
    from matplotlib.patches import Patch
    block_handles = [Patch(color=c, label=f'F{i+1}') for i, c in enumerate(BCOLORS)]
    fig.legend(handles=block_handles, title='Fases', loc='lower right',
               ncol=3, fontsize=7.5, bbox_to_anchor=(0.99, 0.01),
               framealpha=0.9, edgecolor='#CCCCCC')

    fig.savefig(out_path, dpi=155, bbox_inches='tight')
    plt.close(fig)
    print(f'  3D surface: {out_path}')


# ── FIGURA 3: Evolución topológica — las dos variedades activas ────────────────
def fig_bond_evolution(stats, out_path):
    """
    Muestra cómo la 'masa' probabilística en V+1 y V-1 evoluciona bloque a bloque,
    y descompone cada curva por tipo de enlace (campo vs acoplamiento).
    """
    N = 500
    x = np.linspace(-1.45, 1.45, N)
    y = np.linspace(-1.45, 1.45, N)
    X, Y = np.meshgrid(x, y)
    Z = H_M1(X, Y)

    # Pares en cada variedad activa
    v_pos = [(s0,s1) for s0,s1 in VALID_PAIRS if H_M1(s0,s1) > 0]  # V+1
    v_neg = [(s0,s1) for s0,s1 in VALID_PAIRS if H_M1(s0,s1) < 0]  # V-1

    fig = plt.figure(figsize=(16, 5.5), facecolor='#F8F5EE')
    fig.suptitle(
        'Evolución de la masa probabilística sobre $V_{-1}$ y $V_{+1}$ '
        '(las dos variedades cúbicas activas del Go)',
        fontsize=12, fontweight='bold', color='#1A1A2E', y=1.01
    )

    gs = gridspec.GridSpec(1, 3, left=0.05, right=0.97, top=0.88, bottom=0.12,
                           wspace=0.38)

    # ── Panel izquierdo: las dos curvas con evolución de masa ──────────────────
    ax_left = fig.add_subplot(gs[0])
    ax_left.set_facecolor('#F0EDE6')
    ax_left.contourf(X, Y, Z, levels=30, cmap='RdBu_r', alpha=0.30,
                     vmin=-2.2, vmax=2.2)

    # Curvas fantasma
    ax_left.contour(X, Y, Z, levels=[-2.,0.,2.], colors=['#BBBBBB'],
                    linewidths=0.7, linestyles='--', alpha=0.6)

    # Curvas activas siempre dibujadas
    ax_left.contour(X, Y, Z, levels=[-1.], colors=['#1A5276'], linewidths=2.0)
    ax_left.contour(X, Y, Z, levels=[ 1.], colors=['#C0392B'], linewidths=2.0)

    # Scatter de los 6 pares físicos: 6 capas (una por bloque)
    # Los puntos de distintos bloques se superponen con offsets suaves
    offsets = [(0.0,0.0),(-0.04,-0.04),(0.04,-0.04),
               (-0.04,0.04),(0.04,0.04),(0.0,0.0)]
    for bi, (st, bc) in enumerate(zip(stats, BCOLORS)):
        for (s0, s1) in VALID_PAIRS:
            p = st['prob'][(s0, s1)]
            dx, dy = offsets[bi]
            ax_left.scatter(s0 + dx, s1 + dy, s=max(10, p * 2200),
                            c=bc, alpha=0.75, zorder=8 + bi,
                            edgecolors='white', linewidths=0.8)

    ax_left.set_xlim(-1.45, 1.45); ax_left.set_ylim(-1.45, 1.45)
    ax_left.set_xticks([-1,0,1]); ax_left.set_xticklabels(['B','∅','W'], fontsize=9)
    ax_left.set_yticks([-1,0,1]); ax_left.set_yticklabels(['B','∅','W'], fontsize=9)
    ax_left.set_xlabel('$s_0$', fontsize=10); ax_left.set_ylabel('$s_1$', fontsize=10)
    ax_left.axhline(0, color='gray', lw=0.4, ls=':')
    ax_left.axvline(0, color='gray', lw=0.4, ls=':')
    ax_left.set_title('Masa en $V_{\\pm1}$ por fase\n(tamaño ∝ probabilidad del par)',
                      fontsize=9.5, pad=4)
    # Leyenda de fases
    from matplotlib.patches import Patch
    hl = [Patch(color=c, label=f'F{i+1}: {LABELS[i].split(chr(10))[1]}')
          for i, c in enumerate(BCOLORS)]
    ax_left.legend(handles=hl, fontsize=6.5, loc='lower right',
                   framealpha=0.85, ncol=2, edgecolor='#CCCCCC')
    for sp in ax_left.spines.values():
        sp.set_color('#CCCCCC')

    # ── Panel central: masa total en V+1 vs V-1 ────────────────────────────────
    ax_mid = fig.add_subplot(gs[1])
    ax_mid.set_facecolor('#F0EDE6')

    prob_vpos = [sum(st['prob'][p] for p in v_pos) for st in stats]
    prob_vneg = [sum(st['prob'][p] for p in v_neg) for st in stats]

    bx = np.arange(6)
    w  = 0.38
    rects1 = ax_mid.bar(bx - w/2, prob_vpos, w, color='#E74C3C', alpha=0.8,
                        edgecolor='white', label='$V_{+1}$: H=+1')
    rects2 = ax_mid.bar(bx + w/2, prob_vneg, w, color='#2980B9', alpha=0.8,
                        edgecolor='white', label='$V_{-1}$: H=−1')

    for rect, color in zip(list(rects1) + list(rects2), BCOLORS * 2):
        ax_mid.bar_label(
            ax_mid.containers[0 if rect in rects1 else 1],
            fmt='%.2f', fontsize=7, padding=2
        )

    ax_mid.set_xticks(bx)
    ax_mid.set_xticklabels([f'F{i+1}' for i in range(6)], fontsize=8.5)
    for tick, color in zip(ax_mid.get_xticklabels(), BCOLORS):
        tick.set_color(color)
        tick.set_fontweight('bold')
    ax_mid.set_ylim(0, 0.70)
    ax_mid.set_ylabel('Fracción de enlaces', fontsize=9)
    ax_mid.set_title('Masa total en cada variedad activa\npor fase del juego',
                     fontsize=9.5, pad=4)
    ax_mid.legend(fontsize=8.5, framealpha=0.85, edgecolor='#CCCCCC')
    ax_mid.axhline(0.5, color='gray', lw=0.6, ls=':')
    for sp in ax_mid.spines.values():
        sp.set_color('#CCCCCC')

    # ── Panel derecho: evolución par a par ────────────────────────────────────
    ax_right = fig.add_subplot(gs[2])
    ax_right.set_facecolor('#F0EDE6')

    pair_styles = {
        (-1,-1): ('#2471A3','o','-','B–B'),
        (-1, 0): ('#5DADE2','s','--','B–∅'),
        (-1, 1): ('#AED6F1','^',':','B–W'),
        ( 1,-1): ('#922B21','o','-','W–B'),
        ( 1, 0): ('#E74C3C','s','--','W–∅'),
        ( 1, 1): ('#F1948A','^',':','W–W'),
    }

    bx = np.arange(6)
    for (s0,s1), (col,mk,ls,lbl) in pair_styles.items():
        vals = [st['prob'][(s0,s1)] for st in stats]
        ax_right.plot(bx, vals, marker=mk, linestyle=ls, color=col,
                      lw=1.8, ms=6, label=lbl, alpha=0.9)

    ax_right.set_xticks(bx)
    ax_right.set_xticklabels([f'F{i+1}' for i in range(6)], fontsize=8.5)
    for tick, color in zip(ax_right.get_xticklabels(), BCOLORS):
        tick.set_color(color)
        tick.set_fontweight('bold')
    ax_right.set_ylabel('P(s₀, s₁)', fontsize=9)
    ax_right.set_title('Probabilidad por par de enlace\na lo largo del juego',
                       fontsize=9.5, pad=4)
    ax_right.legend(fontsize=7.5, ncol=2, framealpha=0.85, edgecolor='#CCCCCC',
                    loc='upper left')
    ax_right.set_ylim(0, None)
    ax_right.axhline(1/6, color='gray', lw=0.5, ls=':', label='uniforme')
    for sp in ax_right.spines.values():
        sp.set_color('#CCCCCC')

    fig.savefig(out_path, dpi=155, bbox_inches='tight')
    plt.close(fig)
    print(f'  Bond evolution: {out_path}')


# ── Main ───────────────────────────────────────────────────────────────────────
def main():
    os.makedirs(RES, exist_ok=True)
    print('\n' + '='*60)
    print('  VISUALIZACIÓN DE VARIEDADES CÚBICAS — Go Entrópico')
    print('='*60)

    bond_counts = collect_bond_counts()
    stats = compute_stats(bond_counts)

    print('\n  Estadisticas por bloque:')
    for i, st in enumerate(stats):
        print(f'    Fase {i+1}: {LABELS[i].split(chr(10))[1]}'
              f'  campo={st["p_field"]:.2%}  acopl.={st["p_coupling"]:.2%}'
              f'  E_M1={st["mean_M1"]:+.4f}'
              f'  E_AL={st["mean_AL"]:+.4f}')

    print('\n  Generando figuras...')
    fig_2d_blocks(stats, os.path.join(RES, 'varieties_2d_blocks.png'))
    fig_3d_surface(stats, os.path.join(RES, 'varieties_3d_surface.png'))
    fig_bond_evolution(stats, os.path.join(RES, 'varieties_bond_evolution.png'))

    print('\n  Listo.')


if __name__ == '__main__':
    main()
