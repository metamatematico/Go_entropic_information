"""
audit_ruta_b.py
================
Las tres auditorías obligatorias del §7 del preregistro, que se corren ANTES
del análisis principal porque sus resultados pueden invalidar el uso de una
categoría entera.

A1  ¿La base geométrica de joseki está degenerada? Las regiones joseki son las
    4 esquinas fijas del tablero, definidas por geometría pura y no por
    ownership: si las tres columnas geométricas son casi constantes entre
    ellas, el modelo base no discrimina y el Delta R^2 de joseki mide contra
    un rival artificialmente débil — no comparable con el de moyo.
    Criterio congelado: si R^2(geometría sola) < 0.05, la categoría se reporta
    con advertencia y queda fuera de H3 y H4.

A2  ¿Cuánta señal hay que capturar en cada categoría? Se reporta el R^2 de la
    base geométrica sola, porque una ganancia de 0.11 sobre una base de 0.67
    (territorio) no significa lo mismo que sobre una de 0.31 (moyo).

A3  Verificación de la reparametrización, por categoría. H_M1 con sus
    coeficientes crudos (a1=1, a2=2, c112=-1, c122=-1) y H_M1 mapeado a
    (Sigma_a, Sigma_b, b12, Sigma_c) = (3, 0, 0, -2) deben dar EXACTAMENTE el
    mismo campo, por la identidad de Klein. Si falla en alguna categoría, esa
    búsqueda no se lanza.

Uso:  python audit_ruta_b.py
"""

import json
import pickle
import sys
from pathlib import Path

import numpy as np

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

from families import Hamiltonian                       # noqa: E402
from evaluate import build_dataframe                   # noqa: E402
from bootstrap import _r2, delta_r2, GEOM_COLS         # noqa: E402

# §2 del preregistro: categorías, caches y claves de región.
CATEGORIAS = {
    "moyo":       ("cache_full20_cats", "moyos"),
    "territorio": ("cache_full20_cats", "territory"),
    "fuseki":     ("cache_early20", "moyos"),
    "joseki":     ("cache_early20", "joseki"),
}

# §3 del preregistro: las 6 partidas de búsqueda de Fases A y B.
SEARCH_GAMES = {
    "31mn-gokifu-20200319-Gu_Lingyi-Tao_Xinran.sgf",
    "31pr-gokifu-20200323-Li_Xiaoxi-Lu_Jia.sgf",
    "31ps-gokifu-20200323-Tang_Yi-Wang_Shuang.sgf",
    "31pt-gokifu-20200324-Wang_Chenxing-Tang_Yi.sgf",
    "31pu-gokifu-20200324-Lu_Jia-Cao_Youyin.sgf",
    "31pv-gokifu-20200324-Chen_Yiming-Li_Xiaoxi.sgf",
}

RADIUS = 9
N_SWEEPS_BUSQUEDA = 4
UMBRAL_DEGENERACION = 0.05

# H_M1 por las dos rutas: coeficientes crudos, y reparametrizado a las 4
# dimensiones efectivas con reparto simétrico. Deben dar el mismo campo.
H_M1_CRUDO = Hamiltonian("h_m1", {"a1": 1.0, "a2": 2.0,
                                   "c112": -1.0, "c122": -1.0})
H_M1_REPARAM = Hamiltonian("cubic_mixed", {
    "a1": 1.5, "a2": 1.5, "b11": 0.0, "b12": 0.0, "b22": 0.0,
    "c112": -1.0, "c122": -1.0})


def _cargar(cache_name, region_key, solo_busqueda=None):
    cache = pickle.load(open(OUTDIR / f"{cache_name}.pkl", "rb"))
    if solo_busqueda is True:
        cache = [e for e in cache if e["game"] in SEARCH_GAMES]
    elif solo_busqueda is False:
        cache = [e for e in cache if e["game"] not in SEARCH_GAMES]
    return [e for e in cache if e.get(region_key)]


def _filas_geometria(cache, region_key):
    """Solo geometría y etiqueta — sin calcular ningún campo."""
    X, y = [], []
    for entry in cache:
        for m in entry.get(region_key, []):
            bf = m["board_feats"]
            X.append([bf[c] for c in GEOM_COLS])
            y.append(m["pct_black"])
    return np.array(X, dtype=float), np.array(y, dtype=float)


