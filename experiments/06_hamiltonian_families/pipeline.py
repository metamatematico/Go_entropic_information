#!/usr/bin/env python3
"""
pipeline.py
===========
CLI batch runner: La familia de polinomios Go y sus variedades asociadas.

Uso
---
  python pipeline.py                          # configuración por defecto
  python pipeline.py --template odd_cubic --n 100
  python pipeline.py --template h_m1         # solo H_M1 de referencia
  python pipeline.py --top 10                # resumen de los mejores ya catalogados
  python pipeline.py --all-templates         # corre todas las plantillas
"""

import argparse
import os
import sys
import time
import yaml
import json
import numpy as np
from pathlib import Path
from tqdm import tqdm

# ── Rutas ──────────────────────────────────────────────────────────────────────
HERE    = Path(__file__).resolve().parent
PROJDIR = HERE.parent.parent   # raíz del proyecto
sys.path.insert(0, str(HERE))

from src.families      import generate_random, generate_grid, reference_hamiltonians, TEMPLATES
from src.algebra       import analyze
from src.topology      import compute_persistence
from src.filter_candidates import filter_candidate, robustness_test
from src.dynamics      import validate_on_sgf
from src.catalog       import Catalog


def load_cfg(path: str = None) -> dict:
    default = str(HERE / "config.yaml")
    with open(path or default) as f:
        return yaml.safe_load(f)


def process_one(h, cfg: dict, catalog: Catalog,
                sgf_dir: str, is_ref: bool = False) -> dict:
    """Analiza un Hamiltoniano y lo añade al catálogo."""
    alg_cfg = cfg.get("analysis", {})
    tda_cfg = cfg.get("tda", {})
    fil_cfg = cfg.get("filter", {})
    val_cfg = cfg.get("validation", {})

    # 1. Álgebra
    alg = analyze(h, alg_cfg)

    # 2. TDA
    tda = compute_persistence(
        h,
        L=alg_cfg.get("box_L", 2.0),
        N=alg_cfg.get("grid_size", 150),
        tau=tda_cfg.get("tau", 0.15),
        n_thresh=tda_cfg.get("n_thresholds", 80),
    )

    # 3. Filtro
    filt = filter_candidate(alg, tda, fil_cfg)
    filt["tda_score"] = filt.get("tda_score", 0.0)

    # 4. Robustez (solo si pasa el filtro, para ahorrar tiempo)
    if filt["passes"]:
        rob = robustness_test(h, filt["tda_score"], {**alg_cfg, **fil_cfg, **tda_cfg})
        filt["robustness"] = rob["robustness"]
    else:
        filt["robustness"] = 0.0

    # 5. Validación dinámica
    val = validate_on_sgf(
        h, alg,
        sgf_dir=sgf_dir,
        n_games=val_cfg.get("n_games", 5),
    )

    # 6. Registro en catálogo
    eid = catalog.add(h, alg, tda, filt, val, is_reference=is_ref)
    catalog.save()
    return {"id": eid, "passes": filt["passes"],
            "tda_score": filt["tda_score"]}


def run_pipeline(cfg: dict, template: str, n_samples: int,
                 sample_mode: str):
    out_cfg = cfg.get("output", {})
    cat_path = str(HERE / out_cfg.get("catalog_path", "output/catalog.json"))
    sgf_dir  = str(PROJDIR / cfg["validation"].get("sgf_dir",
                   "data/sgf_partidas"))

    catalog = Catalog(cat_path)

    # ── Referencias ────────────────────────────────────────────────────────────
    print("── Procesando referencias (H_M1, Alvarado) ─────────────────────────")
    for h_ref in reference_hamiltonians():
        r = process_one(h_ref, cfg, catalog, sgf_dir, is_ref=True)
        print(f"  {r['id']}  passes={r['passes']}  tda={r['tda_score']:.3f}")

    # ── Familia candidata ──────────────────────────────────────────────────────
    if template == "h_m1":
        print("Solo referencia H_M1 procesada.")
        _print_summary(catalog, cfg)
        return

    print(f"\n── Generando {n_samples} candidatos ({template}, {sample_mode}) ──")
    if sample_mode == "grid":
        steps = max(3, int(np.sqrt(n_samples)))
        hams  = generate_grid(template, steps, cfg.get("family", {}))
    else:
        hams  = generate_random(template, n_samples, cfg.get("family", {}),
                                seed=cfg["family"].get("seed", 42))

    passed = 0
    for h in tqdm(hams, desc="Analizando"):
        try:
            r = process_one(h, cfg, catalog, sgf_dir)
            if r["passes"]:
                passed += 1
        except Exception as ex:
            print(f"\n  [WARN] {ex}")

    print(f"\n  Candidatos que pasan el filtro: {passed}/{len(hams)}")
    _print_summary(catalog, cfg)


