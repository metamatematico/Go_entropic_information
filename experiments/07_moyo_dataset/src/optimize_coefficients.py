"""
optimize_coefficients.py
=========================
Optimización directa de coeficientes contra el cache de posiciones
reales (ver cache_positions.py) — en vez de generar candidatos al
azar y esperar que uno sea bueno, busca directamente los coeficientes
que maximizan Delta R^2 contra el territorio real de KataGo.

La función objetivo reutiliza exactamente las mismas piezas ya
verificadas: relaxation_field (features.py) y incremental_r2_test
(analyze_results.py).
"""

import sys
import pickle
import time
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.optimize import differential_evolution

HERE = Path(__file__).resolve().parent
PROJDIR = HERE.parent.parent.parent

sys.path.insert(0, str(PROJDIR / "src"))
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(PROJDIR / "experiments" / "06_hamiltonian_families" / "src"))

from families import Hamiltonian, COEF_NAMES, COEF_RANGES   # noqa: E402
from features import relaxation_field, region_field_features  # noqa: E402
from analyze_results import incremental_r2_test, GEOM_COLS    # noqa: E402


def load_cache(name: str = "position_cache") -> list:
    path = HERE.parent / "output" / f"{name}.pkl"
    with open(path, "rb") as f:
        return pickle.load(f)


def cache_to_dataframe(cache: list, h: "Hamiltonian" = None,
                       radius: int = 1, n_sweeps: int = 4,
                       region_key: str = "moyos") -> pd.DataFrame:
    """Construye el DataFrame de filas (una por region) a partir del cache.
    region_key: 'moyos' (default) o 'territory' -- selecciona la categoria.
    Si h no es None, agrega las columnas H_field_mean / H_field_std."""
    rows = []
    for entry in cache:
        field = None
        if h is not None:
            field = relaxation_field(h, entry["board"], radius=radius, n_sweeps=n_sweeps)
        for m in entry.get(region_key, []):
            row = {
                "game": entry["game"], "move_number": entry["move"],
                "n_total_moves": entry.get("n_total_moves"),
                "phase_frac": entry.get("phase_frac"),
                "label_pct_black": m["pct_black"],
                "score_lead": entry.get("score_lead"),
                "score_stdev": entry.get("score_stdev"),
                "winrate": entry.get("winrate"),
                "ownership_stdev_mean": m.get("ownership_stdev_mean"),
                "policy_mass": m.get("policy_mass"),
                "n_top_moves_in_region": m.get("n_top_moves_in_region"),
            }
            row.update(m["board_feats"])
            if field is not None:
                rf = region_field_features(field, m["points"])
                row["H_field_mean"] = rf["H_field_mean"]
                row["H_field_std"] = rf["H_field_std"]
            rows.append(row)
    return pd.DataFrame(rows)


def make_objective(cache: list, template: str, radius: int, n_sweeps: int = 4):
    """Cierra sobre el cache y devuelve una funcion objetivo(coef_vector) -> -DeltaR2."""
    names = COEF_NAMES[template]

    def objective(x: np.ndarray) -> float:
        coefs = dict(zip(names, x))
        try:
            h = Hamiltonian(template, coefs)
            df = cache_to_dataframe(cache, h, radius=radius, n_sweeps=n_sweeps)
            inc = incremental_r2_test(df, "H_field_mean", "label_pct_black", GEOM_COLS)
            delta_r2 = inc["delta_r2"]
            if np.isnan(delta_r2):
                return 0.0
            return -delta_r2
        except Exception:
            return 0.0
    return objective


def optimize(template: str, radius: int, cache_name: str = "position_cache",
             n_sweeps: int = 4, maxiter: int = 15, popsize: int = 8,
             seed_coefs: list = None, seed: int = 42) -> dict:
    cache = load_cache(cache_name)
    names = COEF_NAMES[template]
    bounds = COEF_RANGES[template]
    if bounds is None:
        raise ValueError(
            f"La plantilla '{template}' no tiene rangos de coeficientes definidos "
            f"(COEF_RANGES[{template!r}] es None) — probablemente es una referencia "
            f"fija (como 'h_m1'). Usa 'sparse_cubic' para optimizar la misma forma "
            f"de monomios con coeficientes libres.")

    objective = make_objective(cache, template, radius, n_sweeps)

    init = "latinhypercube"
    if seed_coefs:
        pop = [ [c[n] for n in names] for c in seed_coefs ]
        # completar la poblacion con muestras aleatorias hasta popsize*len(bounds)
        rng = np.random.default_rng(seed)
        target_size = popsize * len(bounds)
        while len(pop) < target_size:
            pop.append([rng.uniform(lo, hi) for lo, hi in bounds])
        init = np.array(pop[:target_size])

    t0 = time.time()
    result = differential_evolution(
        objective, bounds, maxiter=maxiter, popsize=popsize,
        init=init, seed=seed, tol=1e-4, polish=True, disp=True,
        workers=1,  # KataGo/GPU no es thread-safe entre evaluaciones concurrentes
    )
    elapsed = time.time() - t0

    best_coefs = dict(zip(names, result.x))
    return {
        "template": template, "radius": radius,
        "best_coefs": best_coefs, "best_delta_r2": -result.fun,
        "n_evaluations": result.nfev, "elapsed_s": elapsed,
        "success": result.success,
    }