def main():
    resultados = {}

    # ── A1 + A2 ──────────────────────────────────────────────────────────────
    print("=" * 84)
    print("A1 + A2  Fuerza de la base geométrica por categoría (sin campo)")
    print("=" * 84)
    print(f"{'categoría':<12} {'conj.':<9} {'n reg':>6} {'R2 geom':>9} "
          f"{'CV(dist_borde)':>15} {'CV(dist_negra)':>15}  veredicto")

    a12 = {}
    for cat, (cache_name, key) in CATEGORIAS.items():
        a12[cat] = {}
        for etiqueta, filtro in (("hold-out", False), ("completo", None)):
            cache = _cargar(cache_name, key, filtro)
            X, y = _filas_geometria(cache, key)
            r2 = _r2(y, X)
            # Coeficiente de variación de dos columnas geométricas: mide si la
            # base tiene algo que variar entre regiones de esta categoría.
            cv = [float(np.std(X[:, i]) / abs(np.mean(X[:, i])))
                  if np.mean(X[:, i]) else float("nan") for i in range(X.shape[1])]
            degenerada = r2 < UMBRAL_DEGENERACION
            veredicto = "DEGENERADA" if degenerada else "ok"
            print(f"{cat:<12} {etiqueta:<9} {len(y):>6} {r2:>9.4f} "
                  f"{cv[2]:>15.3f} {cv[0]:>15.3f}  {veredicto}")
            a12[cat][etiqueta] = {"n": int(len(y)), "r2_geom": float(r2),
                                   "cv_dist_edge": cv[2], "cv_dist_black": cv[0],
                                   "degenerada": bool(degenerada)}
        print()
    resultados["A1_A2_base_geometrica"] = a12

    # ── A3 ───────────────────────────────────────────────────────────────────
    print("=" * 84)
    print(f"A3  Reparametrización: H_M1 crudo vs (Sa,Sb,b12,Sc)=(3,0,0,-2)")
    print(f"    (r={RADIUS}, {N_SWEEPS_BUSQUEDA} barridos, F_eq, conjunto de búsqueda)")
    print("=" * 84)
    print(f"{'categoría':<12} {'n reg':>6} {'dR2 crudo':>11} {'dR2 reparam':>13} "
          f"{'|dif|':>10}  veredicto")

    hams = {"crudo": H_M1_CRUDO, "reparam": H_M1_REPARAM}
    a3 = {}
    for cat, (cache_name, key) in CATEGORIAS.items():
        cache = _cargar(cache_name, key, True)
        df = build_dataframe(cache, hams, radius=RADIUS,
                             n_sweeps=N_SWEEPS_BUSQUEDA, region_key=key,
                             predictors=("F_eq",))
        y = df["label_pct_black"].to_numpy(float)
        Xg = df[GEOM_COLS].to_numpy(float)
        d_crudo = delta_r2(y, Xg, df["crudo__F_eq_mean"].to_numpy(float))
        d_rep = delta_r2(y, Xg, df["reparam__F_eq_mean"].to_numpy(float))
        dif = abs(d_crudo - d_rep)
        ok = dif < 1e-9
        print(f"{cat:<12} {len(df):>6} {d_crudo:>11.6f} {d_rep:>13.6f} "
              f"{dif:>10.2e}  {'OK' if ok else 'FALLA -> no lanzar'}")
        a3[cat] = {"n": int(len(df)), "delta_r2_crudo": float(d_crudo),
                   "delta_r2_reparam": float(d_rep), "dif": float(dif),
                   "ok": bool(ok)}
    resultados["A3_reparametrizacion"] = a3

    # ── Veredicto ────────────────────────────────────────────────────────────
    print()
    print("=" * 84)
    print("VEREDICTO")
    print("=" * 84)
    degeneradas = [c for c, v in a12.items() if v["completo"]["degenerada"]]
    fallan = [c for c, v in a3.items() if not v["ok"]]
    if degeneradas:
        print(f"  A1: base geométrica degenerada en {degeneradas} -> reportar con "
              f"advertencia, fuera de H3 y H4")
    else:
        print(f"  A1: ninguna categoría por debajo de R2={UMBRAL_DEGENERACION}")
    print(f"  A3: {'todas las categorías pasan' if not fallan else f'FALLAN {fallan}'}")
    listas = [c for c in CATEGORIAS if c not in fallan]
    print(f"\n  Categorías habilitadas para búsqueda: {listas}")

    out = OUTDIR / "audit_ruta_b.json"
    with open(out, "w", encoding="utf-8") as f:
        json.dump(resultados, f, ensure_ascii=False, indent=2, default=float)
    print(f"\nGuardado en: {out}")


if __name__ == "__main__":
    main()