def _print_summary(catalog: Catalog, cfg: dict):
    top_n = cfg.get("output", {}).get("top_n", 10)
    top   = catalog.top_n(top_n)
    print(f"\n══ TOP {len(top)} candidatos (por score total) ══════════════════════")
    print(f"{'ID':>8}  {'template':>14}  {'H1_max':>8}  {'rob':>6}  {'imp':>8}  {'total':>7}")
    print("─"*60)
    for e in top:
        sc = e["scores"]
        val = e["validation"]
        print(f"  {e['id']:>6}  {e['template']:>14}  "
              f"{e['tda'].get('max_h1_lifetime',0):8.3f}  "
              f"{sc.get('robustness',0):6.3f}  "
              f"{(val.get('improvement') or 0):8.4f}  "
              f"{sc.get('total',0):7.4f}")
    rep_path = HERE / cfg["output"].get("reports_dir","output/reports") / "executive_summary.md"
    _write_summary_md(catalog, cfg, str(rep_path))
    print(f"\n  Resumen ejecutivo → {rep_path}")


def _write_summary_md(catalog: Catalog, cfg: dict, path: str):
    import datetime
    top_n = cfg.get("output", {}).get("top_n", 10)
    top   = catalog.top_n(top_n)
    df    = catalog.to_dataframe()
    n_total    = len(df)
    n_pass     = int(df["passes"].sum()) if "passes" in df.columns else 0
    n_ref      = int(df["is_reference"].sum()) if "is_reference" in df.columns else 0
    templates  = df["template"].value_counts().to_dict() if not df.empty else {}
    today      = str(datetime.date.today())
    os.makedirs(os.path.dirname(path), exist_ok=True)

    def _row(e):
        sc  = e["scores"]
        alg = e["algebraic"]
        val = e["validation"]
        imp = val.get("improvement") or 0.0
        pv  = val.get("p_value")
        pv_str = f"{pv:.3f}" if pv is not None else "—"
        crit_sep = alg.get("min_crit_separation", 0)
        crit_sep_str = f"{crit_sep:.3f}" if isinstance(crit_sep, float) and crit_sep != float("inf") else "∞"
        return (
            f"| {e['id']} | {e['template']} | `{e['expression'][:38]}` |"
            f" {alg.get('n_nodes_A1','?')} |"
            f" {crit_sep_str} |"
            f" {e['tda'].get('well_depth',0):.1f} |"
            f" {sc.get('robustness',0):.3f} |"
            f" {imp:+.4f} | {pv_str} |"
            f" **{sc.get('total',0):.4f}** |"
        )

    criteria_cfg = cfg.get("filter", {})
    tau1   = criteria_cfg.get("tau1",       0.20)
    dE     = criteria_cfg.get("delta_E",    0.50)
    dcrit  = criteria_cfg.get("delta_crit", 0.30)

    tmpl_lines = "\n".join(
        f"  - `{t}`: {n} muestras" for t, n in templates.items()
    )

    lines = [
        "# La familia de polinomios Go y sus variedades asociadas",
        "## Informe ejecutivo — Fibración de Milnor en estrategia de Go",
        "",
        f"*Generado automáticamente · {today}*",
        f"*Catálogo: {n_total} Hamiltonianos ({n_ref} referencias + {n_total-n_ref} candidatos) · {n_pass} pasan el filtro*",
        "",
        "---",
        "",
        "## Resumen de la búsqueda",
        "",
        f"Plantillas exploradas:",
        tmpl_lines,
        "",
        f"| Métrica              | Valor  |",
        f"|----------------------|--------|",
        f"| Total analizados     | {n_total}  |",
        f"| Pasan el filtro      | {n_pass}   |",
        f"| Tasa de éxito        | {100*n_pass/max(n_total,1):.1f} % |",
        f"| Top candidatos       | {len(top)}   |",
        "",
        "---",
        "",
        f"## Top {len(top)} candidatos",
        "",
        "| ID | Template | Expresión | A₁ | Δc | ΔE | Rob. | Mejora | p-val | Score |",
        "|---|---|---|:---:|:---:|:---:|:---:|:---:|:---:|:---:|",
    ]
    for e in top:
        lines.append(_row(e))

    lines += [
        "",
        "> **A₁**: nodos A₁ detectados · **Δc**: separación mínima entre c* ·",
        "> **ΔE**: rango energético en [−2,2]² · **Rob.**: fracción de perturbaciones ±5% estables",
        "",
        "---",
        "",
        "## Criterios de selección",
        "",
        f"Un candidato pasa si cumple **al menos 2 de 3**:",
        "",
        f"| Criterio       | Umbral  | Qué mide                                      |",
        f"|----------------|:-------:|-----------------------------------------------|",
        f"| H₁_max (τ₁)   | > {tau1:.2f} | Loops topológicos en subniveles de H          |",
        f"| ΔE             | > {dE:.2f} | Rango energético (profundidad del pozo)       |",
        f"| δ_crit         | > {dcrit:.2f} | Separación mínima entre valores críticos c*   |",
        "",
        "**Score total** = 0.45 × TDA + 0.30 × Robustez + 0.25 × Mejora estratégica",
        "",
        "---",
        "",
        "## Invariantes matemáticos",
        "",
        "| Invariante         | Definición                              | Rol en Go                        |",
        "|--------------------|-----------------------------------------|----------------------------------|",
        "| Nodo A₁            | det(Hess H) < 0 en punto crítico        | Fibra singular → tensión crítica |",
        "| Número de Milnor μ | # nodos A₁; μ ≤ (d−1)²                 | Complejidad topológica           |",
        "| Genus g de fibra   | g=(d−1)(d−2)/2; cúbico → g=1 (toro)    | Tipo topológico de cada estado   |",
        "| c* (valor crítico) | H(punto crítico)                        | Umbral de cambio topológico      |",
        "| Separación Δc      | min|c*ᵢ − c*ⱼ|                          | Resolución entre regímenes       |",
        "",
        "---",
        "",
        "*Pipeline: `experiments/06_hamiltonian_families/` · Catálogo: `output/catalog.json`*",
    ]
    with open(path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))


