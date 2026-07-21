# Go Ising — Entropic Information Analysis

Comparative analysis of two classical Ising models applied to the game of Go.
Computes bond-level interaction energies, Shannon entropy, Boltzmann entropy, and
effective temperature for 19 standard opening patterns and real professional games.

**Paper:** Sesma González & Jiménez Martínez, *"Pattern Acquisition and Comparative
Analysis in the Game of Go"*, Journal of Go Studies, Vol. 19 No. 2, 2025.

---

## Models compared

### Model M1 — Mercado Sánchez & Jiménez Martínez
```
H(sᵢ, sⱼ) = sᵢ + 2sⱼ − sᵢ·sⱼ² − sᵢ²·sⱼ
```
- Spins: Negro = −1, Vacío = 0, Blanco = +1
- 5 possible bond values: {−2, −1, 0, +1, +2}
- **Asymmetric**: H(i→j) ≠ H(j→i) for 6 of 9 pairs
- **Vacuum is active**: H(0, xⱼ) ≠ 0 — empty cells carry energy

### Model Alvarado — Atomic-Go (Rojas-Domínguez, Barradas-Bautista & Alvarado 2019)
```
H(xᵢ, xⱼ) = xᵢ · xⱼ    (µ = 0, wᵢⱼ = 1)
```
- Spins: Negro = −1, Vacío = 0, Blanco = +1
- 3 possible bond values: {−1, 0, +1}
- **Symmetric**: H(i→j) = H(j→i) always
- **Vacuum is invisible**: H(0, xⱼ) = 0 always

---

## Requirements

```bash
pip install numpy>=1.23 scipy>=1.10 matplotlib>=3.7
```

---

## Project structure

