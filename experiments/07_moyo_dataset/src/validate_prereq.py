"""
validate_prereq.py
===================
Puerta de entrada a la Ruta B: verifica que la implementación de F_eq,
F_bias y beta(H) en el repositorio reproduce las cifras publicadas antes
de usarlas para decidir cualquier cosa.

Las mediciones de la Parte IV se hicieron con una reimplementación externa
al repositorio. Este script las rehace con el código del repo. Si algún
número no cuadra, el problema es la implementación de aquí — no se sigue
adelante hasta cerrarlo.

Referencias a reproducir (informe 07+08, Parte IV):
  T1  beta en tablero vacío   H_M1 -0.66 | Alvarado 0.00 | H_OPT_A +0.51 | H_OPT_B +0.40
  T2  equivariancia           Alvarado ~1e-16 (precisión de máquina); los otros ~1.1-1.4
  T3  descomposición de Klein suma exacta = H; normas por pieza
  T4  Delta R^2 (moyo, r=9, 8 barridos, cache_full20_cats, 864 regiones)
        H_M1     F 0.298 | F_eq 0.357 | F_bias 0.001
        H_OPT_B  F 0.453 | F_eq 0.457 | F_bias 0.001

Uso:  python validate_prereq.py [--n-boot 500] [--quick]
"""

import argparse
import json
import pickle
import sys
import time
from pathlib import Path

import numpy as np

# La consola de Windows usa cp1252 por defecto y revienta con acentos.
try:
    sys.stdout.reconfigure(encoding="utf-8")
except (AttributeError, OSError):
    pass

HERE = Path(__file__).resolve().parent
PROJDIR = HERE.parent.parent.parent
OUTDIR = HERE.parent / "output"

sys.path.insert(0, str(PROJDIR / "src"))
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(PROJDIR / "experiments" / "06_hamiltonian_families" / "src"))
sys.path.insert(0, str(PROJDIR / "experiments" / "08_teoria_invariantes" / "src"))

from features import relaxation_field, beta_empty_board       # noqa: E402
from evaluate import REFERENCE_HAMILTONIANS, build_dataframe  # noqa: E402
from bootstrap import paired_bootstrap, format_report         # noqa: E402
import klein                                                   # noqa: E402

RADIUS, N_SWEEPS = 9, 8

# La Parte IV reportó "864 regiones" sin nombrar el cache, y su Cuadro 8 achacó
# la diferencia con el 0.421 del informe interno a "detalles de la ruta de
# evaluación". La ruta es el cache: de los cuatro caches de 20 partidas, solo
# `cache_full20` (115 posiciones, 864 moyos) reproduce sus cuatro cifras.
#   cache_full20       115 pos, 864 moyos -> H_M1 0.2981 | H_OPT_B 0.4534  (Parte IV)
#   cache_full20_rich  113 pos, 864 moyos -> H_M1 0.2967 | H_OPT_B 0.4394
#   cache_full20_cats  120 pos, 872 moyos -> H_M1 0.2774 | H_OPT_B 0.4210  (informe interno)
# La brecha entre rutas (0.03 en H_OPT_B) es del mismo orden que el optimismo
# por traslape búsqueda-validación (0.06), así que fijar el cache es una
# decisión de preregistro, no un detalle.
CACHE_FIDELIDAD = "cache_full20"
CACHE_PROTOCOLO = "cache_full20_cats"   # el que usa la Ruta B: trae territorio

ESPERADO_BETA = {"H_M1": -0.66, "Alvarado": 0.00, "H_OPT_A": 0.51, "H_OPT_B": 0.40}
ESPERADO_DR2 = {
    ("H_M1", "F"): 0.298, ("H_M1", "F_eq"): 0.357, ("H_M1", "F_bias"): 0.001,
    ("H_OPT_B", "F"): 0.453, ("H_OPT_B", "F_eq"): 0.457,
    ("H_OPT_B", "F_bias"): 0.001,
}