def _generate_figures(catalog: Catalog, cfg: dict, id_to_rank: dict = None):
    """
    Genera figuras detalladas (3 paneles) para los candidatos del frente Pareto 1.
    Si id_to_rank es None, calcula el frente internamente.
    """
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from mpl_toolkits.mplot3d import Axes3D          # noqa: F401
    from mpl_toolkits.mplot3d.art3d import Poly3DCollection
    from src.topology import plot_persistence_diagram
    import numpy as np

    out_fig = HERE / cfg["output"].get("figures_dir", "output/figures")
    os.makedirs(out_fig / "frente_1", exist_ok=True)

    if id_to_rank is None:
        id_to_rank, _ = _compute_pareto_ranks(catalog)

    # Candidatos del frente 1 ordenados por score, máx 30
    front1 = [e for e in catalog.entries
               if e["filter"].get("passes") and id_to_rank.get(e["id"]) == 1]
    front1 = sorted(front1, key=lambda e: -e["scores"].get("total", 0))[:30]
    print(f"  Generando {len(front1)} figuras (frente Pareto 1)…")

    L = cfg["analysis"].get("box_L", 2.0)
    N = cfg["analysis"].get("grid_size", 150)

    for e in front1:
        from src.families import Hamiltonian
        h     = Hamiltonian(e["template"], e["coefficients"])
        cpts  = e["algebraic"].get("critical_points_summary", [])
        cvals = sorted(set(
            p["c_val"] for p in cpts if p.get("c_val") is not None
        ))
        a1pts = [p for p in cpts if p.get("type") == "A1_node"]

        xs = np.linspace(-L, L, N)
        ys = np.linspace(-L, L, N)
        X, Y = np.meshgrid(xs, ys)
        Z = np.array(h(X, Y), dtype=float)
        tda_r = compute_persistence(h, L=L, N=N,
                                    tau=cfg["tda"].get("tau", 0.15),
                                    n_thresh=cfg["tda"].get("n_thresholds", 80))

        fig = plt.figure(figsize=(17, 5))
        fig.patch.set_facecolor("#0A0A14")
        expr_str = e["expression"][:60]
        fig.suptitle(
            f"{e['id']}  ·  score={e['scores']['total']:.4f}  ·  {expr_str}",
            fontsize=8.5, color="white", y=1.01
        )

        # ── Panel 1: mapa 2D de energía + fibras críticas ──────────────────────
        ax2d = fig.add_subplot(1, 3, 1)
        ax2d.set_facecolor("#0A0A14")
        im = ax2d.contourf(X, Y, Z, levels=40, cmap="RdBu_r", alpha=0.85)
        cb = plt.colorbar(im, ax=ax2d, pad=0.02)
        cb.ax.yaxis.set_tick_params(color="white", labelcolor="white")

        # fibras críticas (líneas de nivel en c*)
        if cvals:
            ax2d.contour(X, Y, Z, levels=cvals,
                         colors="#F59B0A", linewidths=1.5, linestyles="--")
        # fibras de juego c = ±1
        for cv, col in [(-1., "#4488FF"), (1., "#FF6644")]:
            ax2d.contour(X, Y, Z, levels=[cv], colors=[col],
                         linewidths=1.2, linestyles="-")

        # puntos críticos: A₁ como diamantes naranjas, resto como círculos
        for p in cpts:
            mk = "D" if p.get("type") == "A1_node" else "o"
            ax2d.scatter(p["x"], p["y"], s=90, c="#F59B0A",
                         marker=mk, edgecolors="white", linewidths=0.8,
                         zorder=10)
            ax2d.annotate(
                f"c*={p.get('c_val',0):.3f}",
                (p["x"], p["y"]),
                textcoords="offset points", xytext=(6, 4),
                fontsize=6, color="#F59B0A"
            )

        # pares Go válidos
        GO_PAIRS = [(-1,-1),(-1,0),(-1,1),(1,-1),(1,0),(1,1)]
        gx = [p[0] for p in GO_PAIRS]
        gy = [p[1] for p in GO_PAIRS]
        ax2d.scatter(gx, gy, s=55, c="white", marker="^",
                     edgecolors="#AAAAAA", linewidths=0.6, zorder=9, alpha=0.8)

        ax2d.set_xlim(-L, L); ax2d.set_ylim(-L, L)
        ax2d.set_title("H(x,y)  —  fibras y puntos críticos", fontsize=8,
                        color="white", pad=4)
        ax2d.set_xlabel("s₀", color="white", fontsize=8)
        ax2d.set_ylabel("s₁", color="white", fontsize=8)
        ax2d.tick_params(colors="white", labelsize=7)
        for spine in ax2d.spines.values():
            spine.set_edgecolor("#444")

        # ── Panel 2: variedad 3D Γ(H) con puntos críticos A₁ ──────────────────
        ax3d = fig.add_subplot(1, 3, 2, projection="3d")
        ax3d.set_facecolor("#0A0A14")
        ax3d.xaxis.pane.fill = False
        ax3d.yaxis.pane.fill = False
        ax3d.zaxis.pane.fill = False
        for pane in [ax3d.xaxis.pane, ax3d.yaxis.pane, ax3d.zaxis.pane]:
            pane.set_edgecolor("#222")

        zmin, zmax = float(Z.min()), float(Z.max())
        zc = np.clip(Z, zmin, zmax)
        # superficie
        ax3d.plot_surface(X, Y, zc, cmap="RdBu_r",
                          alpha=0.82, linewidth=0, antialiased=True,
                          rcount=60, ccount=60)

        # fibras críticas sobre la variedad
        for cv in cvals:
            ax3d.contour(X, Y, zc, levels=[cv], offset=cv,
                         colors="#F59B0A", linewidths=1.8, zdir="z")

        # fibras de juego
        for cv, col in [(-1., "#4488FF"), (1., "#FF6644")]:
            if zmin < cv < zmax:
                ax3d.contour(X, Y, zc, levels=[cv], offset=cv,
                             colors=[col], linewidths=1.4, zdir="z")

        # puntos críticos A₁ sobre la variedad
        for p in a1pts:
            px, py = p["x"], p["y"]
            pz = float(h(px, py))
            ax3d.scatter([px], [py], [pz], s=200, c="#F59B0A",
                         marker="*", edgecolors="white", linewidths=0.8,
                         depthshade=False, zorder=20)
            ax3d.text(px, py, pz + (zmax - zmin) * 0.04,
                      f"A₁\nc*={pz:.3f}",
                      fontsize=6, color="#F59B0A", ha="center")

        ax3d.set_title("Γ(H) = {z=H(x,y)}  —  nodos A₁", fontsize=8,
                        color="white", pad=2)
        ax3d.set_xlabel("s₀", fontsize=7, color="white")
        ax3d.set_ylabel("s₁", fontsize=7, color="white")
        ax3d.set_zlabel("H", fontsize=7, color="white")
        ax3d.tick_params(colors="white", labelsize=6)
        ax3d.view_init(elev=28, azim=-55)

        # ── Panel 3: diagrama de persistencia ──────────────────────────────────
        ax_pd = fig.add_subplot(1, 3, 3)
        ax_pd.set_facecolor("#0A0A14")
        plot_persistence_diagram(
            tda_r,
            title=f"Persistencia  H₁_max={tda_r['max_h1_lifetime']:.3f}",
            ax=ax_pd
        )
        ax_pd.set_facecolor("#0A0A14")
        ax_pd.tick_params(colors="white", labelsize=7)
        ax_pd.xaxis.label.set_color("white")
        ax_pd.yaxis.label.set_color("white")
        ax_pd.title.set_color("white")
        for spine in ax_pd.spines.values():
            spine.set_edgecolor("#444")
        ax_pd.plot([zmin, zmax], [zmin, zmax], color="#555", lw=0.6)

        fig.tight_layout(pad=1.2)
        out_path = out_fig / "frente_1" / f"{e['id']}.png"
        fig.savefig(out_path, dpi=130, facecolor=fig.get_facecolor(),
                    bbox_inches="tight")
        plt.close(fig)
        print(f"  {out_path.parent.name}/{out_path.name}")