```
Go_entropic_information/
│
├── src/
│   ├── go_ising_classical.py       # M1 Hamiltonian, energy map, kernel config
│   ├── go_entropy.py               # Shannon, Boltzmann entropy, T_eff
│   ├── go_game_engine.py           # Go rules engine + SGF parser
│   ├── go_visualization.py         # Grid and comparison plots
│   └── board_utils.py              # Board utilities
│
├── scripts/
│   ├── pipeline/                   # Data generation scripts
│   │   ├── build_dataset.py        # Build main feature dataset
│   │   ├── build_patterns_dataset.py
│   │   ├── build_trajectory_dataset.py
│   │   ├── extract_sgf_patterns.py # SGF opening pattern extraction
│   │   └── analyze_sgf_evolution.py # SGF phase/block energy analysis
│   ├── analysis/
│   │   ├── analysis_patterns.py
│   │   ├── analysis_game.py
│   │   └── compare_per_bond.py
│   └── viz/
│       └── ...                     # Visualization scripts
│
├── data/
│   └── sgf_partidas/               # ~3024 professional SGF games (not in repo)
│
└── results/
    ├── 01_patrones/                # 19 joseki opening patterns
    │   ├── patterns_base_boards.png
    │   ├── patterns_comparison.png
    │   ├── energy_grid_M1.png
    │   ├── energy_grid_alvarado.png
    │   ├── energy_inventory.png
    │   └── patterns_base.csv       # Pattern definitions table
    │
    ├── 02_enlaces_ising/           # Bond-level Ising interaction analysis
    │   ├── bond_interaction_table.png
    │   ├── bond_interaction_graph.png
    │   ├── bond_distribution.png
    │   ├── bond_entropy_compare.png
    │   ├── interaction_comparison.png
    │   └── interactions_H.png
    │
    ├── 03_entropia/                # Shannon, Boltzmann entropy & T_eff
    │   ├── entropy_comparison.png  # Full 3-model comparison
    │   ├── entropy_compare_M1.png
    │   ├── entropy_boltzmann_lnW.png
    │   ├── dashboard_M1.png        # Complete M1 dashboard
    │   ├── dashboard_alvarado.png
    │   ├── dataset_features.csv    # 107 features × 19 patterns
    │   ├── dataset_board_flat.csv
    │   └── dataset_metadata.json
    │
    ├── 04_trayectoria/             # Turn-by-turn trajectory (19 patterns)
    │   ├── trajectory_viz.png      # Heatmaps + energy curves
    │   ├── trajectory_full.csv     # One row per (pattern, turn)
    │   └── trajectory_summary.csv  # Aggregated per pattern
    │
    ├── 05_partidas_reales/         # Analysis of 3024 real professional games
    │   ├── sgf_heatmap.png         # Positional frequency heatmaps
    │   ├── sgf_histogram.png       # Opening divergence histogram
    │   ├── sgf_top_openings.png    # Most common openings (4/8/16 moves)
    │   ├── sgf_phase_heatmaps.png  # Spatial distribution by phase
    │   ├── sgf_phase_energy.png    # M1 + Alvarado energy by phase
    │   ├── sgf_phase_sequences.png # Most frequent sequences per phase
    │   ├── sgf_openings.csv        # First 30 moves per game (3024 rows)
    │   ├── sgf_patterns.csv        # Top-20 recurring patterns by length
    │   ├── sgf_evolution_by_move.csv   # Energy per (game, turn) — 121k rows
    │   └── sgf_evolution_by_block.csv  # Stats per 10-move phase (6 rows)
    │
    ├── 06_animaciones/             # GIF animations of real games
    │   └── *.gif
    │
    └── interactive/
        └── feature_explorer.html   # Interactive feature dashboard
│
└── experiments/
    ├── 06_hamiltonian_families/    # Búsqueda y clasificación de Hamiltonianos cúbicos
        ├── pipeline.py             # Pipeline completo: generar, analizar, visualizar
        ├── src/
        │   ├── hamiltonians.py     # Familias de polinomios (cubic_mixed, h_m1, …)
        │   ├── algebra.py          # Puntos críticos, nodos A₁, número de Milnor
        │   ├── topology.py         # TDA: H₀/H₁ con gudhi CubicalComplex
        │   └── robustness.py       # Perturbaciones ±5%, fracción de estabilidad
        └── output/
            ├── catalog.json        # 305 Hamiltonianos + métricas completas
            ├── figures/
            │   ├── pareto_overview.png      # Panorama de los 4 criterios Pareto
            │   ├── atlas_candidatos.png     # Cuadrícula 15×20 de las 296 variedades (2D)
            │   ├── atlas_candidatos_3d.png  # Idem con superficies 3D
            │   ├── hasse_diagram.png        # Diagrama de Hasse del orden parcial (2D)
            │   └── hasse_diagram_3d.png     # Idem con nodos como superficies 3D
            └── reports/
                ├── executive_summary.md     # Resumen ejecutivo + top 5
                └── hasse_diagram_report.md  # Informe completo: matemática + Go

    ├── 07_moyo_dataset/            # Predicción de moyo/territorio contra KataGo real
    │   ├── src/
    │   │   ├── katago_engine.py        # Wrapper del motor KataGo (modo analysis, JSON)
    │   │   ├── moyo_detector.py        # Flood-fill de regiones por banda de ownership
    │   │   ├── features.py             # board_features, relaxation_field (Boltzmann)
    │   │   ├── early_regions.py        # Muestreo de fuseki (3–15%) + regiones de joseki
    │   │   ├── cache_positions.py      # Corre KataGo 1 vez, cachea moyo/territorio
    │   │   ├── cache_early_positions.py# Idem para fuseki/joseki
    │   │   ├── optimize_coefficients.py# Fase A/B: differential_evolution sobre el cache
    │   │   ├── run_fase_b.py           # Fase B: búsqueda en las 4 dims. efectivas
    │   │   └── analyze_results.py      # ΔR² incremental, bootstrap por partida
    │   └── output/
    │       ├── cache_*.pkl              # Caches de posiciones (KataGo corrido 1 vez)
    │       └── reports/
    │           ├── informe_completo_07_08.tex # Reporte unificado (exp. 07 + 08)
    │           ├── avance_experimento07.tex   # Reporte solo del exp. 07 (histórico)
    │           └── correlaciones_moyo.png     # Campo del Hamiltoniano vs. KataGo real
    │
    └── 08_teoria_invariantes/      # Por qué el campo solo ve 4 de 7 parámetros
        └── output/reports/
            └── teoria_invariantes_klein.tex  # Derivación vía el grupo de Klein
```

---

## Usage

### Bond interaction table (4 visual representations)
```bash
python viz_interaction_comparison.py
# → results/interaction_comparison.png
```

### Entropy comparison (Shannon + Boltzmann + T_eff) for 19 patterns
```bash
python viz_entropy_comparison.py
# → results/entropy_comparison.png
```