def make_objective_4d(cache: list, radius: int, n_sweeps: int = 4):
    """Fase B: busca directamente en las 4 dimensiones efectivas
    (Sigma_a, Sigma_b, b12, Sigma_c) que el Experimento 08 demostro que
    son las unicas que importan para relaxation_field, en vez de los 7
    parametros crudos de cubic_mixed. Reparte cada suma de forma
    simetrica (a1=a2=Sigma_a/2, etc.) -- por la identidad de Klein
    (P_{--} y P_{-+} se cancelan exactamente en H(s,q)+H(q,s)), CUALQUIER
    reparto de una suma dada produce el mismo Delta R^2, asi que esta
    eleccion no pierde generalidad para este objetivo."""
    def objective(x: np.ndarray) -> float:
        sa, sb, b12, sc = x
        coefs = {"a1": sa / 2, "a2": sa / 2,
                  "b11": sb / 2, "b12": b12, "b22": sb / 2,
                  "c112": sc / 2, "c122": sc / 2}
        try:
            h = Hamiltonian("cubic_mixed", coefs)
            df = cache_to_dataframe(cache, h, radius=radius, n_sweeps=n_sweeps)
            inc = incremental_r2_test(df, "H_field_mean", "label_pct_black", GEOM_COLS)
            delta_r2 = inc["delta_r2"]
            if np.isnan(delta_r2):
                return 0.0
            return -delta_r2
        except Exception:
            return 0.0
    return objective


# Cotas de las 4 combinaciones efectivas, derivadas de COEF_RANGES["cubic_mixed"]:
# Sigma_a = a1+a2 con a1,a2 en [-3,3] -> [-6,6]; igual para Sigma_b.
# b12 ya es un solo coeficiente -> [-3,3] sin cambio.
# Sigma_c = c112+c122 con c112,c122 en [-1,1] -> [-2,2].
BOUNDS_4D = [(-6, 6), (-6, 6), (-3, 3), (-2, 2)]


def optimize_4d(radius: int, cache_name: str = "position_cache",
                 n_sweeps: int = 4, maxiter: int = 15, popsize: int = 8,
                 seed_points: list = None, seed: int = 42,
                 bounds: list = None) -> dict:
    """Fase B completa: optimiza (Sigma_a, Sigma_b, b12, Sigma_c) sobre
    la familia cubic_mixed completa (incluye los terminos b que
    sparse_cubic/Fase A nunca exploro)."""
    cache = load_cache(cache_name)
    objective = make_objective_4d(cache, radius, n_sweeps)
    bounds = bounds or BOUNDS_4D

    init = "latinhypercube"
    if seed_points:
        pop = [list(p) for p in seed_points]
        rng = np.random.default_rng(seed)
        target_size = popsize * len(bounds)
        while len(pop) < target_size:
            pop.append([rng.uniform(lo, hi) for lo, hi in bounds])
        init = np.array(pop[:target_size])

    t0 = time.time()
    result = differential_evolution(
        objective, bounds, maxiter=maxiter, popsize=popsize,
        init=init, seed=seed, tol=1e-4, polish=True, disp=True,
        workers=1,
    )
    elapsed = time.time() - t0

    sa, sb, b12, sc = result.x
    best_coefs_4d = {"Sigma_a": sa, "Sigma_b": sb, "b12": b12, "Sigma_c": sc}
    best_coefs_raw = {"a1": sa / 2, "a2": sa / 2, "b11": sb / 2, "b12": b12,
                       "b22": sb / 2, "c112": sc / 2, "c122": sc / 2}
    return {
        "template": "cubic_mixed", "radius": radius,
        "best_coefs_4d": best_coefs_4d, "best_coefs_raw": best_coefs_raw,
        "best_delta_r2": -result.fun,
        "n_evaluations": result.nfev, "elapsed_s": elapsed,
        "success": result.success,
    }


if __name__ == "__main__":
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--template", type=str, default="sparse_cubic")
    ap.add_argument("--radius", type=int, default=9)
    ap.add_argument("--cache_name", type=str, default="position_cache")
    ap.add_argument("--maxiter", type=int, default=15)
    ap.add_argument("--popsize", type=int, default=8)
    args = ap.parse_args()

    res = optimize(args.template, args.radius, args.cache_name,
                   maxiter=args.maxiter, popsize=args.popsize)
    print("\n=== RESULTADO ===")
    print(f"Mejor Delta R2: {res['best_delta_r2']:.4f}")
    print(f"Coeficientes: {res['best_coefs']}")
    print(f"Evaluaciones: {res['n_evaluations']}  Tiempo: {res['elapsed_s']:.0f}s")