# ── Análisis de orden parcial (Pareto) ────────────────────────────────────────

def _compute_pareto_ranks(catalog: Catalog):
    """
    Calcula rangos Pareto sobre candidatos que pasan el filtro.
    Criterios (todos higher-is-better):
      H₁_max, robustez, well_depth, n_nodes_A1
    Devuelve: (dict id→rank, list entries_que_pasan)
    """
    entries = [e for e in catalog.entries if e["filter"].get("passes")]

    def vals(e):
        dc = e["algebraic"].get("min_crit_separation", 0) or 0
        return [
            float(e["tda"].get("max_h1_lifetime", 0) or 0),
            float(e["scores"].get("robustness", 0) or 0),
            float(e["tda"].get("well_depth", 0) or 0),
            int(e["algebraic"].get("n_nodes_A1", 0) or 0),
        ]

    V = [vals(e) for e in entries]
    n = len(entries)

    def dominates(i, j):
        return all(V[i][k] >= V[j][k] for k in range(4)) and \
               any(V[i][k] >  V[j][k] for k in range(4))

    id_to_rank = {}
    remaining  = list(range(n))
    rank = 1
    while remaining:
        front = [i for i in remaining
                 if not any(dominates(j, i) for j in remaining if j != i)]
        for i in front:
            id_to_rank[entries[i]["id"]] = rank
        remaining = [i for i in remaining if i not in set(front)]
        rank += 1

    return id_to_rank, entries