### Animated game with single-model energy overlay
```bash
python animation_game.py                             # first available SGF
python animation_game.py data/sgf_partidas/X.sgf    # specific game
python animation_game.py --step 2 --fps 6 --m 1
# → results/<game>_M1.gif
```

### Animated game with dual-model entropy comparison
```bash
python animation_entropy_compare.py
python animation_entropy_compare.py data/sgf_partidas/X.sgf --step 2 --fps 5
# → results/<game>_entropy_compare.gif
```

### Per-bond analysis for all 19 patterns
```bash
python compare_per_bond.py
# → results/bond_interaction_table.png
# → results/bond_entropy_compare.png
# → results/bond_distribution.png
```

### Experiment 06 — Hamiltonian family search
```bash
cd experiments/06_hamiltonian_families

# 1. Generate catalog (300 cubic_mixed + reference Hamiltonians)
python pipeline.py --generate --n 300

# 2. Pareto analysis + all figures
python pipeline.py --pareto
# → output/figures/pareto_overview.png
# → output/figures/atlas_candidatos.png
# → output/figures/atlas_candidatos_3d.png
# → output/figures/hasse_diagram.png
# → output/figures/hasse_diagram_3d.png

# 3. Individual Hamiltonians (Frente 1)
python pipeline.py --frente1
# → output/figures/frente_1/H_00XX.png  (one per candidate)
```

### Experiment 07 — moyo prediction pipeline
```bash
cd experiments/07_moyo_dataset/src

# 1. Run KataGo once per position, cache board + regions (moyo/territory)
python cache_positions.py --n_games 20
# → ../output/position_cache.pkl

# 2. Fuseki (3–15%) + joseki (corners), same caching pattern
python cache_early_positions.py --n_games 20
# → ../output/cache_early20.pkl

# 3. Fase B: optimize directly in the 4 effective dimensions
#    (Sigma_a, Sigma_b, b12, Sigma_c) over the full cubic_mixed family
python run_fase_b.py
# → ../output/fase_b_result.json
```
Requires a local KataGo binary + neural net (see the experiment's own
setup notes) — not bundled in this repo (see `tools/` in `.gitignore`).

---

## Results overview

| File | Description |
|------|-------------|
| `interaction_comparison.png` | Heatmaps, difference matrix, bar chart and node graphs |
| `entropy_comparison.png` | Shannon, Boltzmann, T_eff for table + 19 patterns + scatter |
| `bond_interaction_table.png` | Directed bond energy table for both models |
| `bond_entropy_compare.png` | Per-pattern Shannon entropy comparison |
| `*_entropy_compare.gif` | Game animation: S_Shannon, S_Boltzmann, T_eff live |
| `*_M1.gif` | Game animation: board + M1 energy overlay |
| `dashboard_M1/M2.png` | Full energy and entropy dashboard per model |

---

## Experiment 06 — Hamiltonian families & Pareto order

Systematic search over 300 cubic polynomial Hamiltonians H(x,y), evaluated with 4 criteria:

| Criterion | Symbol | What it measures |
|-----------|--------|-----------------|
| Topological lifetime H₁ | H₁_max | Persistent 1-cycles in Milnor fibration — tactical complexity |
| Robustness | Rob | Fraction of ±5% perturbations that preserve the candidate's rank |
| Energy range | ΔE | H(max) − H(min) on [−2,2]² — contrast between extreme positions |
| A₁ nodes | n_A₁ | Saddle critical points where fiber H⁻¹(c) changes topology |

**296 candidates** passed the filter (97%). Pareto peeling produced **148 fronts**.

**Frente 1 — 4 Pareto-optimal Hamiltonians (mutually incomparable):**

| ID | H₁_max | Rob | ΔE | A₁ |
|----|:------:|:---:|:--:|:--:|
| H_0094 | **0.188** | 1.0 | 31.3 | 1 |
| H_0113 | 0.173 | 1.0 | 35.4 | 1 |
| H_0045 | 0.166 | 1.0 | **43.4** | **2** |
| H_0042 | 0.120 | 1.0 | 33.5 | **2** |

**Mathematical structure (Hasse diagram):**
- The partial order is a finite poset with no top or bottom element (no supremum, no infimum)
- Not a lattice: joins fail for pairs in Frente 1
- By Dilworth's theorem: max antichain = 4 → minimum chain cover = **4 chains**
- 475 cover relations visualized in `hasse_diagram.png`

