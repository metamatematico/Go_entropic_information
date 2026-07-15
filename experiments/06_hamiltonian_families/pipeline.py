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
    top = catalog.top_n(cfg.get("output",{}).get("top_n",10))
    os.makedirs(os.path.dirname(path), exist_ok=True)
    lines = [
        "# Resumen ejecutivo: Familia de polinomios Go",
        f"*Generado: {__import__('datetime').date.today()}*\n",
        "## Descripción",
        "Pipeline de búsqueda, análisis y validación de Hamiltonianos polinómicos",
        "para modelar estrategia en Go mediante la teoría de la fibración de Milnor.",
        "",
        f"## Top {len(top)} candidatos\n",
        "| ID | Template | Expresión | H₁_max | Robustez | Mejora estratégica | Score |",
        "|---|---|---|---|---|---|---|",
    ]
    for e in top:
        sc  = e["scores"]
        val = e["validation"]
        imp = val.get("improvement") or 0.0
        lines.append(
            f"| {e['id']} | {e['template']} | `{e['expression'][:40]}` |"
            f" {e['tda'].get('max_h1_lifetime',0):.3f} |"
            f" {sc.get('robustness',0):.3f} |"
            f" {imp:.4f} |"
            f" {sc.get('total',0):.4f} |"
        )
    lines += [
        "",
        "## Criterios de filtrado",
        "- Vida máxima H₁ normalizada > 0.20",
        "- Profundidad de pozo ΔE > 0.50",
        "- Separación entre valores críticos > 0.30",
        "- Robustez: ≥80% de perturbaciones ±5% mantienen el score",
        "",
        "## Invariantes clave",
        "- **Nodo A₁**: punto crítico no degenerado → fibra singular (pinchada)",
        "- **H₁ persistente**: agujero topológico en los subniveles → pozo estratégico",
        "- **Fibración de Milnor**: familia {H⁻¹(c) : c ∈ ℝ} parametrizada por el hamiltoniano",
    ]
    with open(path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))


def _generate_figures(catalog: Catalog, cfg: dict):
    """Genera visualizaciones para los top candidatos."""
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from src.topology import plot_persistence_diagram
    import numpy as np

    out_fig = HERE / cfg["output"].get("figures_dir","output/figures")
    os.makedirs(out_fig, exist_ok=True)
    top = catalog.top_n(cfg.get("output",{}).get("top_n",10))

    for e in top[:5]:   # figuras solo para top 5
        from src.families import Hamiltonian
        h   = Hamiltonian(e["template"], e["coefficients"])
        tda_r = compute_persistence(h, L=cfg["analysis"].get("box_L",2.0),
                                    N=cfg["analysis"].get("grid_size",150))

        fig, axes = plt.subplots(1, 2, figsize=(11, 4.5))
        fig.suptitle(f"{e['id']}  —  {e['expression'][:55]}", fontsize=9)

        # Mapa de calor H(x,y)
        L  = cfg["analysis"].get("box_L", 2.0)
        N  = cfg["analysis"].get("grid_size", 150)
        xs = np.linspace(-L, L, N)
        ys = np.linspace(-L, L, N)
        X, Y = np.meshgrid(xs, ys)
        Z = np.array(h(X, Y), dtype=float)
        im = axes[0].contourf(X, Y, Z, levels=30, cmap="RdBu_r")
        plt.colorbar(im, ax=axes[0])
        axes[0].contour(X, Y, Z,
                        levels=[p["c_val"] for p in
                                e["algebraic"].get("critical_points_summary",[])
                                if p.get("c_val") is not None],
                        colors="orange", linewidths=1.2, linestyles="--")
        cpts = e["algebraic"].get("critical_points_summary", [])
        if cpts:
            axes[0].scatter([p["x"] for p in cpts],
                            [p["y"] for p in cpts],
                            c="orange", s=60, zorder=5, marker="D")
        axes[0].set_title("H(x,y) — mapa de energía", fontsize=8)
        axes[0].set_xlabel("s₀"); axes[0].set_ylabel("s₁")

        # Diagrama de persistencia
        plot_persistence_diagram(tda_r,
                                 title=f"Persistencia — score={e['scores']['total']:.3f}",
                                 ax=axes[1])

        plt.tight_layout()
        fig.savefig(out_fig / f"{e['id']}.png", dpi=110)
        plt.close(fig)


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
                        help="Genera figuras para el top N")
    args = parser.parse_args()

    cfg = load_cfg(args.config)

    # Overrides desde CLI
    fam_cfg = cfg.setdefault("family", {})
    if args.template: fam_cfg["template"]   = args.template
    if args.n:        fam_cfg["n_samples"]  = args.n
    if args.mode:     fam_cfg["sample_mode"] = args.mode

    cat_path = str(HERE / cfg["output"].get("catalog_path","output/catalog.json"))

    if args.top:
        catalog = Catalog(cat_path)
        cfg["output"]["top_n"] = args.top
        _print_summary(catalog, cfg)
        if args.figures:
            _generate_figures(catalog, cfg)
        return

    templates = list(TEMPLATES.keys()) if args.all_templates \
                else [fam_cfg.get("template", "cubic_mixed")]

    for tmpl in templates:
        print(f"\n{'═'*60}")
        print(f"  TEMPLATE: {tmpl}")
        print(f"{'═'*60}")
        t0 = time.time()
        run_pipeline(cfg, tmpl,
                     fam_cfg.get("n_samples", 300),
                     fam_cfg.get("sample_mode", "random"))
        print(f"  Tiempo total: {time.time()-t0:.1f} s")

    if args.figures:
        catalog = Catalog(cat_path)
        _generate_figures(catalog, cfg)
        print("  Figuras generadas.")


if __name__ == "__main__":
    main()