def _generate_pareto_overview(catalog: Catalog, cfg: dict):
    """
    Figura panorámica: 6 subplots que muestran los 300 candidatos
    ordenados por rango Pareto (frente 1 = no dominado por nadie).
    """
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    import matplotlib.gridspec as mgridspec
    from matplotlib.colors import Normalize
    from matplotlib.cm import ScalarMappable
    import numpy as np

    out_dir = HERE / cfg["output"].get("figures_dir", "output/figures")
    os.makedirs(out_dir, exist_ok=True)

    id_to_rank, entries = _compute_pareto_ranks(catalog)
    if not entries:
        print("  Sin candidatos para Pareto.")
        return id_to_rank

    # Guardar frentes en JSON
    fronts_by_rank = {}
    for eid, r in id_to_rank.items():
        fronts_by_rank.setdefault(str(r), []).append(eid)
    with open(out_dir / "pareto_fronts.json", "w") as f:
        json.dump(fronts_by_rank, f, indent=2)
    n_fronts = max(id_to_rank.values())
    n_front1 = sum(1 for r in id_to_rank.values() if r == 1)
    print(f"  Pareto: {n_fronts} frentes · {n_front1} en frente 1")

    # Arrays de métricas
    h1s  = np.array([e["tda"].get("max_h1_lifetime", 0) or 0  for e in entries])
    robs = np.array([e["scores"].get("robustness", 0) or 0     for e in entries])
    wds  = np.array([e["tda"].get("well_depth", 0) or 0        for e in entries])
    na1s = np.array([e["algebraic"].get("n_nodes_A1", 0) or 0  for e in entries], dtype=float)
    dcs_raw = [e["algebraic"].get("min_crit_separation", 0) or 0 for e in entries]
    dcs  = np.array([min(float(v), 80.) for v in dcs_raw])
    tots = np.array([e["scores"].get("total", 0) or 0          for e in entries])
    ids  = [e["id"] for e in entries]
    rnks = np.array([id_to_rank[e["id"]] for e in entries])

    norm  = Normalize(vmin=1, vmax=n_fronts)
    cmap  = plt.cm.plasma_r
    cols  = cmap(norm(rnks))
    sizes = 18 + h1s * 180

    f1_mask = rnks == 1

    fig = plt.figure(figsize=(22, 14), facecolor="#080810")
    fig.suptitle(
        f"Orden parcial Pareto  ·  {len(entries)} candidatos  ·  "
        f"{n_front1} en frente 1  ·  {n_fronts} frentes",
        color="white", fontsize=13, y=0.995)

    gs = mgridspec.GridSpec(2, 3, figure=fig,
                            hspace=0.38, wspace=0.30,
                            left=0.06, right=0.91, top=0.93, bottom=0.21)

    def _ax(pos, xlabel, ylabel, title):
        ax = fig.add_subplot(gs[pos])
        ax.set_facecolor("#0D0D1A")
        ax.set_xlabel(xlabel, color="#AAA", fontsize=9)
        ax.set_ylabel(ylabel, color="#AAA", fontsize=9)
        ax.set_title(title, color="white", fontsize=10, pad=5)
        ax.tick_params(colors="#777", labelsize=8)
        for sp in ax.spines.values(): sp.set_edgecolor("#2A2A3A")
        return ax

    def _scatter(ax, x, y, annotate_f1=True):
        ax.scatter(x[~f1_mask], y[~f1_mask], c=cols[~f1_mask],
                   s=sizes[~f1_mask], alpha=0.55, edgecolors="none", zorder=2)
        ax.scatter(x[f1_mask], y[f1_mask], c=cols[f1_mask],
                   s=sizes[f1_mask] * 2.2, edgecolors="white",
                   linewidths=0.7, zorder=5)
        if annotate_f1:
            for xi, yi, eid in zip(x[f1_mask], y[f1_mask],
                                   np.array(ids)[f1_mask]):
                ax.annotate(eid, (xi, yi), xytext=(3, 3),
                            textcoords="offset points",
                            fontsize=5, color="#FFD700", alpha=0.95)

    def _explain(ax, lines, loc="lower left"):
        """Añade una caja de explicación dentro del subplot."""
        va = "bottom" if "lower" in loc else "top"
        ha = "left"   if "left"  in loc else "right"
        x  = 0.02 if "left" in loc else 0.98
        y  = 0.03 if "lower" in loc else 0.97
        ax.text(x, y, "\n".join(lines),
                transform=ax.transAxes,
                fontsize=6.4, color="#C8C8DC", va=va, ha=ha,
                linespacing=1.45,
                bbox=dict(boxstyle="round,pad=0.35",
                          fc="#080818", ec="#2A2A4A", alpha=0.82))

    # — Plot 1: H₁ vs Δc ——————————————————————————————————————————————————————
    ax1 = _ax((0,0), "Δc (sep. entre c*)", "H₁_max",
               "H₁_max vs Δc  [★ frente 1]")
    _scatter(ax1, dcs, h1s)
    _explain(ax1, [
        "H₁_max: vida máxima del generador H₁ en la",
        "  fibración de Milnor (ciclos topológicos).",
        "Δc: separación mínima entre valores críticos c*",
        "  (resolución entre regímenes de juego).",
        "★ Frente 1: candidatos no dominados por ningún otro",
        "  en los 4 criterios simultáneamente.",
    ], loc="lower right")

    # — Plot 2: H₁ vs Robustez ————————————————————————————————————————————————
    ax2 = _ax((0,1), "Robustez", "H₁_max",
               "H₁_max vs Robustez")
    _scatter(ax2, robs, h1s, annotate_f1=False)
    _explain(ax2, [
        "Robustez: fracción de 20 perturbaciones ±5%",
        "  en coeficientes que mantienen al candidato",
        "  dentro del filtro (estabilidad estructural).",
        "H₁_max: topología de los subniveles de H.",
        "Ideal: ambos valores altos → candidato robusto",
        "  y topológicamente rico.",
    ], loc="lower left")

    # — Plot 3: ΔE vs nodos A₁ (jitter en x) ———————————————————————————————
    ax3 = _ax((0,2), "Nodos A₁", "ΔE (well depth)",
               "ΔE vs Nodos A₁")
    jitter = np.random.default_rng(0).uniform(-0.12, 0.12, len(na1s))
    _scatter(ax3, na1s + jitter, wds, annotate_f1=False)
    ax3.set_xticks([0, 1, 2, 3, 4])
    _explain(ax3, [
        "Nodos A₁: puntos críticos con det(Hess H) < 0",
        "  (sillas). Cada A₁ marca una transición donde",
        "  la fibra de Milnor H⁻¹(c) cambia de topología.",
        "ΔE: rango H(máx)−H(mín) en [−2,2]².",
        "  Mayor ΔE → mayor separación energética entre",
        "  posiciones de Go (contraste de evaluación).",
    ], loc="lower right")

    # — Plot 4: Score total vs H₁ ——————————————————————————————————————————————
    ax4 = _ax((1,0), "Score total", "H₁_max",
               "Score vs H₁  (color = rango Pareto)")
    _scatter(ax4, tots, h1s, annotate_f1=False)
    _explain(ax4, [
        "Score total = 0.45·TDA + 0.30·Robustez",
        "            + 0.25·Mejora estratégica.",
        "Color: rango Pareto (amarillo=frente 1,",
        "  violeta=frentes tardíos).",
        "Un candidato puede tener score alto pero no",
        "  estar en frente 1 si otro lo domina en todos",
        "  los criterios Pareto simultáneamente.",
    ], loc="lower right")

    # — Plot 5: distribución de candidatos por frente —————————————————————————
    ax5 = _ax((1,1), "Rango Pareto (frente)", "# candidatos",
               "Distribución por frente Pareto")
    counts = {}
    for r in rnks:
        counts[int(r)] = counts.get(int(r), 0) + 1
    xs_b = sorted(counts.keys())
    ys_b = [counts[x] for x in xs_b]
    bc   = [cmap(norm(x)) for x in xs_b]
    bars = ax5.bar(xs_b, ys_b, color=bc, edgecolor="#1A1A2A", linewidth=0.5)
    for bar, cnt in zip(bars, ys_b):
        ax5.text(bar.get_x() + bar.get_width()/2, cnt + 0.4, str(cnt),
                 ha="center", va="bottom", color="white", fontsize=7)
    ax5.tick_params(colors="#777", labelsize=8)
    _explain(ax5, [
        "Frente 1: candidatos no dominados (óptimos Pareto).",
        "Frente k: no dominados tras eliminar frentes 1…k−1.",
        "Algoritmo iterativo O(n³); 148 frentes indican",
        "  alta diversidad: pocos candidatos comparten el",
        "  mismo perfil en los 4 criterios a la vez.",
    ], loc="upper right")

    # — Plot 6: coordenadas paralelas (front 1 + muestra del resto) ————————
    ax6 = _ax((1,2), "", "Valor normalizado [0,1]",
               "Coordenadas paralelas  (frente 1 brillante)")
    crit_labels = ["H₁_max", "Robustez", "ΔE", "Nodos A₁"]
    raw = np.column_stack([h1s, robs, wds, na1s])
    lo, hi = raw.min(0), raw.max(0)
    hi = np.where(hi == lo, lo + 1e-9, hi)
    norm_data = (raw - lo) / (hi - lo)

    sample_rest = np.where(~f1_mask)[0]
    rng = np.random.default_rng(7)
    if len(sample_rest) > 50:
        sample_rest = rng.choice(sample_rest, 50, replace=False)
    for idx in sample_rest:
        ax6.plot(range(4), norm_data[idx], color=cols[idx], alpha=0.20, lw=0.6)
    for idx in np.where(f1_mask)[0]:
        ax6.plot(range(4), norm_data[idx], color=cols[idx], alpha=0.90, lw=1.6)
    ax6.set_xticks(range(4))
    ax6.set_xticklabels(crit_labels, color="white", fontsize=8)
    ax6.set_yticks([0, 0.5, 1.0])
    ax6.set_yticklabels(["mín", "med", "máx"], color="#777", fontsize=7)
    ax6.set_xlim(-0.15, 3.15); ax6.set_ylim(-0.05, 1.05)
    for xi in range(4):
        ax6.axvline(xi, color="#2A2A3A", lw=0.8)
    _explain(ax6, [
        "Cada línea = un candidato; ejes = criterios Pareto.",
        "Valores normalizados: 0=mín, 1=máx observado.",
        "Líneas brillantes: frente 1 (no dominadas).",
        "Líneas tenues: muestra de 50 candidatos del resto.",
        "El frente 1 ideal aparece alto en todos los ejes.",
    ], loc="lower left")

    # Colorbar compartida
    sm = ScalarMappable(norm=norm, cmap=cmap)
    sm.set_array([])
    cax = fig.add_axes([0.925, 0.21, 0.018, 0.69])
    cb  = fig.colorbar(sm, cax=cax)
    cb.set_label("Rango Pareto", color="white", fontsize=9)
    cb.ax.yaxis.set_tick_params(color="white", labelcolor="white")

    # ── Panel de leyenda / explicación general ─────────────────────────────────
    legend_ax = fig.add_axes([0.035, 0.01, 0.955, 0.175])
    legend_ax.set_facecolor("#0B0B1E")
    for sp in legend_ax.spines.values():
        sp.set_edgecolor("#3A3A5C"); sp.set_linewidth(0.8)
    legend_ax.set_xticks([]); legend_ax.set_yticks([])

    # Título del panel
    legend_ax.text(0.5, 0.93,
        "¿QUÉ ES EL ORDEN PARCIAL PARETO?",
        transform=legend_ax.transAxes,
        fontsize=9.5, fontweight="bold", color="#FFD700",
        ha="center", va="top")

    col_w = 0.245   # ancho de cada columna (en fracción de ejes)
    col_xs = [0.005, 0.255, 0.505, 0.755]  # x inicio de cada columna
    col_titles = ["CONCEPTO", "4 CRITERIOS PARETO", "CÓDIGO VISUAL", "INTERPRETACIÓN EN GO"]
    col_bodies = [
        (
            "Un orden parcial no produce un ranking lineal único,\n"
            "sino una jerarquía por capas (frentes).\n\n"
            "El candidato i  domina  a j  si:\n"
            "  · i ≥ j  en TODOS los 4 criterios, y\n"
            "  · i > j  en AL MENOS UNO.\n\n"
            "Frente 1 (★): ningún candidato los domina.\n"
            "Frente k: eliminando los frentes 1…k−1,\n"
            "son los no dominados del resto."
        ),
        (
            "1. H₁_max  →  vida del generador H₁ en la\n"
            "   filtración de sublevel sets de H.\n"
            "   Mide ciclos topológicos (toros de Milnor).\n\n"
            "2. Robustez  →  fracción de perturbaciones\n"
            "   ±5% que mantienen al candidato activo.\n\n"
            "3. ΔE  →  rango energético en [−2,2]².\n"
            "   Contraste entre posiciones extremas.\n\n"
            "4. Nodos A₁  →  puntos críticos de silla\n"
            "   (det Hess < 0): transiciones de fibra."
        ),
        (
            "Color  →  rango Pareto.\n"
            "  Amarillo  = Frente 1 (óptimos).\n"
            "  Violeta   = Frentes tardíos.\n\n"
            "Tamaño del punto  →  H₁_max.\n"
            "  Puntos grandes = más ciclos topológicos\n"
            "  en la fibración de Milnor.\n\n"
            "★ en gráficos = candidato del Frente 1.\n"
            "Borde blanco   = candidato no dominado."
        ),
        (
            "Cada A₁ corresponde a un  momento crítico\n"
            "de la partida: la fibra H⁻¹(c*) deja de ser\n"
            "un toro (g=1) y se convierte en una figura-8.\n\n"
            "H₁_max alto  →  el jugador atraviesa regiones\n"
            "topológicamente ricas; mayor tensión táctica.\n\n"
            "Frente 1 = los 4 candidatos que ofrecen la\n"
            "mejor combinación posible sin sacrificar\n"
            "ningún criterio estratégico a la vez."
        ),
    ]

    for ci, (cx, ctitle, cbody) in enumerate(zip(col_xs, col_titles, col_bodies)):
        # Línea divisoria vertical (excepto primera)
        if ci > 0:
            legend_ax.axvline(cx - 0.008, color="#2A2A4A", lw=0.8)
        # Título de columna
        legend_ax.text(cx + col_w * 0.48, 0.82, ctitle,
                       transform=legend_ax.transAxes,
                       fontsize=7.2, fontweight="bold", color="#A0A0FF",
                       ha="center", va="top")
        # Cuerpo
        legend_ax.text(cx + 0.005, 0.73, cbody,
                       transform=legend_ax.transAxes,
                       fontsize=6.6, color="#C8C8DC", va="top", ha="left",
                       linespacing=1.4,
                       fontfamily="monospace")

    out_path = out_dir / "pareto_overview.png"
    fig.savefig(out_path, dpi=130, facecolor=fig.get_facecolor(),
                bbox_inches="tight")
    plt.close(fig)
    print(f"  Panorámica Pareto → {out_path.name}")
    return id_to_rank


