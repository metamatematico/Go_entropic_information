"""
go_visualization.py
===================
Visualizacion de tableros de Go y mapas de energia con matplotlib.
Solo Python puro, sin Jupyter ni Bokeh.
"""

import numpy as np
import matplotlib.pyplot as plt
import matplotlib.patches as patches
from matplotlib.patches import Circle
from typing import Optional, List, Tuple


# ============================================================================
# VISUALIZADOR DE TABLERO
# ============================================================================

def plot_board(board: np.ndarray,
               title: str = "Tablero de Go",
               ax: Optional[plt.Axes] = None,
               show_move_numbers: Optional[List[Tuple[int, int, int]]] = None,
               highlight: Optional[Tuple[int, int]] = None,
               figsize: Tuple[int, int] = (7, 7)) -> plt.Figure:
    """
    Dibuja un tablero de Go con piedras.

    Args:
        board:      Array 2D con 'B', 'W', '.'
        title:      Titulo del grafico
        ax:         Axes existente (si None, crea figura nueva)
        show_move_numbers: lista de (row, col, numero) para anotar jugadas
        highlight:  (row, col) a marcar con circulo rojo
        figsize:    Tamanio de figura cuando ax=None
    """
    size = board.shape[0]
    create_fig = ax is None
    if create_fig:
        fig, ax = plt.subplots(figsize=figsize)
    else:
        fig = ax.get_figure()

    ax.set_facecolor('#DEB887')
    ax.set_xlim(-0.5, size - 0.5)
    ax.set_ylim(-0.5, size - 0.5)
    ax.set_aspect('equal')
    ax.invert_yaxis()

    # Cuadricula
    for i in range(size):
        ax.plot([0, size - 1], [i, i], 'k-', linewidth=0.8, zorder=1)
        ax.plot([i, i], [0, size - 1], 'k-', linewidth=0.8, zorder=1)

    # Borde grueso
    for xs, ys in [([0, size-1], [0, 0]), ([0, size-1], [size-1, size-1]),
                   ([0, 0], [0, size-1]), ([size-1, size-1], [0, size-1])]:
        ax.plot(xs, ys, 'k-', linewidth=2, zorder=1)

    # Hoshi (puntos estrella)
    hoshi = _hoshi_positions(size)
    for hr, hc in hoshi:
        ax.plot(hc, hr, 'ko', markersize=5, zorder=2)

    # Piedras
    move_map = {}
    if show_move_numbers:
        for r, c, n in show_move_numbers:
            move_map[(r, c)] = n

    for r in range(size):
        for c in range(size):
            stone = board[r, c]
            if stone == 'B':
                circ = Circle((c, r), 0.46, facecolor='#1a1a1a', edgecolor='black',
                               linewidth=1, zorder=3)
                ax.add_patch(circ)
                if (r, c) in move_map:
                    ax.text(c, r, str(move_map[(r, c)]), ha='center', va='center',
                            color='white', fontsize=7, zorder=4, fontweight='bold')
            elif stone == 'W':
                circ = Circle((c, r), 0.46, facecolor='white', edgecolor='#333',
                               linewidth=1.5, zorder=3)
                ax.add_patch(circ)
                if (r, c) in move_map:
                    ax.text(c, r, str(move_map[(r, c)]), ha='center', va='center',
                            color='black', fontsize=7, zorder=4, fontweight='bold')

    # Ultima jugada destacada
    if highlight:
        hr, hc = highlight
        ax.plot(hc, hr, 'r+', markersize=10, markeredgewidth=2, zorder=5)

    # Etiquetas de coordenadas
    letters = [c for c in 'ABCDEFGHJKLMNOPQRST'][:size]
    ax.set_xticks(range(size))
    ax.set_xticklabels(letters, fontsize=8)
    ax.set_yticks(range(size))
    ax.set_yticklabels(range(size, 0, -1), fontsize=8)
    ax.tick_params(length=0)
    ax.set_title(title, fontsize=12, fontweight='bold', pad=8)

    if create_fig:
        plt.tight_layout()
    return fig


