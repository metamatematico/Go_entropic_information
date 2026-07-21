"""
early_regions.py
=================
Lógica de detección de MOMENTO (fuseki: jugadas tempranas) y de
REGIÓN (joseki: esquinas fijas del tablero) — categorías 5 y 4 de la
taxonomía de Go, complementarias a moyo/territorio (que son
ownership-based, sin importar la posición en el tablero).

Diferencia clave con moyo/territorio (moyo_detector.py):
  - moyo/territorio: región definida por BANDA DE OWNERSHIP,
    en cualquier momento de la partida ya muestreado (15%-90%).
  - joseki: región definida por GEOMETRÍA FIJA (una esquina),
    sin importar el ownership.
  - fuseki: mismo mecanismo que moyo/territorio (ownership-based,
    todo el tablero), pero en un MOMENTO distinto — el rango
    3%-15% que sample_move_numbers() excluye a propósito.
"""
from typing import List, Dict, Any
import numpy as np

from moyo_detector import ownership_to_grid

CORNER_SIZE = 6  # lado del cuadrado de esquina, en puntos


def sample_early_move_numbers(n_total_moves: int, n_samples: int = 4) -> list:
    """Jugadas equiespaciadas entre el 3% y el 15% de la partida --
    exactamente el rango que sample_move_numbers() excluye a propósito.
    Esto SÍ es fuseki real (apertura), a diferencia del "temprano"
    relativo de la Sección de fase de partida (que vive dentro del
    15%-90% ya muestreado)."""
    if n_total_moves < 30:
        return []
    lo, hi = int(0.03 * n_total_moves), int(0.15 * n_total_moves)
    if hi <= lo:
        return []
    return sorted(set(np.linspace(lo, hi, n_samples).astype(int).tolist()))


def corner_regions(board_size: int = 19, size: int = CORNER_SIZE) -> Dict[str, list]:
    """4 regiones fijas (esquinas), independientes de ownership.
    Devuelve dict nombre_esquina -> lista de (fila, columna)."""
    corners = {
        "sup_izq": (range(0, size), range(0, size)),
        "sup_der": (range(0, size), range(board_size - size, board_size)),
        "inf_izq": (range(board_size - size, board_size), range(0, size)),
        "inf_der": (range(board_size - size, board_size), range(board_size - size, board_size)),
    }
    return {name: [(r, c) for r in rows for c in cols]
            for name, (rows, cols) in corners.items()}


def joseki_regions(board: np.ndarray, ownership: list, board_size: int = 19,
                    size: int = CORNER_SIZE) -> List[Dict[str, Any]]:
    """Para cada esquina, intersecta la geometría fija con los puntos
    vacíos reales de esa posición -- reutiliza ownership_to_grid()
    de moyo_detector.py, solo restringido espacialmente a la esquina
    en vez de por banda de ownership."""
    own_grid = ownership_to_grid(ownership, board_size)
    corners = corner_regions(board_size, size)
    results = []
    for name, pts in corners.items():
        empty_pts = [(r, c) for (r, c) in pts if board[r, c] == 0]
        if len(empty_pts) < 3:
            continue
        vals = [own_grid[r, c] for (r, c) in empty_pts]
        mean_own = float(np.mean(vals))
        pct_black = (mean_own + 1.0) / 2.0 * 100.0
        results.append({
            "points": sorted(empty_pts),
            "kind": "joseki",
            "corner": name,
            "size": len(empty_pts),
            "mean_ownership": mean_own,
            "pct_black": pct_black,
        })
    return results
