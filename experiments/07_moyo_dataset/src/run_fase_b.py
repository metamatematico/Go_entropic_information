"""
run_fase_b.py
==============
Fase B: optimiza directamente en las 4 dimensiones efectivas
(Sigma_a, Sigma_b, b12, Sigma_c) sobre la familia completa cubic_mixed
-- a diferencia de Fase A, que solo exploro sparse_cubic (sin terminos
b11/b12/b22). La garantia teorica de que basta buscar en 4 dimensiones,
en vez de 7, viene del Experimento 08 (grupo de Klein).

Mismo protocolo que Fase A: busca sobre el cache chico (6 partidas,
mas rapido para iterar), despues valida el optimo encontrado sobre el
cache completo de 20 partidas antes de aceptar cualquier conclusion.
"""
import sys
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

from optimize_coefficients import optimize_4d, load_cache, cache_to_dataframe  # noqa: E402
from families import Hamiltonian  # noqa: E402
from analyze_results import incremental_r2_test, GEOM_COLS  # noqa: E402

RADIUS = 9
N_SWEEPS = 4

# Puntos conocidos, mapeados a (Sigma_a, Sigma_b, b12, Sigma_c) para
# sembrar la poblacion inicial (misma logica que Fase A con H_M1/H_0106/H_0115).
SEED_POINTS = [
    [3.0, 0.0, 0.0, -2.0],        # H_M1 (a1=1,a2=2,c112=-1,c122=-1)
    [-1.0012, 0.0, 0.0, 0.8607],  # H_OPT_A (Fase A)
    [0.0, 0.0, 1.0, 0.0],         # Alvarado (b12=1, resto 0)
]

print("=== Fase B: busqueda en el cache chico (6 partidas) ===")
res = optimize_4d(radius=RADIUS, cache_name="cache_faseA", n_sweeps=N_SWEEPS,
                   maxiter=15, popsize=8, seed_points=SEED_POINTS, seed=42)

print(f"\nMejor Delta R2 (cache chico): {res['best_delta_r2']:.4f}")
print(f"Coeficientes efectivos: {res['best_coefs_4d']}")
print(f"Coeficientes crudos: {res['best_coefs_raw']}")
print(f"Evaluaciones: {res['n_evaluations']}  Tiempo: {res['elapsed_s']:.0f}s  success={res['success']}")

print("\n=== Validando sobre las 20 partidas completas (cache_full20_cats) ===")
h_optb = Hamiltonian("cubic_mixed", res["best_coefs_raw"])
cache20 = load_cache("cache_full20_cats")
df20 = cache_to_dataframe(cache20, h_optb, radius=RADIUS, n_sweeps=8, region_key="moyos")
inc20 = incremental_r2_test(df20, "H_field_mean", "label_pct_black", GEOM_COLS)
print(f"Delta R2 sobre 20 partidas (n_sweeps=8): {inc20['delta_r2']:.4f}  p={inc20['p_value']:.2e}")

df20_4 = cache_to_dataframe(cache20, h_optb, radius=RADIUS, n_sweeps=4, region_key="moyos")
inc20_4 = incremental_r2_test(df20_4, "H_field_mean", "label_pct_black", GEOM_COLS)
print(f"Delta R2 sobre 20 partidas (n_sweeps=4, comparable a cache chico): {inc20_4['delta_r2']:.4f}")

out = {
    "fase_b_small_cache": res,
    "fase_b_validation_20games_sweeps8": {"delta_r2": inc20["delta_r2"], "p_value": inc20["p_value"]},
    "fase_b_validation_20games_sweeps4": {"delta_r2": inc20_4["delta_r2"], "p_value": inc20_4["p_value"]},
}
out_path = HERE.parent / "output" / "fase_b_result.json"
with open(out_path, "w", encoding="utf-8") as f:
    json.dump(out, f, ensure_ascii=False, indent=2, default=float)
print(f"\nGuardado en: {out_path}")
