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
│   ├── go_ising_classical.py   # M1 Hamiltonian, energy map, kernel config
│   ├── go_entropy.py           # Shannon, Boltzmann entropy, T_eff
│   ├── go_game_engine.py       # Go rules engine + SGF parser
│   ├── go_visualization.py     # Grid and comparison plots
│   └── board_utils.py          # Board utilities
│
├── data/
│   └── sgf_partidas/           # Professional game records (SGF format)
│
├── results/                    # All generated figures and animations
│
├── analysis_patterns.py        # 19 opening patterns (Table I of paper)
├── compare_per_bond.py         # Bond-level energy functions (both models)
│
├── viz_interaction_comparison.py  # 4-panel bond interaction table
├── viz_entropy_comparison.py      # Shannon + Boltzmann + T_eff comparison
│
├── animation_game.py              # GIF: board + M1 energy overlay
├── animation_entropy_compare.py   # GIF: dual-model entropy evolution
│
├── analysis_game.py            # Game metrics analysis
├── analysis_patterns.py        # Pattern entropy analysis
├── visualize_dashboard.py      # Dashboard per model
├── visualize_energy_inventory.py
└── visualize_interactions.py
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
