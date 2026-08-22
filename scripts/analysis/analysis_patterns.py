"""
analysis_patterns.py
====================
Analisis de entropia y temperatura efectiva para los 19 patrones de
apertura del juego de Go descritos en la Tabla I del articulo:

    "Pattern Acquisition and Comparative Analysis in the Game of Go"
    Journal of Go Studies, Vol. 19 No. 2, 2025.

Metodologia:
    1. Cada patron se codifica como tablero 9x9 (esquina superior izquierda)
       con las piedras en sus posiciones estandar de apertura.
    2. Se calcula el mapa de energia usando el modelo de Ising clasico
       con kernels Manhattan-1 y Manhattan-2.
    3. Se mide temperatura efectiva T_eff y entropia de Shannon S.
    4. Se comparan los 19 patrones.

Salidas (directorio results/):
    - energy_grid_M1.png  : grilla de mapas de energia (Manhattan-1)
    - energy_grid_M2.png  : grilla de mapas de energia (Manhattan-2)
    - entropy_compare.png : comparacion de entropia y temperatura
    - ranking.txt         : ranking de patrones por entropia
"""

import sys
from pathlib import Path
import os
import numpy as np
import matplotlib
matplotlib.use('Agg')   # sin GUI, guarda a archivo
import matplotlib.pyplot as plt

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from src.go_ising_classical import ClassicalIsingModel, EnergyMapGenerator
from src.go_entropy import GoEntropyAnalyzer, board_from_stones
from src.go_visualization import plot_energy_grid, plot_entropy_comparison

_BASE       = str(Path(__file__).resolve().parents[2])
RESULTS_DIR = os.path.join(_BASE, 'results', '01_patrones')
REPORTS_DIR = os.path.join(_BASE, 'results', 'reports')
ENTROPY_DIR = os.path.join(_BASE, 'results', '03_entropia')
os.makedirs(RESULTS_DIR, exist_ok=True)
os.makedirs(REPORTS_DIR, exist_ok=True)
os.makedirs(ENTROPY_DIR, exist_ok=True)

# ============================================================================
# DEFINICION DE PATRONES  (tablero 9x9, coordenadas 0-indexed desde esquina)
#
# Notacion Go estandar en tablero 9x9 (esquina sup-izq del 19x19):
#   (0,0) = esquina 1-1
#   (2,2) = san-san 3-3
#   (2,3) = komoku 3-4
#   (3,3) = hoshi 4-4
#
# Piedras:  B = Negro  |  W = Blanco
# Fuente:   Tabla I del articulo (columna 2025)
# ============================================================================

BOARD_SIZE = 9

