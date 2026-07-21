"""
analyze_results.py
===================
Analiza el dataset "futures" (crudo + campos de H) para responder dos
preguntas:

1. Por Hamiltoniano, ¿cuánto correlaciona su campo con el territorio
   real de KataGo (label_pct_black)? Agregado por grupo (frente1 vs
   tardios).

2. ¿El campo de H aporta algo POR ENCIMA de la geometría simple
   (distancia a la piedra más cercana de cada color)? Se mide con
   correlación parcial y con R² incremental (regresión lineal:
   geometría sola vs. geometría + H_field_mean), usando un F-test
   para la significancia del incremento.
"""

import sys
import re
import json
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.stats import pearsonr, f as f_dist
from sklearn.linear_model import LinearRegression

HERE = Path(__file__).resolve().parent

GEOM_COLS = ["dist_to_nearest_black", "dist_to_nearest_white", "dist_to_edge"]


def partial_correlation(x: pd.Series, y: pd.Series, controls: pd.DataFrame) -> float:
    """Correlación parcial de x con y, controlando linealmente por
    las columnas de `controls` (residuales de ambas regresiones)."""
    reg_x = LinearRegression().fit(controls, x)
    res_x = x - reg_x.predict(controls)
    reg_y = LinearRegression().fit(controls, y)
    res_y = y - reg_y.predict(controls)
    r, _ = pearsonr(res_x, res_y)
    return r


def incremental_r2_test(df: pd.DataFrame, h_field_col: str, label_col: str,
                         geom_cols: list) -> dict:
    """Compara R² de un modelo solo-geometría vs geometría+H_field.
    F-test para el incremento (Δdf=1)."""
    y = df[label_col].values
    X_base = df[geom_cols].values
    X_full = df[geom_cols + [h_field_col]].values
    n = len(y)

    reg_base = LinearRegression().fit(X_base, y)
    r2_base = reg_base.score(X_base, y)
    reg_full = LinearRegression().fit(X_full, y)
    r2_full = reg_full.score(X_full, y)

    p_base = X_base.shape[1]
    p_full = X_full.shape[1]
    rss_base = np.sum((y - reg_base.predict(X_base)) ** 2)
    rss_full = np.sum((y - reg_full.predict(X_full)) ** 2)

    df1 = p_full - p_base
    df2 = n - p_full - 1
    if rss_full <= 0 or df2 <= 0:
        f_stat, p_value = float("nan"), float("nan")
    else:
        f_stat = ((rss_base - rss_full) / df1) / (rss_full / df2)
        p_value = float(1 - f_dist.cdf(f_stat, df1, df2))

    return {
        "r2_base": r2_base, "r2_full": r2_full,
        "delta_r2": r2_full - r2_base,
        "f_stat": f_stat, "p_value": p_value,
    }


def weighted_incremental_r2_test(df: pd.DataFrame, h_field_col: str, label_col: str,
                                  geom_cols: list, weight_col: str) -> dict:
    """Igual que incremental_r2_test pero pondera cada fila por
    1/ownership_stdev_mean^2 (menos peso a moyos donde KataGo mismo
    está incierto) — separa "el modelo falla" de "KataGo no está seguro ahí"."""
    y = df[label_col].values
    X_base = df[geom_cols].values
    X_full = df[geom_cols + [h_field_col]].values
    n = len(y)
    w = 1.0 / np.clip(df[weight_col].values, 1e-6, None) ** 2

    reg_base = LinearRegression().fit(X_base, y, sample_weight=w)
    r2_base = reg_base.score(X_base, y, sample_weight=w)
    reg_full = LinearRegression().fit(X_full, y, sample_weight=w)
    r2_full = reg_full.score(X_full, y, sample_weight=w)

    p_base = X_base.shape[1]
    p_full = X_full.shape[1]
    rss_base = np.sum(w * (y - reg_base.predict(X_base)) ** 2)
    rss_full = np.sum(w * (y - reg_full.predict(X_full)) ** 2)

    df1 = p_full - p_base
    df2 = n - p_full - 1
    if rss_full <= 0 or df2 <= 0:
        f_stat, p_value = float("nan"), float("nan")
    else:
        f_stat = ((rss_base - rss_full) / df1) / (rss_full / df2)
        p_value = float(1 - f_dist.cdf(f_stat, df1, df2))

    return {
        "r2_base": r2_base, "r2_full": r2_full,
        "delta_r2": r2_full - r2_base,
        "f_stat": f_stat, "p_value": p_value,
    }


