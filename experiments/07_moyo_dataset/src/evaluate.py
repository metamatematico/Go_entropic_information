"""
evaluate.py
============
Construcción del DataFrame de evaluación con VARIOS Hamiltonianos y varios
predictores de campo a la vez, sobre un mismo cache.

`optimize_coefficients.cache_to_dataframe` evalúa un solo Hamiltoniano con
un solo predictor (F). Aquí se generaliza a la forma que necesitan tanto el
bootstrap pareado (Ruta A) como la matriz de transferencia entre categorías
(Ruta B): todas las columnas de predictor viven en el MISMO DataFrame, sobre
las MISMAS filas, que es la condición para que las comparaciones sean pareadas.

Predictores disponibles por Hamiltoniano:
  F       campo relajado crudo                  -> "<nombre>__F"
  F_eq    parte equivariante, 1/2 (F(B)-F(-B))  -> "<nombre>__F_eq"
  F_bias  parte de sesgo,     1/2 (F(B)+F(-B))  -> "<nombre>__F_bias"

Pedir F_eq o F_bias cuesta el doble de cómputo (relaja B y -B); pedir ambos
no cuesta más que pedir uno, porque salen de la misma pareja de relajaciones.
"""

import sys
from pathlib import Path
from typing import Dict, Sequence

import pandas as pd

HERE = Path(__file__).resolve().parent
PROJDIR = HERE.parent.parent.parent

sys.path.insert(0, str(PROJDIR / "src"))
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(PROJDIR / "experiments" / "06_hamiltonian_families" / "src"))

from families import Hamiltonian                                    # noqa: E402
from features import (relaxation_field, equivariant_fields,         # noqa: E402
                       region_field_features)

# Los cuatro Hamiltonianos con nombre del proyecto.
# H_OPT_A: Fase A (sparse_cubic, 4 coefs). H_OPT_B: Fase B (cubic_mixed, 4 dims
# efectivas repartidas simétricamente) — coeficientes de output/fase_b_result.json.
REFERENCE_HAMILTONIANS: Dict[str, Hamiltonian] = {
    "H_M1": Hamiltonian("h_m1", {"a1": 1.0, "a2": 2.0,
                                  "c112": -1.0, "c122": -1.0}),
    "Alvarado": Hamiltonian("quadratic", {"a1": 0.0, "a2": 0.0, "b11": 0.0,
                                           "b12": 1.0, "b22": 0.0}),
    "H_OPT_A": Hamiltonian("sparse_cubic", {"a1": -0.8404, "a2": -0.1608,
                                             "c112": 0.9828, "c122": -0.1221}),
    "H_OPT_B": Hamiltonian("cubic_mixed", {
        "a1": -0.12413054697841827, "a2": -0.12413054697841827,
        "b11": 1.8643239093374513, "b12": -3.0,
        "b22": 1.8643239093374513,
        "c112": -0.4830045413846782, "c122": -0.4830045413846782}),
}

# Claves de región por categoría. Ojo: en `cache_early20` las regiones de
# fuseki se guardaron bajo la clave "moyos" (es el mismo detector por bandas
# de ownership, aplicado a jugadas tempranas), y "joseki" son las 4 esquinas
# fijas, geometría pura, independiente de ownership.
REGION_KEYS = {
    "moyo": "moyos",
    "territorio": "territory",
    "fuseki": "moyos",      # sobre cache_early20
    "joseki": "joseki",     # sobre cache_early20
    "neutral": "neutral",   # aún no poblada por el pipeline
}


def build_dataframe(cache: list, hamiltonians: Dict[str, Hamiltonian],
                     radius: int = 9, n_sweeps: int = 8,
                     region_key: str = "moyos",
                     predictors: Sequence[str] = ("F",),
                     temperature: float = 1.0) -> pd.DataFrame:
    """Una fila por región, con una columna por (Hamiltoniano, predictor).

    Las columnas geométricas y la etiqueta salen del cache tal cual, así que
    la base de comparación es idéntica para todos los candidatos — que es lo
    que hace legítimo comparar sus Delta R^2 entre sí.
    """
    predictors = tuple(predictors)
    desconocidos = set(predictors) - {"F", "F_eq", "F_bias"}
    if desconocidos:
        raise ValueError(f"Predictores no reconocidos: {sorted(desconocidos)}")
    necesita_par = bool({"F_eq", "F_bias"} & set(predictors))

    rows = []
    for entry in cache:
        regions = entry.get(region_key, [])
        if not regions:
            continue

        campos: Dict[str, Dict[str, "object"]] = {}
        for nombre, h in hamiltonians.items():
            if necesita_par:
                campos[nombre] = equivariant_fields(
                    h, entry["board"], radius=radius, n_sweeps=n_sweeps,
                    temperature=temperature)
            else:
                campos[nombre] = {"F": relaxation_field(
                    h, entry["board"], radius=radius, n_sweeps=n_sweeps,
                    temperature=temperature)}

        for m in regions:
            row = {
                "game": entry["game"], "move_number": entry["move"],
                "n_total_moves": entry.get("n_total_moves"),
                "phase_frac": entry.get("phase_frac"),
                "label_pct_black": m["pct_black"],
                "region_kind": m.get("kind"),
                "ownership_stdev_mean": m.get("ownership_stdev_mean"),
            }
            row.update(m["board_feats"])
            for nombre in hamiltonians:
                for p in predictors:
                    rf = region_field_features(campos[nombre][p], m["points"],
                                                prefix=f"{nombre}__{p}")
                    row[f"{nombre}__{p}_mean"] = rf[f"{nombre}__{p}_mean"]
            rows.append(row)

    return pd.DataFrame(rows)


def predictor_columns(hamiltonians, predictor: str = "F") -> list:
    """Nombres de columna del predictor pedido, en el orden de `hamiltonians`."""
    return [f"{n}__{predictor}_mean" for n in hamiltonians]