See [`experiments/06_hamiltonian_families/output/reports/hasse_diagram_report.md`](experiments/06_hamiltonian_families/output/reports/hasse_diagram_report.md) for the full mathematical and strategic interpretation.

---

## Experiments 07 & 08 — how they relate

Experiments 07 and 08 are two sides of the same investigation, not two
unrelated projects:

- **Experiment 07 is empirical.** It uses classical Ising Hamiltonians
  plus a Boltzmann relaxation field to **predict** real moyo/territory
  the way KataGo (a reference AI engine) sees it after analyzing
  professional games. It runs KataGo, measures ΔR², compares
  candidates — applied statistics on real data.
- **Experiment 08 is theoretical.** It predicts nothing new and never
  runs KataGo. It takes one specific finding that surfaced *inside*
  Experiment 07 — "the relaxation field only depends on 4 of the 7
  coefficients of `cubic_mixed`, never on all 7 independently" — and
  proves **why** that has to happen, systematically, using group
  theory (the Klein four-group). It formalizes a mechanism Experiment
  07 was already using without proving it.

In short: Experiment 07 answers *"how well does this Hamiltonian
predict real moyo?"*; Experiment 08 answers *"why does the relaxation
field ignore certain coefficients of the Hamiltonian, no matter which
Hamiltonian it is?"*. The second question was born inside the first
experiment, but its answer is purely algebraic — it needs no KataGo run
and no data — so it became its own experiment with its own folder.
Both live in [`experiments/07_moyo_dataset/output/reports/informe_completo_07_08.tex`](experiments/07_moyo_dataset/output/reports/informe_completo_07_08.tex),
a single unified report presented in the order they are logically
needed: first the empirical evidence that motivates the question
(Experiment 07), then the formal answer (Experiment 08).

---

## Experiment 07 — Predicting moyo against real KataGo analysis

**Question:** can a classical pairwise Ising Hamiltonian $H(s_i,s_j)$,
built on the Go spin model $s\in\{-1,0,+1\}$, predict **real territory**
(*moyo*) — as computed by a reference AI engine (KataGo) analyzing
professional games — better than board geometry alone (distance to
stones, distance to the edge)?

**Success metric:** ΔR² — the gain in R² from adding the Hamiltonian's
averaged field over a candidate region, on top of a geometry-only
baseline, with significance checked by an F-test.

**Pipeline** (KataGo runs once per position, cached, then reused for
hundreds of Hamiltonian evaluations — the expensive step is separated
from the cheap one):

```
game.sgf → sample positions → KataGo (ownership, once) → cache
                                                             │
                              47+ Hamiltonians × relaxation_field(cache)
                                                             │
                                                 ΔR² per Hamiltonian
```

**Key results** (20 real professional games, `kata1-b15c192`, local OpenCL):

