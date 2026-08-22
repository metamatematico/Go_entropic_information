"""
bootstrap.py
=============
Inferencia por remuestreo de PARTIDAS COMPLETAS para Delta R^2.

Dos correcciones distintas, y conviene no confundirlas:

1. Bootstrap por partida (ya usado en el proyecto). Las regiones de una
   misma partida no son independientes — comparten tablero, estilo y fase.
   Tratar cada región como una observación independiente es pseudo-replicación
   y hunde artificialmente los p-valores. La corrección es remuestrear las
   20 partidas completas, no las 864 filas. El ancho resultante (~0.13-0.15
   con 20 partidas) es el techo de resolución real del experimento.

2. Bootstrap PAREADO (nuevo aquí). Comparar dos Hamiltonianos mirando si
   sus IC marginales se traslapan es el test equivocado, y es conservador
   de más: todos los candidatos se evalúan sobre LAS MISMAS partidas, así
   que la comparación es pareada. Dos IC del 95% pueden traslaparse
   ampliamente mientras la diferencia es claramente distinta de cero,
   porque la variabilidad común entre partidas (unas partidas son más
   fáciles de predecir que otras, para todos los Hamiltonianos a la vez)
   se cancela al restar dentro de cada réplica.

   Concretamente: en cada réplica se remuestrean partidas UNA vez y se
   calcula Delta R^2 de ambos candidatos sobre ESE MISMO remuestreo; el
   IC se construye sobre la diferencia. Eso es lo que resuelve empates que
   los IC marginales dejan indecidibles, sin una sola partida nueva.
"""

from typing import Dict, Sequence

import numpy as np
import pandas as pd

GEOM_COLS = ["dist_to_nearest_black", "dist_to_nearest_white", "dist_to_edge"]


def _r2(y: np.ndarray, X: np.ndarray) -> float:
    """R^2 de una regresión lineal con intercepto, por mínimos cuadrados.
    Equivale a LinearRegression().fit(X, y).score(X, y) de sklearn, que es
    lo que usa `analyze_results.incremental_r2_test`."""
    A = np.column_stack([np.ones(len(y)), X])
    coef, *_ = np.linalg.lstsq(A, y, rcond=None)
    resid = y - A @ coef
    ss_res = float(resid @ resid)
    ss_tot = float(((y - y.mean()) ** 2).sum())
    if ss_tot <= 0:
        return float("nan")
    return 1.0 - ss_res / ss_tot


def delta_r2(y: np.ndarray, X_geom: np.ndarray, h_col: np.ndarray) -> float:
    """Ganancia de R^2 del predictor del Hamiltoniano sobre la base geométrica."""
    return _r2(y, np.column_stack([X_geom, h_col])) - _r2(y, X_geom)