def _generate_atlas(catalog: Catalog, cfg: dict, id_to_rank: dict):
    """
    Atlas: grid de todos los candidatos como mini-heatmaps,
    ordenados por rango Pareto y luego por score total.
    Borde dorado = frente 1, plateado = frente 2, bronce = frente 3.
    """
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    import numpy as np
    from src.families import Hamiltonian as _Ham

    out_dir = HERE / cfg["output"].get("figures_dir", "output/figures")
    os.makedirs(out_dir, exist_ok=True)

    entries = [e for e in catalog.entries if e["filter"].get("passes")]
    entries = sorted(entries,
                     key=lambda e: (id_to_rank.get(e["id"], 999),
                                    -e["scores"].get("total", 0)))

    L  = cfg["analysis"].get("box_L", 2.0)
    N  = 48
    xs = np.linspace(-L, L, N)
    ys = np.linspace(-L, L, N)
    X, Y = np.meshgrid(xs, ys)

    ncols   = 20
    nrows   = (len(entries) + ncols - 1) // ncols
    ts      = 1.15   # pulgadas por thumbnail
    fig, axes = plt.subplots(nrows, ncols,
                              figsize=(ncols * ts, nrows * ts + 0.8))
    fig.patch.set_facecolor("#060610")
    fig.suptitle(
        f"Atlas — {len(entries)} candidatos · orden Pareto (izq→der, arriba=frente 1)",
        color="white", fontsize=11, y=1.002)

    border_col  = {1: "#FFD700", 2: "#C0C0C0", 3: "#CD7F32"}
    border_lw   = {1: 2.2,       2: 1.6,       3: 1.2}

    for idx, e in enumerate(entries):
        row, col = divmod(idx, ncols)
        ax = axes[row, col] if nrows > 1 else axes[col]
        ax.set_facecolor("#0A0A14")
        ax.set_xticks([]); ax.set_yticks([])

        try:
            h = _Ham(e["template"], e["coefficients"])
            Z = np.array(h(X, Y), dtype=float)
            ax.contourf(X, Y, Z, levels=10, cmap="RdBu_r", alpha=0.9)
            for p in e["algebraic"].get("critical_points_summary", []):
                if p.get("type") == "A1_node":
                    ax.scatter(p["x"], p["y"], s=10, c="#F59B0A",
                               marker="D", zorder=5, linewidths=0)
        except Exception:
            pass

        rank = id_to_rank.get(e["id"], 99)
        bc   = border_col.get(rank, "#1A1A2A")
        blw  = border_lw.get(rank, 0.4)
        for sp in ax.spines.values():
            sp.set_edgecolor(bc); sp.set_linewidth(blw)

        score  = e["scores"].get("total", 0)
        tcol   = "white" if rank <= 3 else "#555"
        tfsize = 4.2 if rank <= 3 else 3.8
        ax.set_title(f"{e['id']}  #{rank}\n{score:.3f}",
                     fontsize=tfsize, color=tcol, pad=1.2)

    for idx in range(len(entries), nrows * ncols):
        row, col = divmod(idx, ncols)
        ax = axes[row, col] if nrows > 1 else axes[col]
        ax.set_visible(False)

    fig.tight_layout(pad=0.25, h_pad=0.6, w_pad=0.3)
    out_path = out_dir / "atlas_candidatos.png"
    fig.savefig(out_path, dpi=115, facecolor=fig.get_facecolor(),
                bbox_inches="tight")
    plt.close(fig)
    print(f"  Atlas → {out_path.name}  ({len(entries)} candidatos)")