| Finding | Result |
|---|---|
| Topological criteria (Experiment 06's "Frente 1") vs. real ΔR² | **worst** real performance of all groups tested — do not use to rank candidates |
| Random search (69 candidates, 2 families) | never beats hand-derived Hamiltonians; unstable across interaction radius |
| $H_{M1}$ (Mercado & Jiménez) / Alvarado, hand-derived | the only candidates whose ΔR² **improves** with wider interaction radius |
| Fase A — direct optimization (`sparse_cubic`, 4 params) | $H_{OPT\_A}$: ΔR²=0.317, CI95%=[0.227,0.380] — statistical tie with $H_{M1}$ |
| Fase B — optimization in the 4 effective dims (`cubic_mixed`, full) | $H_{OPT\_B}$: ΔR²=0.421, CI95%=[0.339,0.486] — narrow overlap, strongest result so far |
| Full model $R^2$ (geometry + $H_{OPT\_B}$) | 0.733 ⇒ correlation $r\approx0.86$ against real KataGo territory |
| KataGo signal audit (7 fields tested) | only `ownershipStdev` (via weighting) adds real signal; `policy`, `moveInfos`, `scoreStdev`, `winrate`, `scoreLead` don't |

**Go-position categories covered** (all reusing the same
`relaxation_field` machinery except sente/gote):

| # | Category | Status |
|---|---|---|
| 1 | Moyo (contested territory) | ✅ enabled |
| 2 | Settled territory | ✅ enabled |
| 3 | Game phase (15–90%) | ✅ enabled |
| 4 | Joseki (corners) | ✅ enabled |
| 5 | Fuseki (opening, 3–15%) | ✅ enabled |
| 6 | Stone groups / life-death | ⬜ pending — needs a new group-level mechanism |
| 7 | Active border / aji | ⬜ pending — needs a new group-level mechanism |
| 8 | Sente/gote (tempo) | ✅ enabled — real but weak signal |

Full report, with every table, statistical caveat (game-level
bootstrap, not row-level p-values), and open decision points:
[`experiments/07_moyo_dataset/output/reports/informe_completo_07_08.tex`](experiments/07_moyo_dataset/output/reports/informe_completo_07_08.tex).

---

## Experiment 08 — Why the field only sees 4 of 7 parameters

The `cubic_mixed` template has 7 free coefficients:
$H(x,y)=a_1x+a_2y+b_{11}x^2+b_{12}xy+b_{22}y^2+c_{112}x^2y+c_{122}xy^2$.
Experiment 07 found empirically that `relaxation_field` only ever
depends on 4 combinations of them ($\Sigma a,\Sigma b,b_{12},\Sigma c$),
because it always evaluates the symmetric sum $H(s,q)+H(q,s)$, never
$H(s,q)$ alone. Experiment 08 derives **why** that has to be true, using
representation theory instead of case-by-case algebra:

1. **σ (position swap)**, $(x,y)\mapsto(y,x)$ — motivated directly by
   the $H(s,q)+H(q,s)$ symmetrization. A group of order 2 splits any
   polynomial into an invariant half (survives averaging) and an
   anti-invariant half (cancels exactly) — no third option.
2. Applied monomial by monomial: **4 of the 7 survive**, 3 cancel
   identically. Verified both symbolically (`sympy`) and empirically —
   Hamiltonians built purely from the anti-invariant part give
   ΔR²=0.000000 exact, to machine precision, on real game data.
3. **τ (color swap)**, $(x,y)\mapsto(-x,-y)$ — a second, independent
   symmetry. Together, $\{e,\sigma,\tau,\sigma\tau\}$ form the **Klein
   four-group** ($\mathbb{Z}_2\times\mathbb{Z}_2$, not cyclic $\mathbb{Z}_4$ — every
   non-identity element has order 2), which has exactly 4 real
   irreducible characters. Projecting `cubic_mixed` onto each
   (Reynolds operator) refines the 4 surviving combinations without
   changing how many there are.
4. **Practical payoff:** searching directly in the 4 effective
   dimensions instead of the 7 raw ones (used for Fase B, Experiment
   07) is provably lossless for this objective — not just empirically
   convenient.

Full derivation, with the Cayley table, character table, and the
corrected decomposition showing that $H_{M1}$ itself is *not* purely
invariant (a subtlety the report explicitly walks through after an
earlier overclaim):
[`experiments/08_teoria_invariantes/output/reports/teoria_invariantes_klein.tex`](experiments/08_teoria_invariantes/output/reports/teoria_invariantes_klein.tex).

---

## Key findings (summary)

1. **M1 Shannon entropy > Alvarado in all 19/19 patterns** (mean gap: 1.92 nats).
2. **Same-color interaction inverts sign**: M1 gives −1 (attraction), Alvarado gives +1 (repulsion).
3. **Correlation r = 0.83** between models across patterns — structurally complex positions are complex for both.
4. **Thermodynamic cooling is not captured**: T_eff → ∞ throughout real games because two colors cancel ⟨E⟩ ≈ 0.
5. **Shannon entropy grows** with move count (more active bonds), not strategic complexity.
6. **Boltzmann entropy** stays near maximum for the same reason (T_eff large → uniform Gibbs distribution).

See [REPORTE.md](REPORTE.md) for the full scientific findings report.

---

## Authors

- **Leonardo Jiménez Martínez** — Entropic analysis, model comparison (UNAM)
- **Mario Mercado Sánchez** — Ising model development ([Ometitlan / Project-Quantum-Go](https://github.com/ometitlan/Project-Quantum-Go))

Paper co-authored with **Ángel Alberto Sesma González**: *"Pattern Acquisition and Comparative Analysis in the Game of Go"*, Journal of Go Studies, Vol. 19 No. 2, 2025.

Comparison with: Rojas-Domínguez, Barradas-Bautista & Alvarado (2019), *Atomic-Go*. IEEE Access.