def plot_energy_map(board: np.ndarray,
                    energy_map: np.ndarray,
                    title: str = "Mapa de Energia",
                    ax: Optional[plt.Axes] = None,
                    figsize: Tuple[int, int] = (7, 7),
                    cmap: str = 'RdBu_r',
                    alpha: float = 0.5) -> plt.Figure:
    """
    Dibuja el tablero con el mapa de energia superpuesto.

    Rojo = energia positiva (influencia blanca).
    Azul = energia negativa (influencia negra).
    """
    size = board.shape[0]
    create_fig = ax is None
    if create_fig:
        fig, ax = plt.subplots(figsize=figsize)
    else:
        fig = ax.get_figure()

    # Primero dibujar el tablero
    plot_board(board, title=title, ax=ax)

    # Superponer mapa de energia
    vmax = float(max(abs(energy_map.min()), abs(energy_map.max())))
    if vmax < 1e-10:
        vmax = 1.0
    im = ax.imshow(energy_map, cmap=cmap, vmin=-vmax, vmax=vmax,
                   origin='upper', alpha=alpha, zorder=2,
                   extent=(-0.5, size - 0.5, size - 0.5, -0.5))
    if create_fig:
        plt.colorbar(im, ax=ax, shrink=0.7, label='Energia Ising')
        plt.tight_layout()
    return fig


def _hoshi_positions(size: int) -> List[Tuple[int, int]]:
    """Devuelve posiciones hoshi segun el tamanio del tablero."""
    if size == 19:
        return [(3,3),(3,9),(3,15),(9,3),(9,9),(9,15),(15,3),(15,9),(15,15)]
    if size == 13:
        return [(3,3),(3,9),(6,6),(9,3),(9,9)]
    if size == 9:
        return [(2,2),(2,6),(4,4),(6,2),(6,6)]
    return []


# ============================================================================
# GRAFICOS DE ENTROPIA Y TEMPERATURA
# ============================================================================

def plot_entropy_comparison(names: List[str],
                             s_shannon: List[float],
                             t_eff: List[float],
                             s_boltzmann: Optional[List[float]] = None,
                             title: str = "Comparacion de Patrones: Entropia y Temperatura",
                             output_path: Optional[str] = None) -> plt.Figure:
    """
    Grafico de barras comparando entropia y temperatura efectiva
    entre multiples patrones.
    """
    n = len(names)
    rows = 2 if s_boltzmann is None else 3
    fig, axes = plt.subplots(rows, 1, figsize=(max(10, n * 0.7), 4 * rows))
    fig.suptitle(title, fontsize=13, fontweight='bold', y=0.98)

    x = np.arange(n)
    colors_s = ['#2563EB' if v == max(s_shannon) else
                '#DC2626' if v == min(s_shannon) else '#6B7280'
                for v in s_shannon]
    colors_t = ['#D97706' if v == max(t_eff) else
                '#10B981' if v == min(t_eff) else '#6B7280'
                for v in t_eff]

    # Shannon entropy
    ax0 = axes[0]
    bars = ax0.bar(x, s_shannon, color=colors_s, edgecolor='white', linewidth=0.5)
    ax0.set_xticks(x)
    ax0.set_xticklabels(names, rotation=45, ha='right', fontsize=8)
    ax0.set_ylabel('S Shannon (nats)')
    ax0.set_title('Entropia de Shannon  [mayor = mas desordenado]')
    ax0.axhline(np.mean(s_shannon), color='gray', linestyle='--', linewidth=1, label='media')
    ax0.legend(fontsize=8)
    for bar, val in zip(bars, s_shannon):
        ax0.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 0.005,
                 f'{val:.2f}', ha='center', va='bottom', fontsize=7)

    # Temperatura efectiva
    ax1 = axes[1]
    t_plot = [min(v, 10.0) for v in t_eff]   # cap visual en 10 para legibilidad
    bars2 = ax1.bar(x, t_plot, color=colors_t, edgecolor='white', linewidth=0.5)
    ax1.set_xticks(x)
    ax1.set_xticklabels(names, rotation=45, ha='right', fontsize=8)
    ax1.set_ylabel('T efectiva (u.a.)')
    ax1.set_title('Temperatura Efectiva  [mayor = mas fluctuaciones de energia]')
    ax1.axhline(np.mean(t_plot), color='gray', linestyle='--', linewidth=1, label='media')
    ax1.legend(fontsize=8)
    for bar, val in zip(bars2, t_eff):
        label = f'{val:.2f}' if val < 10.0 else f'{val:.1f}*'
        ax1.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 0.01,
                 label, ha='center', va='bottom', fontsize=7)

    if s_boltzmann is not None:
        ax2 = axes[2]
        bars3 = ax2.bar(x, s_boltzmann, color='#7C3AED', edgecolor='white', linewidth=0.5)
        ax2.set_xticks(x)
        ax2.set_xticklabels(names, rotation=45, ha='right', fontsize=8)
        ax2.set_ylabel('S Boltzmann (nats)')
        ax2.set_title('Entropia de Boltzmann a T=1  [ensamble canonico]')
        ax2.axhline(np.mean(s_boltzmann), color='gray', linestyle='--', linewidth=1, label='media')
        ax2.legend(fontsize=8)
        for bar, val in zip(bars3, s_boltzmann):
            ax2.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 0.005,
                     f'{val:.2f}', ha='center', va='bottom', fontsize=7)

    plt.tight_layout()
    if output_path:
        fig.savefig(output_path, dpi=150, bbox_inches='tight')
        print(f"Guardado: {output_path}")
    return fig