def main():
    parser = argparse.ArgumentParser(
        description="Pipeline: Familia de polinomios Go y sus variedades")
    parser.add_argument("--config",   default=None,  help="Ruta al config.yaml")
    parser.add_argument("--template", default=None,
                        choices=list(TEMPLATES.keys()),
                        help="Plantilla a usar (por defecto: config.yaml)")
    parser.add_argument("--n",        type=int, default=None,
                        help="Número de muestras")
    parser.add_argument("--mode",     default=None,
                        choices=["random","grid"],
                        help="Modo de muestreo")
    parser.add_argument("--all-templates", action="store_true",
                        help="Corre todas las plantillas en secuencia")
    parser.add_argument("--top",      type=int, default=None,
                        help="Solo imprime resumen de los mejores N")
    parser.add_argument("--figures",  action="store_true",
                        help="Genera figuras detalladas (3 paneles) para frente Pareto 1")
    parser.add_argument("--pareto",   action="store_true",
                        help="Genera panorámica Pareto y atlas de todos los candidatos")
    args = parser.parse_args()

    cfg = load_cfg(args.config)

    fam_cfg = cfg.setdefault("family", {})
    if args.template: fam_cfg["template"]    = args.template
    if args.n:        fam_cfg["n_samples"]   = args.n
    if args.mode:     fam_cfg["sample_mode"] = args.mode

    cat_path = str(HERE / cfg["output"].get("catalog_path", "output/catalog.json"))

    if args.top or args.pareto or args.figures:
        catalog = Catalog(cat_path)
        if args.top:
            cfg["output"]["top_n"] = args.top
            _print_summary(catalog, cfg)
        if args.pareto:
            id_to_rank = _generate_pareto_overview(catalog, cfg)
            _generate_atlas(catalog, cfg, id_to_rank)
        if args.figures:
            # Figuras detalladas para frente 1 (o top 20 si front1 > 20)
            id_to_rank_f, _ = _compute_pareto_ranks(catalog)
            _generate_figures(catalog, cfg, id_to_rank=id_to_rank_f)
        return

    templates = list(TEMPLATES.keys()) if args.all_templates \
                else [fam_cfg.get("template", "cubic_mixed")]

    for tmpl in templates:
        print(f"\n{'='*60}")
        print(f"  TEMPLATE: {tmpl}")
        print(f"{'='*60}")
        t0 = time.time()
        run_pipeline(cfg, tmpl,
                     fam_cfg.get("n_samples", 300),
                     fam_cfg.get("sample_mode", "random"))
        print(f"  Tiempo total: {time.time()-t0:.1f} s")

    if args.figures or args.pareto:
        catalog = Catalog(cat_path)
        id_to_rank = _generate_pareto_overview(catalog, cfg)
        _generate_atlas(catalog, cfg, id_to_rank)
        _generate_figures(catalog, cfg, id_to_rank=id_to_rank)


if __name__ == "__main__":
    main()