# Cada entrada: (id, descripcion, [(color, row, col), ...])
PATTERNS = [
    (
        '1b',
        '4-4 hoshi',
        [('B', 3, 3)],
    ),
    (
        '2b',
        '3-4 komoku',
        [('B', 2, 3)],
    ),
    (
        '3b',
        'Approach bajo a 3-4',
        # Opponent en komoku (2,3), jugador approacha en keima (3,5)
        [('W', 2, 3), ('B', 3, 5)],
    ),
    (
        '4b',
        'Invasion san-san (3-3) a hoshi',
        # Defensor en hoshi (3,3), invasor en san-san (2,2)
        [('W', 3, 3), ('B', 2, 2)],
    ),
    (
        '5b',
        'Joseki san-san — invader en gote',
        # Secuencia estandar tras invasion san-san (jugador en gote)
        [('W', 3, 3), ('B', 2, 2), ('W', 3, 2), ('W', 2, 1), ('B', 3, 1)],
    ),
    (
        '6b',
        'Extension blanca tras joseki',
        # Blancas extienden en 3ra linea tras completar el cierre
        [('W', 3, 3), ('B', 2, 2), ('W', 3, 2), ('W', 2, 1), ('B', 3, 1), ('W', 4, 2)],
    ),
    (
        '7b',
        'Approach bajo a 4-4',
        # Oponente en hoshi (3,3), jugador approacha en (4,5) — 5ta linea keima
        [('W', 3, 3), ('B', 4, 5)],
    ),
    (
        '8b',
        'Approach a cercado desde 4-4',
        # Negras tienen cercado (3,3)+(2,5), blancas approachan desde (4,6)
        [('B', 3, 3), ('B', 2, 5), ('W', 4, 6)],
    ),
    (
        '9b',
        'Joseki san-san — variante',
        # Variante: B extiende hacia arriba en lugar de hacia abajo
        [('W', 3, 3), ('B', 2, 2), ('W', 3, 2), ('W', 2, 1), ('B', 1, 2)],
    ),
    (
        '10b',
        'Salto doble desde komoku (cercado)',
        # Negras cierran la esquina con salto doble desde komoku
        [('B', 2, 3), ('B', 2, 5)],
    ),
    (
        '11b',
        'Approach alto a komoku',
        # Oponente en komoku (2,3), jugador approacha en (4,4) — 4ta linea
        [('W', 2, 3), ('B', 4, 4)],
    ),
    (
        '12b',
        'Joseki san-san — 6 jugadas',
        # Continuation de 5b con respuesta de blancas en la linea 1
        [('W', 3, 3), ('B', 2, 2), ('W', 3, 2), ('W', 2, 1), ('B', 3, 1), ('W', 1, 3)],
    ),
    (
        '13b',
        'Approach bajo desde 5ta linea a 4-4',
        # Approacha a hoshi desde abajo (5ta linea)
        [('W', 3, 3), ('B', 5, 4)],
    ),
    (
        '14b',
        'San-san joseki + extension 3ra linea',
        # Post-joseki: blancas extienden en la 3ra linea (tennuki implicito)
        [('W', 3, 3), ('B', 2, 2), ('W', 3, 2), ('W', 2, 1),
         ('B', 3, 1), ('W', 4, 2), ('W', 5, 2)],
    ),
    (
        '15b',
        'San-san joseki — hane blanco',
        # Secuencia alternativa: blancas hacen hane
        [('W', 3, 3), ('B', 2, 2), ('W', 2, 3), ('B', 1, 3), ('W', 1, 2)],
    ),
    (
        '16b',
        'Approach a cercado (menos frecuente)',
        # Negras tienen posicion (3,3)+(2,5), blancas approachan desde (3,7)
        [('B', 3, 3), ('B', 2, 5), ('W', 3, 7)],
    ),
    (
        '17b',
        'Tras hane blanco en joseki',
        # Continuation de 15b: negras responden
        [('W', 3, 3), ('B', 2, 2), ('W', 2, 3), ('B', 1, 3), ('W', 1, 2), ('B', 1, 4)],
    ),
    (
        '18b',
        'Joseki menos frecuente en juego moderno',
        # Blancas en komoku (2,3), negras en san-san (2,2) + extension
        [('W', 2, 3), ('B', 2, 2), ('B', 1, 3), ('W', 1, 2)],
    ),
    (
        '19b',
        'Continuation de joseki (patron 9b)',
        # Tras la variante de 9b: negras conectan en la esquina
        [('W', 3, 3), ('B', 2, 2), ('W', 3, 2), ('W', 2, 1), ('B', 1, 2), ('B', 2, 3)],
    ),
]


# ============================================================================
# ANALISIS
# ============================================================================

def analyze_patterns(manhattan_distance: int = 1) -> dict:
    """
    Ejecuta el analisis de Ising + entropia para todos los patrones.

    Returns:
        dict con boards, energy_maps, metricas y nombres.
    """
    analyzer = GoEntropyAnalyzer(manhattan_distance=manhattan_distance)

    ids, descs, boards, emaps, metrics = [], [], [], [], []

    for pid, desc, stones in PATTERNS:
        board = board_from_stones(BOARD_SIZE, stones)
        result = analyzer.analyze(board, T=1.0)

        ids.append(pid)
        descs.append(desc)
        boards.append(board)
        emaps.append(result['energy_map'])
        metrics.append({
            'id': pid,
            'desc': desc,
            'n_stones': len(stones),
            'total_energy': result['total_energy'],
            'mean_energy': result['mean_energy'],
            'std_energy': result['std_energy'],
            'T_eff': result['T_eff'],
            'S_shannon': result['S_shannon'],
            'S_boltzmann': result['S_boltzmann'],
        })

    return {
        'ids': ids,
        'descs': descs,
        'boards': boards,
        'energy_maps': emaps,
        'metrics': metrics,
        'manhattan_distance': manhattan_distance,
    }


