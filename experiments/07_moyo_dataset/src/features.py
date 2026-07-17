"""
features.py
===========
Dos familias de features por posición/moyo:

1. board_features(): features crudas de tablero (densidad de piedras,
   distancia a piedras de cada color, tamaño/geometría del moyo).
2. relaxation_field() + topology_features(): features derivadas del
   Hamiltoniano H — el campo de "energía propagada" sobre todo el
   tablero (relajación tipo campo medio, usando H como acoplamiento
   local) y descriptores topológicos de la variedad Gamma(H).

El campo de relajación es una elección de modelado (no hay una única
forma "correcta" de llevar una energía local a un campo global) — ver
docstring de relaxation_field().
"""

import sys
from pathlib import Path

import numpy as np
from typing import Dict, Any, List, Tuple

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent.parent / "src"))
from go_ising_classical import IsingGoConfig  # noqa: E402  (fuente unica de coef(d)=1/d^2)

_DIRS = [(0, 1), (0, -1), (1, 0), (-1, 0)]


def manhattan_kernel_offsets(radius: int) -> List[Tuple[int, int, float]]:
    """(dx, dy, coeficiente) para todo punto a distancia Manhattan
    1..radius del centro, usando la misma ley 1/d^2 de go_ising_classical.
    radius=1 reproduce exactamente los 4 vecinos cardinales originales."""
    offsets = []
    for d in range(1, radius + 1):
        coef = IsingGoConfig.INTERACTION_COEFFS.get(d, 0.0)
        for dx in range(-d, d + 1):
            dy_abs = d - abs(dx)
            for dy in ({dy_abs, -dy_abs} if dy_abs else {0}):
                offsets.append((dx, dy, coef))
    return offsets


def board_features(board: np.ndarray, region_points: list,
                    move_number: int, board_size: int = 19) -> Dict[str, Any]:
    """Features crudas para una región (moyo) dada. Distancia Manhattan
    (L1), consistente con la conectividad real del tablero (libertades,
    capturas, kernel de interaccion) — no euclidiana."""
    rs = [p[0] for p in region_points]
    cs = [p[1] for p in region_points]
    centroid_r, centroid_c = float(np.mean(rs)), float(np.mean(cs))

    black_pts = np.argwhere(board == -1)
    white_pts = np.argwhere(board == 1)

    def min_dist(pts):
        if len(pts) == 0:
            return float(board_size)
        d = np.abs(pts[:, 0] - centroid_r) + np.abs(pts[:, 1] - centroid_c)
        return float(d.min())

    dist_edge = min(centroid_r, centroid_c, board_size - 1 - centroid_r,
                     board_size - 1 - centroid_c)

    return {
        "region_size": len(region_points),
        "centroid_row": centroid_r,
        "centroid_col": centroid_c,
        "dist_to_nearest_black": min_dist(black_pts),
        "dist_to_nearest_white": min_dist(white_pts),
        "dist_to_edge": float(dist_edge),
        "move_number": move_number,
        "n_black_stones": int((board == -1).sum()),
        "n_white_stones": int((board == 1).sum()),
    }


_S_GRID = np.linspace(-1.0, 1.0, 41)


def relaxation_field(h, board: np.ndarray, radius: int = 1, n_sweeps: int = 15,
                      temperature: float = 1.0,
                      board_size: int = 19) -> np.ndarray:
    """
    Campo de "energía propagada" sobre todo el tablero usando H como
    acoplamiento local (relajación tipo campo medio / Gauss-Seidel),
    con un kernel de interacción de radio Manhattan configurable
    (radius=1 = solo 4 vecinos cardinales; radius=9 = hasta 180 puntos,
    ponderados por 1/d^2 como en go_ising_classical.py).

    Cada punto vacío p se actualiza con el valor ESPERADO de spin bajo
    una distribución de Boltzmann a temperatura T sobre su energía
    local con TODOS los puntos del kernel, ya colocados/actualizados:

        E_local(s) = sum_q coef(d_q) * [ H(s, F[q]) + H(F[q], s) ]
        F[p] = E_{s~Z(T)}[s] = sum_s s * exp(-E_local(s)/T) / Z(T)

    donde Z(T) = sum_s exp(-E_local(s)/T), la misma función de
    partición usada para un solo par, ahora evaluada localmente en
    cada punto y propagada por el tablero. Vectorizado sobre vecinos
    Y sobre la rejilla de spin de prueba (broadcasting numpy) — sin
    esto, radios grandes (hasta 180 vecinos) serían intratables en
    Python puro.

    NOTA: un primer intento usó argmin duro (minimize_scalar) en vez
    de este promedio térmico, pero como H es un polinomio de bajo
    grado, el argmin casi siempre cae exactamente en la frontera
    s=±1 sin importar el contexto — el campo resultante era binario
    y, para algunos Hamiltonianos, literalmente constante. El promedio
    de Boltzmann evita ese colapso y da valores continuos genuinos,
    comparables a `ownership` de KataGo.

    Las piedras son condiciones de frontera fijas (F = -1 o +1, no se
    actualizan). Se hacen n_sweeps barridos completos del tablero.
    """
    F = board.astype(float).copy()
    empty_mask = (board == 0)
    empty_points = list(zip(*np.where(empty_mask)))
    kernel = manhattan_kernel_offsets(radius)

    for _ in range(n_sweeps):
        for (r, c) in empty_points:
            nv, cf = [], []
            for dr, dc, coef in kernel:
                nr, nc = r + dr, c + dc
                if 0 <= nr < board_size and 0 <= nc < board_size:
                    nv.append(F[nr, nc])
                    cf.append(coef)
            if not nv:
                continue

            NV = np.asarray(nv)[None, :]     # (1, K)
            CF = np.asarray(cf)[None, :]     # (1, K)
            S = _S_GRID[:, None]             # (41, 1)  -> broadcast a (41, K)

            e_matrix = CF * (h(S, NV) + h(NV, S))   # (41, K)
            energies = e_matrix.sum(axis=1)          # (41,)
            energies -= energies.min()  # estabilidad numerica del exp
            weights = np.exp(-energies / temperature)
            F[r, c] = float(np.sum(_S_GRID * weights) / np.sum(weights))
    return F


def region_field_features(field: np.ndarray, region_points: list) -> Dict[str, float]:
    """Resume el campo H sobre una región: media y desviación estándar."""
    vals = [field[r, c] for (r, c) in region_points]
    return {
        "H_field_mean": float(np.mean(vals)),
        "H_field_std": float(np.std(vals)),
    }


def topology_features(alg: Dict[str, Any]) -> Dict[str, Any]:
    """Descriptores topológicos globales de Gamma(H), a partir del dict
    que devuelve src/algebra.py::analyze() (experimento 06)."""
    crit_vals = alg.get("critical_values", [])
    return {
        "n_A1": alg.get("n_nodes_A1", 0),
        "n_critical_points": len(crit_vals),
        "min_crit_separation": alg.get("min_crit_separation", float("inf")),
        "mean_critical_value": float(np.mean(crit_vals)) if crit_vals else 0.0,
    }