def paired_bootstrap(df: pd.DataFrame, h_cols: Sequence[str],
                      label_col: str = "label_pct_black",
                      geom_cols: Sequence[str] = None,
                      n_boot: int = 500, seed: int = 1,
                      game_col: str = "game") -> Dict[str, dict]:
    """Delta R^2 con IC 95% por partida para cada predictor de `h_cols`, MÁS
    el IC de todas las diferencias por pares — calculadas sobre el mismo
    remuestreo, que es lo que las vuelve pareadas.

    `h_cols` son columnas del mismo DataFrame: para comparar dos Hamiltonianos
    se evalúan ambos sobre el mismo cache y se agregan como dos columnas
    (p. ej. "H_M1_field_mean" y "H_OPT_B_field_mean"). Para comparar F contra
    F_eq del mismo Hamiltoniano, igual: dos columnas, misma fila.

    Devuelve, por predictor: punto y IC 95%. Por par (i, j): la diferencia
    punto, su IC 95%, y un p-valor bootstrap de dos colas — la fracción de
    réplicas que cruzan el cero, duplicada. Un IC de la diferencia que NO
    contiene el cero es evidencia de que un candidato supera al otro, aunque
    sus IC marginales se traslapen.
    """
    geom_cols = list(geom_cols or GEOM_COLS)
    h_cols = list(h_cols)

    faltantes = [c for c in list(h_cols) + geom_cols + [label_col, game_col]
                 if c not in df.columns]
    if faltantes:
        raise KeyError(f"Faltan columnas en el DataFrame: {faltantes}")

    y_all = df[label_col].to_numpy(dtype=float)
    X_all = df[geom_cols].to_numpy(dtype=float)
    H_all = {c: df[c].to_numpy(dtype=float) for c in h_cols}

    games = df[game_col].to_numpy()
    unique_games = np.unique(games)
    idx_by_game = {g: np.flatnonzero(games == g) for g in unique_games}

    # Punto estimado sobre la muestra completa (sin remuestrear).
    point = {c: delta_r2(y_all, X_all, H_all[c]) for c in h_cols}

    rng = np.random.default_rng(seed)
    reps = {c: np.empty(n_boot) for c in h_cols}

    for b in range(n_boot):
        pick = rng.choice(unique_games, size=len(unique_games), replace=True)
        rows = np.concatenate([idx_by_game[g] for g in pick])
        y_b, X_b = y_all[rows], X_all[rows]
        # Misma selección de filas para TODOS los predictores: eso es lo que
        # hace que las diferencias de abajo sean pareadas.
        for c in h_cols:
            reps[c][b] = delta_r2(y_b, X_b, H_all[c][rows])

    out: Dict[str, dict] = {"marginal": {}, "paired": {}, "n_boot": n_boot,
                             "n_games": int(len(unique_games)),
                             "n_rows": int(len(df))}

    for c in h_cols:
        v = reps[c][~np.isnan(reps[c])]
        out["marginal"][c] = {
            "delta_r2": float(point[c]),
            "ci_lo": float(np.percentile(v, 2.5)),
            "ci_hi": float(np.percentile(v, 97.5)),
            "boot_mean": float(np.mean(v)),
        }

    for i, ca in enumerate(h_cols):
        for cb in h_cols[i + 1:]:
            d = reps[ca] - reps[cb]
            d = d[~np.isnan(d)]
            frac_neg = float(np.mean(d < 0))
            frac_pos = float(np.mean(d > 0))
            out["paired"][f"{ca} - {cb}"] = {
                "diff": float(point[ca] - point[cb]),
                "ci_lo": float(np.percentile(d, 2.5)),
                "ci_hi": float(np.percentile(d, 97.5)),
                "p_boot": float(min(1.0, 2 * min(frac_neg, frac_pos))),
                "excluye_cero": bool(np.percentile(d, 2.5) > 0
                                      or np.percentile(d, 97.5) < 0),
            }

    return out


def format_report(res: Dict[str, dict]) -> str:
    """Salida legible: marginales primero, después las diferencias pareadas."""
    lines = [f"n = {res['n_games']} partidas, {res['n_rows']} regiones, "
             f"{res['n_boot']} replicas bootstrap", ""]
    lines.append(f"{'predictor':<34} {'dR2':>8}  {'IC 95% (marginal)':>22}")
    lines.append("-" * 68)
    for c, m in res["marginal"].items():
        ci = f"[{m['ci_lo']:.3f}, {m['ci_hi']:.3f}]"
        lines.append(f"{c:<34} {m['delta_r2']:>8.4f}  {ci:>22}")
    if res["paired"]:
        lines += ["", f"{'diferencia pareada':<34} {'dif':>8}  "
                      f"{'IC 95% (pareado)':>22} {'p':>8}  concluye"]
        lines.append("-" * 88)
        for k, d in res["paired"].items():
            ci = f"[{d['ci_lo']:.3f}, {d['ci_hi']:.3f}]"
            veredicto = "DISTINTO de 0" if d["excluye_cero"] else "indecidible"
            lines.append(f"{k:<34} {d['diff']:>8.4f}  {ci:>22} "
                          f"{d['p_boot']:>8.4f}  {veredicto}")
    return "\n".join(lines)