def cluster_robust_f_test(df: pd.DataFrame, h_field_col: str, label_col: str,
                           geom_cols: list, cluster_col: str = "game") -> dict:
    """Corrige la pseudo-replicacion: agrupa filas por partida (cluster_col)
    y bootstrapea por partida (no por fila) para obtener un intervalo de
    confianza de delta_r2 que respeta que las filas de una misma partida
    no son independientes."""
    rng = np.random.default_rng(0)
    games = df[cluster_col].unique()
    n_games = len(games)
    n_boot = 500
    deltas = []
    for _ in range(n_boot):
        sample_games = rng.choice(games, size=n_games, replace=True)
        parts = [df[df[cluster_col] == g] for g in sample_games]
        boot_df = pd.concat(parts, ignore_index=True)
        try:
            inc = incremental_r2_test(boot_df, h_field_col, label_col, geom_cols)
            deltas.append(inc["delta_r2"])
        except Exception:
            continue
    deltas = np.array(deltas)
    return {
        "delta_r2_mean": float(np.mean(deltas)),
        "delta_r2_std": float(np.std(deltas)),
        "ci_lo": float(np.percentile(deltas, 2.5)),
        "ci_hi": float(np.percentile(deltas, 97.5)),
        "n_games": n_games, "n_boot": len(deltas),
    }


def analyze(parquet_path: str, manifest_path: str):
    df = pd.read_parquet(parquet_path)
    manifest = json.loads(Path(manifest_path).read_text(encoding="utf-8"))
    hamiltonians = manifest["hamiltonians"]

    print(f"Dataset: {len(df)} filas, {df['game'].nunique()} partidas, "
          f"{len(hamiltonians)} Hamiltonianos\n")

    controls = df[GEOM_COLS]

    print("=" * 100)
    print(f"{'H_id':<14}{'grupo':<10}{'r_simple':>10}{'r_parcial':>11}"
          f"{'R2_base':>9}{'R2_full':>9}{'DeltaR2':>8}{'p(F-test)':>11}")
    print("=" * 100)

    rows_summary = []
    for h_id, info in hamiltonians.items():
        group = info["group"]
        field_col = f"{h_id}_H_field_mean"
        if field_col not in df.columns:
            continue

        r_simple, _ = pearsonr(df[field_col], df["label_pct_black"])
        r_partial = partial_correlation(df[field_col], df["label_pct_black"], controls)
        inc = incremental_r2_test(df, field_col, "label_pct_black", GEOM_COLS)

        print(f"{h_id:<14}{group:<10}{r_simple:>10.3f}{r_partial:>11.3f}"
              f"{inc['r2_base']:>9.3f}{inc['r2_full']:>9.3f}"
              f"{inc['delta_r2']:>8.3f}{inc['p_value']:>11.2e}")

        rows_summary.append({
            "h_id": h_id, "group": group, "r_simple": r_simple,
            "r_partial": r_partial, **inc,
        })

    summary = pd.DataFrame(rows_summary)
    print("\n" + "=" * 60)
    print("PROMEDIO POR GRUPO")
    print("=" * 60)
    g = summary.groupby("group")[["r_simple", "r_partial", "delta_r2"]].agg(["mean", "std"])
    print(g)

    return summary


if __name__ == "__main__":
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--parquet", type=str, default="futures_expanded")
    args = ap.parse_args()
    out_dir = HERE.parent / "output"
    analyze(str(out_dir / f"{args.parquet}.parquet"),
            str(out_dir / f"{args.parquet}_manifest.json"))
