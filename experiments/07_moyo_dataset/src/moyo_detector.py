"""
moyo_detector.py
================
Detección de moyos a partir del mapa `ownership` de KataGo.

Metodología (sin estándar establecido en la literatura — ver nota en
el manifest del dataset): agrupamos por flood-fill los puntos vacíos
conectados y clasificamos cada región según la confianza promedio de
`ownership`:

  |ownership| > 0.85              -> territorio asentado (no es moyo)
  0.15 <= |ownership| <= 0.85      -> candidato a moyo
  |ownership| < 0.15               -> neutral / dame

Una región de moyo se reporta con su etiqueta: porcentaje de la región
que corresponde a negro, derivado directamente de ownership promedio.
"""

from typing import List, Dict, Any, Set, Tuple
import numpy as np

SETTLED_THRESHOLD = 0.85
NEUTRAL_THRESHOLD = 0.15
MIN_MOYO_SIZE = 4   # puntos mínimos para considerar una región como moyo relevante

_DIRS = [(0, 1), (0, -1), (1, 0), (-1, 0)]


def ownership_to_grid(ownership: List[float], board_size: int = 19) -> np.ndarray:
    """KataGo devuelve ownership como lista plana, fila por fila desde
    arriba (row 0 = fila superior), columna de izquierda a derecha —
    coincide con la convención (fila, columna) SGF ya usada en el resto
    del proyecto."""
    arr = np.array(ownership, dtype=float).reshape(board_size, board_size)
    return arr


def _empty_points(board: np.ndarray) -> Set[Tuple[int, int]]:
    rows, cols = np.where(board == 0)
    return set(zip(rows.tolist(), cols.tolist()))


def _categorize(mean_own: float) -> str:
    """Categoría de un punto individual según su ownership.
    5 bandas para poder separar zonas de negro/blanco/neutral incluso
    cuando el tablero abierto las conecta físicamente."""
    if mean_own > SETTLED_THRESHOLD:
        return "territory_black"
    if mean_own > NEUTRAL_THRESHOLD:
        return "moyo_black"
    if mean_own >= -NEUTRAL_THRESHOLD:
        return "neutral"
    if mean_own >= -SETTLED_THRESHOLD:
        return "moyo_white"
    return "territory_white"


def _flood_fill_regions(empties: Set[Tuple[int, int]], own_grid: np.ndarray,
                         board_size: int) -> List[Set[Tuple[int, int]]]:
    """Agrupa puntos vacíos conectados (4-vecindad) en regiones, pero SOLO
    conecta vecinos que caen en la misma categoría de ownership. Sin esto,
    en posiciones tempranas todo el tablero vacío es una sola componente
    conexa y el promedio da 'neutral' aunque partes leales a negro/blanco
    ya sean distinguibles."""
    categories = {p: _categorize(own_grid[p]) for p in empties}
    remaining = set(empties)
    regions = []
    while remaining:
        start = next(iter(remaining))
        cat = categories[start]
        stack = [start]
        region = set()
        while stack:
            p = stack.pop()
            if p in region or p not in remaining:
                continue
            region.add(p)
            r, c = p
            for dr, dc in _DIRS:
                nr, nc = r + dr, c + dc
                np_ = (nr, nc)
                if (0 <= nr < board_size and 0 <= nc < board_size
                        and np_ in remaining and np_ not in region
                        and categories[np_] == cat):
                    stack.append(np_)
        remaining -= region
        regions.append(region)
    return regions


def detect_moyos(board: np.ndarray, ownership: List[float],
                  board_size: int = 19) -> List[Dict[str, Any]]:
    """
    board: array (board_size, board_size) con -1 negro, 0 vacío, +1 blanco.
    ownership: lista plana de KataGo (perspectiva: +1 negro, -1 blanco
               si currentPlayer es black; se normaliza aquí a +1=negro
               siempre asumiendo que ownership ya viene en esa convención
               fija por posición, no relativa al jugador en turno).

    Devuelve lista de dicts: {points, kind, pct_black, size, mean_ownership}
    con kind ∈ {'territory','moyo','neutral'}.
    """
    own_grid = ownership_to_grid(ownership, board_size)
    empties = _empty_points(board)
    regions = _flood_fill_regions(empties, own_grid, board_size)

    results = []
    for region in regions:
        vals = [own_grid[r, c] for (r, c) in region]
        mean_own = float(np.mean(vals))
        cat = _categorize(mean_own)
        kind = ("territory" if cat.startswith("territory")
                else "moyo" if cat.startswith("moyo") else "neutral")

        pct_black = (mean_own + 1.0) / 2.0 * 100.0

        results.append({
            "points": sorted(region),
            "kind": kind,
            "size": len(region),
            "mean_ownership": mean_own,
            "pct_black": pct_black,
        })
    return results


def filter_moyos(regions: List[Dict[str, Any]],
                  min_size: int = MIN_MOYO_SIZE) -> List[Dict[str, Any]]:
    """Filtra solo las regiones clasificadas como 'moyo' con tamaño mínimo."""
    return [r for r in regions if r["kind"] == "moyo" and r["size"] >= min_size]