def _ok(valor, esperado, tol):
    return "OK " if abs(valor - esperado) <= tol else "REVISAR"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--n-boot", type=int, default=500)
    ap.add_argument("--quick", action="store_true",
                    help="usa solo las primeras 20 posiciones (humo, no validación)")
    args = ap.parse_args()

    resultados = {}

    # ── T1: beta en tablero vacío ────────────────────────────────────────────
    print("=" * 78)
    print("T1  beta(H): campo relajado medio en tablero VACÍO (r=1, 15 barridos, 9x9)")
    print("=" * 78)
    print(f"{'Hamiltoniano':<12} {'beta':>9} {'esperado':>10} {'-sign(Sa)':>11}  {'':>7}")
    betas = {}
    for nombre, h in REFERENCE_HAMILTONIANS.items():
        b = beta_empty_board(h)
        betas[nombre] = b
        eff = klein.effective_coefficients(h.coefs)
        signo_pred = -np.sign(eff["Sigma_a"])
        coincide = "si" if (b == 0 and signo_pred == 0) or np.sign(b) == signo_pred else "NO"
        print(f"{nombre:<12} {b:>+9.4f} {ESPERADO_BETA[nombre]:>+10.2f} "
              f"{coincide:>11}  {_ok(b, ESPERADO_BETA[nombre], 0.02):>7}")
    resultados["T1_beta"] = betas

    # ── T2: equivariancia ────────────────────────────────────────────────────
    print()
    print("=" * 78)
    print("T2  equivariancia: max |F(-B) + F(B)| sobre un tablero real")
    print("=" * 78)
    cache = pickle.load(open(OUTDIR / f"{CACHE_FIDELIDAD}.pkl", "rb"))
    board = cache[0]["board"]
    print(f"{'Hamiltoniano':<12} {'max|F(-B)+F(B)|':>18}  {'P+-(H)=0':>10}  veredicto")
    equiv = {}
    for nombre, h in REFERENCE_HAMILTONIANS.items():
        fp = relaxation_field(h, board, radius=RADIUS, n_sweeps=N_SWEEPS)
        fn = relaxation_field(h, -board, radius=RADIUS, n_sweeps=N_SWEEPS)
        m = float(np.max(np.abs(fp + fn)))
        equiv[nombre] = m
        sin_sesgo = not klein.has_color_bias(h.coefs)
        veredicto = ("equivariante" if m < 1e-10 else "sesgado")
        consistente = "" if (m < 1e-10) == sin_sesgo else "  <-- INCONSISTENTE"
        print(f"{nombre:<12} {m:>18.3e}  {str(sin_sesgo):>10}  "
              f"{veredicto}{consistente}")
    resultados["T2_equivariancia"] = equiv

    # ── T3: descomposición de Klein ──────────────────────────────────────────
    print()
    print("=" * 78)
    print("T3  descomposición de Klein (verificación simbólica con sympy)")
    print("=" * 78)
    x, y = klein.x, klein.y
    a1, a2, b11, b12, b22, c112, c122 = __import__("sympy").symbols(
        "a1 a2 b11 b12 b22 c112 c122", real=True)
    H_gen = (a1 * x + a2 * y + b11 * x**2 + b12 * x * y + b22 * y**2
             + c112 * x**2 * y + c122 * x * y**2)
    print(f"  cubic_mixed genérico: suma de proyecciones == H  ->  "
          f"{klein.verify_decomposition(H_gen)}")
    print(f"  sigma y tau conmutan                            ->  "
          f"{klein.commutes(H_gen)}")
    print(f"\n{'Hamiltoniano':<12} {'|P++|':>8} {'|P+-|':>8} {'|P-+|':>8} {'|P--|':>8}"
          f"   (solo las 2 primeras son visibles)")
    normas = {}
    for nombre, h in REFERENCE_HAMILTONIANS.items():
        n = klein.piece_norms(h.expr)
        normas[nombre] = n
        print(f"{nombre:<12} {n['P++']:>8.2f} {n['P+-']:>8.2f} "
              f"{n['P-+']:>8.2f} {n['P--']:>8.2f}")
    resultados["T3_normas_klein"] = normas

    # ── T4: Delta R^2 con F, F_eq y F_bias ───────────────────────────────────
    print()
    print("=" * 78)
    print(f"T4  Delta R^2 sobre moyo (r={RADIUS}, {N_SWEEPS} barridos, "
          f"{CACHE_FIDELIDAD})")
    print("=" * 78)
    if args.quick:
        cache = cache[:20]
        print("  [--quick] solo 20 posiciones: prueba de humo, NO validación\n")

    hams = {n: REFERENCE_HAMILTONIANS[n] for n in ("H_M1", "H_OPT_B")}
    t0 = time.time()
    df = build_dataframe(cache, hams, radius=RADIUS, n_sweeps=N_SWEEPS,
                          region_key="moyos",
                          predictors=("F", "F_eq", "F_bias"))
    print(f"  {len(df)} regiones, {df['game'].nunique()} partidas "
          f"({time.time() - t0:.0f}s de campo)\n")

    cols = [f"{n}__{p}_mean" for n in hams for p in ("F", "F_eq", "F_bias")]
    res = paired_bootstrap(df, cols, n_boot=args.n_boot, seed=1)
    print(format_report(res))

    print(f"\n  {'columna':<26} {'medido':>9} {'publicado':>10}  {'':>7}")
    for n in hams:
        for p in ("F", "F_eq", "F_bias"):
            col = f"{n}__{p}_mean"
            medido = res["marginal"][col]["delta_r2"]
            esp = ESPERADO_DR2[(n, p)]
            print(f"  {col:<26} {medido:>9.4f} {esp:>10.3f}  "
                  f"{_ok(medido, esp, 0.02):>7}")
    resultados["T4_delta_r2"] = res

    out = OUTDIR / "validate_prereq.json"
    with open(out, "w", encoding="utf-8") as f:
        json.dump(resultados, f, ensure_ascii=False, indent=2, default=float)
    print(f"\nGuardado en: {out}")


if __name__ == "__main__":
    main()