def plot_energy_grid(boards: List[np.ndarray],
                     energy_maps: List[np.ndarray],
                     names: List[str],
                     metrics: Optional[List[dict]] = None,
                     cols: int = 4,
                     output_path: Optional[str] = None) -> plt.Figure:
    """
    Grilla de mapas de energia para multiples patrones.

    Args:
        boards:      Lista de tableros numpy
        energy_maps: Lista de mapas de energia
        names:       Nombre de cada patron
        metrics:     Lista de dicts con T_eff y S_shannon por patron
        cols:        Columnas de la grilla
        output_path: Ruta para guardar la figura
    """
    n = len(boards)
    rows = int(np.ceil(n / cols))
    fig, axes = plt.subplots(rows, cols, figsize=(cols * 3.2, rows * 3.2))
    axes = np.array(axes).flatten()

    vmax_global = max(
        max(abs(em.min()), abs(em.max())) for em in energy_maps
    ) or 1.0

    for i, (board, emap, name) in enumerate(zip(boards, energy_maps, names)):
        ax = axes[i]
        size = board.shape[0]

        ax.set_facecolor('#DEB887')
        ax.set_xlim(-0.5, size - 0.5)
        ax.set_ylim(-0.5, size - 0.5)
        ax.set_aspect('equal')
        ax.invert_yaxis()

        # Cuadricula ligera
        for k in range(size):
            ax.plot([0, size-1], [k, k], 'k-', lw=0.5, zorder=1)
            ax.plot([k, k], [0, size-1], 'k-', lw=0.5, zorder=1)

        # Mapa de energia
        ax.imshow(emap, cmap='RdBu_r', vmin=-vmax_global, vmax=vmax_global,
                  origin='upper', alpha=0.55, zorder=2,
                  extent=(-0.5, size-0.5, size-0.5, -0.5))

        # Piedras
        for r in range(size):
            for c in range(size):
                s = board[r, c]
                if s == 'B':
                    ax.add_patch(Circle((c, r), 0.4, facecolor='#111', edgecolor='k', lw=0.8, zorder=3))
                elif s == 'W':
                    ax.add_patch(Circle((c, r), 0.4, facecolor='white', edgecolor='#333', lw=1, zorder=3))

        # Titulo con metricas
        subtitle = name
        if metrics and i < len(metrics):
            m = metrics[i]
            subtitle += f"\nS={m.get('S_shannon', 0):.2f}  T={m.get('T_eff', 0):.2f}"
        ax.set_title(subtitle, fontsize=8, pad=2)
        ax.set_xticks([])
        ax.set_yticks([])

    # Ocultar axes sobrantes
    for j in range(n, len(axes)):
        axes[j].set_visible(False)

    plt.suptitle("Mapas de Energia Ising — Patrones de Go", fontsize=11,
                 fontweight='bold', y=1.01)
    plt.tight_layout()
    if output_path:
        fig.savefig(output_path, dpi=150, bbox_inches='tight')
        print(f"Guardado: {output_path}")
    return fig