def print_ranking(metrics: list, sort_by: str = 'S_shannon'):
    """Imprime ranking de patrones segun la metrica elegida."""
    ranked = sorted(metrics, key=lambda m: m[sort_by], reverse=True)
    col = sort_by.replace('_', ' ')
    print(f"\n{'='*62}")
    print(f"  RANKING por {col}  (mayor = mas desordenado / mayor T)")
    print(f"{'='*62}")
    print(f"  {'#':>2}  {'ID':<5}  {col:>12}  {'T_eff':>8}  {'S_Bolt':>8}  Descripcion")
    print(f"  {'-'*58}")
    for i, m in enumerate(ranked, 1):
        print(f"  {i:>2}  {m['id']:<5}  {m[sort_by]:>12.4f}  "
              f"{m['T_eff']:>8.4f}  {m['S_boltzmann']:>8.4f}  {m['desc']}")
    print()
    return ranked


def save_ranking(metrics: list, path: str):
    """Guarda el ranking completo en un archivo de texto."""
    with open(path, 'w', encoding='utf-8') as f:
        f.write("RANKING DE PATRONES DE GO — ENTROPIA E TEMPERATURA\n")
        f.write("Modelo: Ising Clasico\n")
        f.write("="*70 + "\n\n")
        ranked_s = sorted(metrics, key=lambda m: m['S_shannon'], reverse=True)
        ranked_t = sorted(metrics, key=lambda m: m['T_eff'], reverse=True)

        f.write("RANKING POR ENTROPIA DE SHANNON\n")
        f.write("-"*70 + "\n")
        f.write(f"{'#':>3}  {'ID':<5}  {'S_Shannon':>10}  {'T_eff':>8}  {'S_Boltz':>8}  Descripcion\n")
        for i, m in enumerate(ranked_s, 1):
            f.write(f"{i:>3}  {m['id']:<5}  {m['S_shannon']:>10.4f}  "
                    f"{m['T_eff']:>8.4f}  {m['S_boltzmann']:>8.4f}  {m['desc']}\n")
        f.write("\n")

        f.write("RANKING POR TEMPERATURA EFECTIVA\n")
        f.write("-"*70 + "\n")
        f.write(f"{'#':>3}  {'ID':<5}  {'T_eff':>10}  {'S_Shannon':>10}  Descripcion\n")
        for i, m in enumerate(ranked_t, 1):
            f.write(f"{i:>3}  {m['id']:<5}  {m['T_eff']:>10.4f}  "
                    f"{m['S_shannon']:>10.4f}  {m['desc']}\n")
    print(f"Ranking guardado: {path}")


# ============================================================================
# MAIN
# ============================================================================

def main():
    print("\n" + "="*62)
    print("  ANALISIS ISING + ENTROPIA — PATRONES DE APERTURA DE GO")
    print("="*62)

    for M in (1, 2):
        print(f"\n--- Kernel Manhattan-{M} ---")
        data = analyze_patterns(manhattan_distance=M)
        ids = data['ids']
        metrics = data['metrics']
        boards = data['boards']
        emaps = data['energy_maps']

        # Extraer vectores
        s_shannon = [m['S_shannon'] for m in metrics]
        t_eff     = [m['T_eff'] for m in metrics]
        s_boltz   = [m['S_boltzmann'] for m in metrics]

        # Imprimir ranking
        print_ranking(metrics, sort_by='S_shannon')

        # Grafico 1: Grilla de mapas de energia
        grid_path = os.path.join(RESULTS_DIR, f'energy_grid_M{M}.png')  # 01_patrones
        plot_energy_grid(
            boards=boards,
            energy_maps=emaps,
            names=ids,
            metrics=metrics,
            cols=5,
            output_path=grid_path,
        )
        plt.close('all')

        # Grafico 2: Comparacion de entropia y temperatura
        cmp_path = os.path.join(ENTROPY_DIR, f'entropy_compare_M{M}.png')
        plot_entropy_comparison(
            names=ids,
            s_shannon=s_shannon,
            t_eff=t_eff,
            s_boltzmann=s_boltz,
            title=f"Patrones de Go — Entropia y Temperatura (Manhattan-{M})",
            output_path=cmp_path,
        )
        plt.close('all')

        # Ranking a archivo
        rank_path = os.path.join(REPORTS_DIR, f'ranking_M{M}.txt')
        save_ranking(metrics, rank_path)

    print("\nListo. Resultados en:", RESULTS_DIR)


if __name__ == '__main__':
    main()
