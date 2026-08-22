# Go Ising — Entropic Information Analysis

Comparative analysis of two classical Ising models applied to the game of Go.
Computes bond-level interaction energies, Shannon entropy, Boltzmann entropy, and
effective temperature for 19 standard opening patterns and real professional games.

---

## Guía conceptual — léase primero

Esta sección explica, sin suponer conocimiento previo de física estadística ni de Go, qué
se está haciendo y por qué. El resto del README es referencia técnica.
Versión extendida: [`docs/reporte_conceptual_07_08.md`](docs/reporte_conceptual_07_08.md).

### 1. La pregunta

El objeto central del Go no es una pieza: es el **espacio vacío**. Ganar consiste en
rodear más territorio —intersecciones vacías controladas— que el rival. Ese control es una
propiedad difusa: hay zonas cuyo dueño ya es inapelable (*territorio asentado*) y zonas
grandes, delimitadas por piedras propias pero todavía invadibles, que son una promesa en
disputa (*moyo*).

La intuición que funda el proyecto es que esa influencia se comporta como un **campo
físico**: cada piedra irradia control que decae con la distancia, las influencias opuestas
compiten, y lo que ocurre en cada punto vacío emerge del balance colectivo. La física
estadística tiene un lenguaje hecho para eso —el modelo de Ising— y la pregunta, formulada
de manera falsable, es:

> ¿Un Hamiltoniano clásico de Ising captura algo **real** del territorio de Go, más allá de
> lo que ya explica la pura geometría del tablero?

No se trata de igualar a un motor de Go —que hace lectura táctica completa—, sino de saber
si un campo clásico de pocos parámetros agrega poder predictivo genuino por encima de lo
obvio.

### 2. Hamiltoniano y "modelo de Ising" no son lo mismo

Es la confusión más frecuente al leer este repositorio, y conviene despejarla antes de
seguir.

Un **Hamiltoniano** es simplemente una función que le asigna una energía a cada
configuración de un sistema. No es una fórmula concreta: es un *rol*. Su importancia viene
de que, una vez que se tiene, la mecánica estadística dice qué observar: la probabilidad de
una configuración decae exponencialmente con su energía —el peso de Boltzmann `exp(-H/T)`—
y de ahí sale todo lo medible.

El **modelo de Ising** es *una elección particular* de Hamiltoniano, la más simple que
describe imanes:

```
H_total = -J · Σ_⟨i,j⟩ s_i · s_j        con  s_i ∈ {−1, +1}
```

Es decir: "Ising" nombra la **forma funcional** del acoplamiento —el producto `s_i·s_j`—,
no el concepto de energía. Hablar de "el polinomio de Ising" mezcla las dos cosas: lo que
existe es un Hamiltoniano *cuyo acoplamiento* es bilineal.

Este proyecto **conserva la estructura de Hamiltoniano de Ising** (una suma de energías
sobre pares de vecinos) y **generaliza únicamente la función de acoplamiento**:

```
H_total = Σ_⟨i,j⟩ H(s_i, s_j)

H(x,y) = a₁x + a₂y + b₁₁x² + b₁₂xy + b₂₂y² + c₁₁₂x²y + c₁₂₂xy²
```

Sigue siendo, formalmente, un Hamiltoniano de Ising clásico. Solo que el acoplamiento es
más rico que el simple producto. El modelo es **enteramente clásico** en todo el proyecto,
nunca cuántico.

### 3. Por qué un Hamiltoniano cúbico es legítimo — y qué gana

**Por qué se puede.** Nada en la mecánica estadística exige que la energía sea bilineal.
Los requisitos son dos: que `H` sea una función real bien definida de la configuración, y
que `exp(-H/T)` sea normalizable. Aquí el espacio de configuraciones es **finito** —cada
intersección toma un valor en `{−1, 0, +1}` sobre un tablero de 19×19—, así que la función
de partición es una suma finita y está siempre bien definida. **Cualquier** función real es
un Hamiltoniano legítimo sobre este espacio. La restricción bilineal del Ising de libro de
texto no es una ley: es una elección de modelado heredada del magnetismo.

**Por qué hace falta.** El acoplamiento `s_i·s_j` solo sabe expresar "alinéate o no te
alinees", y arrastra dos propiedades que el magnetismo quiere pero el Go no:

| Propiedad de `s_i·s_j` | En un imán | En Go |
|---|---|---|
| Simétrico bajo inversión de signo: `(−s_i)(−s_j) = s_i·s_j` | correcto: norte y sur son intercambiables | **problema**: una posición concreta no es simétrica entre negro y blanco |
| El vacío no existe; con `s = 0` la energía es 0 siempre | no aplica | **problema**: el vacío es *el objeto del juego* — el territorio ES espacio vacío |

Con el modelo de Alvarado (`H = xy`), una intersección vacía aporta exactamente cero: el
vacío es **invisible**. Los términos lineales y cúbicos rompen justamente esas dos
limitaciones — los términos lineales `x`, `y` hacen que el vacío **cargue energía**, y los
términos impares en color permiten **distinguir negro de blanco**. Eso es exactamente lo
que el Go necesita y el magnetismo no.

**Por qué grado 3 y no más.** No es arbitrario: es *completo*. Sobre `s ∈ {−1, 0, +1}` vale
la identidad `s³ = s`, así que subir el grado en una misma variable no agrega ninguna
función nueva. Un par de espines tiene 3 × 3 = 9 estados posibles, de modo que el espacio
de **todas** las interacciones de pares imaginables es un espacio vectorial de dimensión
exactamente 9, con base

```
{ 1,  x,  x²,  y,  y²,  xy,  x²y,  xy²,  x²y² }
```

La plantilla `cubic_mixed` de 7 parámetros cubre **7 de esas 9 dimensiones**. Las dos que
faltan son la constante `1` —físicamente irrelevante, porque desplaza todas las energías
por igual y se cancela en el peso de Boltzmann— y el término `x²y²`, que actúa como
indicador de "ambas intersecciones ocupadas".

> **Consecuencia abierta, verificada simbólicamente.** Bajo la simetrización que usa el
> predictor, `x²y²` **sí es visible**: cae en la pieza `P₊₊` de la descomposición de Klein
> (ver Experimento 08, más abajo). Las búsquedas de coeficientes realizadas hasta ahora
> exploran 4 dimensiones efectivas, cuando el espacio que el campo puede ver tiene **5**.
> Explorar la quinta es una extensión natural y todavía no hecha.

### 4. De dónde salen los dos polinomios de partida

El proyecto no empezó eligiendo polinomios al azar. Partió de dos Hamiltonianos de origen
independiente, que representan las dos posturas opuestas sobre cómo tratar el vacío y el
color:

| | **Alvarado** — Atomic-Go | **M1** — Mercado Sánchez & Jiménez Martínez |
|---|---|---|
| Fórmula | `H(x,y) = xy` | `H(x,y) = x + 2y − x²y − xy²` |
| Origen | Rojas-Domínguez, Barradas-Bautista & Alvarado (2019), *IEEE Access* | derivación teórica previa del grupo |
| Valores de enlace | `{−1, 0, +1}` | `{−2, −1, 0, +1, +2}` |
| Orden de los argumentos | simétrico: `H(i→j) = H(j→i)` | **asimétrico** en 6 de 9 pares |
| El vacío | **invisible**: `H(0,y) = 0` siempre | **activo**: `H(0,y) ≠ 0` |
| Grado | 2 — Ising puro | 3 |

Son, respectivamente, el caso mínimo y un caso deliberadamente enriquecido. Y resultaron
ser el punto de partida correcto por una razón empírica que solo apareció después: de todos
los candidatos probados —incluidos 69 generados al azar—, **únicamente estos dos
mejoraban** al ampliar el radio de interacción, en lugar de degradarse. Esa anomalía es la
que motivó abandonar el muestreo aleatorio y pasar a **optimizar coeficientes directamente**
dentro de la familia cúbica que ambos habitan.

Dicho de otro modo: Alvarado y M1 no son dos modelos rivales a comparar, sino **dos puntos
conocidos dentro de un espacio continuo** que el proyecto se dedica a explorar. Ambos son
casos particulares de `cubic_mixed`.

### 5. Por qué usamos KataGo, y qué devuelve realmente

**Por qué hace falta un motor.** Para hacer ciencia sobre el territorio se necesita una
verdad de terreno: un número objetivo que diga cuánto controla cada color cada zona. Y aquí
está la dificultad de fondo: **a mitad de partida, el territorio no es decidible por las
reglas.** No es un hecho del tablero presente, es una *predicción sobre cómo terminará la
partida*. Las reglas del Go determinan el territorio solo al final, tras el conteo. No hay
fórmula, ni árbitro, ni tabla que lo resuelva antes.

Por eso se usa un motor de fuerza sobrehumana. **KataGo no es "la verdad" del Go — es el
mejor estimador disponible**, y se trata como cualquier ciencia experimental trata su
instrumento: se cuantifica su ruido, se verifica que las conclusiones no dependan de una
corrida particular, y se reporta la incertidumbre.

**Qué devuelve, literalmente.** Verificado sobre la instalación de este repositorio
(KataGo v1.16.5, red `kata1-b15c192`), el modo `analysis` responde con:

| Bloque | Contenido |
|---|---|
| raíz | `ownership` (361 números), `ownershipStdev`, `policy`, `moveInfos`, `rootInfo`, `turnNumber` |
| `rootInfo` | 18 campos numéricos: `winrate`, `scoreLead`, `scoreStdev`, `utility`, `visits`, … |
| `moveInfos` | 21 campos por jugada candidata: `prior`, `lcb`, `pv`, `ownership` por jugada, … |

**Ninguno de esos campos es un objeto de Go.** No existe una clave `moyo`, ni `joseki`, ni
`shape`, ni `influence`. No hay ninguna salida donde KataGo nombre una estructura del
juego. Lo que hay son **números por intersección y por jugada**.

La única excepción en todo el motor está en la interfaz GTP, no en `analysis`: el comando
`final_status_list` acepta exactamente tres argumentos —`dead`, `alive`, `seki`— y ahí sí el
motor se compromete con una **etiqueta discreta** del juego. Es la única categorización de
Go que KataGo emite por sí mismo.

### 6. Cómo llegamos nosotros a "moyo"

Entonces, ¿cómo sabe KataGo qué es un moyo? **No lo sabe, y no lo dice.**

Lo que la red aprendió es algo más simple y más útil: su cabeza de *ownership* está
entrenada para predecir, en cada una de las 361 intersecciones, **quién será el dueño de
ese punto al final de la partida**, en una escala continua de `−1` (negro) a `+1` (blanco).
Es un campo escalar. La red nunca vio la palabra "moyo" ni ningún concepto de Go nombrado:
aprendió a estimar un número por punto a partir de millones de partidas.

El moyo aparece en el paso siguiente, y es **construcción nuestra**
([`moyo_detector.py`](experiments/07_moyo_dataset/src/moyo_detector.py)):

1. Se toma el mapa de `ownership` que devuelve el motor.
2. Se agrupan los puntos **vacíos** por inundación (*flood-fill*) en regiones conexas.
3. Cada región se clasifica según su `ownership` promedio, contra umbrales **que elegimos
   nosotros**: `|own| > 0.85` → territorio asentado; `0.15 ≤ |own| ≤ 0.85` → **moyo**;
   `|own| < 0.15` → neutral (*dame*). Tamaño mínimo de región: 4 puntos.
4. La etiqueta a predecir, `pct_black`, es el porcentaje de control negro de la región,
   derivado del mismo campo.

Es decir: **"moyo" es un constructo operacional** —una región conexa de puntos vacíos cuyo
promedio de `ownership` cae en una banda elegida—, no una salida del motor. Los umbrales
`0.85` y `0.15` son decisiones de diseño, no hechos del Go ni de KataGo.

Lo mismo, en distinto grado, vale para las demás categorías del pipeline:

| Categoría | Quién define la **región** | Quién pone la **etiqueta** |
|---|---|---|
| moyo | nuestros umbrales sobre `ownership` | `ownership` |
| territorio | nuestros umbrales sobre `ownership` | `ownership` |
| fuseki | los mismos umbrales, en jugadas 3–15 % | `ownership` |
| joseki | **geometría pura: las 4 esquinas**; el motor no interviene | `ownership` |

Joseki es el caso extremo: esas regiones existirían igual sin motor. Ninguna de las cuatro
es una categoría de KataGo.

### 7. Qué queda licenciado afirmar

**Sí:** *un campo de Ising clásico predice, mejor que la geometría del tablero, el
`ownership` medio de las regiones vacías conexas dentro de una banda dada.* Ese es el
resultado, y es sólido: ΔR² = 0.44 sobre partidas nunca vistas por ninguna búsqueda, para
un modelo completo con R² = 0.73 (r ≈ 0.86).

**Todavía no:** *"el Hamiltoniano predice el moyo"* como concepto de Go, porque ahí "moyo"
es una elección de umbral. La prueba que falta es de **sensibilidad a los umbrales**: si
ΔR² aguanta mover `0.85` / `0.15` / tamaño mínimo, el constructo es robusto; si se mueve,
parte del resultado es artefacto de la banda elegida.

Esa prueba está hoy **bloqueada por una decisión de diseño del cache**: se guardaron las
regiones ya clasificadas pero **no el `ownership` crudo**, de modo que reclasificar exige
volver a correr el motor en vez de reprocesar. Queda anotado como el arreglo prioritario de
la próxima corrida de KataGo — son ~120 posiciones × 361 flotantes, kilobytes.

Hay evidencia de que la advertencia es pertinente: al comparar dos corridas del motor sobre
**los mismos tableros** con distinto presupuesto de búsqueda (`maxVisits` 250 contra 600),
solo **131 de 262 regiones** conservan el mismo conjunto de puntos, mientras que allí donde
la región coincide las etiquetas son casi idénticas (r = 0.974, mediana de diferencia 0.3
puntos porcentuales). Es decir: **lo inestable es la capa de interpretación, no la
medición.** El `ownership` de KataGo es estable; el flood-fill con umbral fijo sobre un
campo continuo con ruido no lo es.

### 8. Los dos experimentos activos, en una frase cada uno

- **Experimento 07 — empírico.** Corre KataGo sobre 20 partidas profesionales, deriva las
  regiones, y mide cuánto agrega el campo del Hamiltoniano por encima de la geometría
  (ΔR²). Es donde se buscan y validan coeficientes.
- **Experimento 08 — teórico.** No corre KataGo ni predice nada nuevo: explica, con teoría
  de representaciones del grupo de Klein, **por qué** el campo solo puede ver 4 de los 7
  coeficientes del polinomio. Nació de una anomalía encontrada dentro del 07 y le devolvió
  el favor: esa garantía es la que hizo posible el mejor resultado empírico del proyecto.

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

    └── 07_moyo_dataset/            # Predicción de moyo/territorio contra KataGo real
        ├── src/
        │   ├── katago_engine.py        # Wrapper del motor KataGo (modo analysis, JSON)
        │   ├── moyo_detector.py        # Flood-fill de regiones por banda de ownership
        │   ├── features.py             # board_features, relaxation_field (Boltzmann)
        │   ├── early_regions.py        # Muestreo de fuseki (3–15%) + regiones de joseki
        │   ├── cache_positions.py      # Corre KataGo 1 vez, cachea moyo/territorio
        │   ├── cache_early_positions.py# Idem para fuseki/joseki
        │   ├── optimize_coefficients.py# Fase A/B: differential_evolution sobre el cache
        │   ├── run_fase_b.py           # Fase B: búsqueda en las 4 dims. efectivas
        │   ├── analyze_results.py      # ΔR² incremental, bootstrap por partida
        │   └── calibration.py          # Ajusta el campo crudo contra pct_black real
        └── output/
            ├── cache_*.pkl                       # Caches de posiciones (KataGo corrido 1 vez)
            ├── hamiltonians_clasificados.{csv,json} # Los 307 Hamiltonianos: simetría, sesgo, tipo, ΔR²
            ├── *_calibration*.json               # Constantes de calibración por Hamiltoniano/nº de barridos
            └── reports/
                ├── informe_completo_07_08.tex        # Reporte unificado (exp. 07 + 08), fuente única de verdad
                ├── avance_experimento07.tex          # Reporte solo del exp. 07 (histórico)
                ├── hamiltonianos_clasificados.pdf     # Clasificación completa, formato legible
                ├── correlaciones_moyo.png             # Campo del Hamiltoniano vs. KataGo real
                └── comparacion_energia_vs_relajacion_*.mp4 # Energía pura vs. relajación de Boltzmann, mismo tablero
```

> **Nota**: el Experimento 08 (teoría de invariantes, por qué el campo solo ve 4 de 7
> parámetros) ya no tiene una carpeta/reporte propio separado — su derivación completa
> vive, actualizada, como Parte II de `informe_completo_07_08.tex` (ver más abajo). La
> versión standalone anterior quedó obsoleta y se eliminó para evitar dos fuentes de
> verdad divergentes.

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

### Estado: en pausa — no es un experimento fallido

**De qué trataba.** La hipótesis del Experimento 06 era razonable y estaba bien planteada:
si un Hamiltoniano `H(x,y)` define una superficie `z = H(x,y)`, entonces las propiedades
matemáticas *intrínsecas* de esa superficie —sus puntos críticos, sus nodos `A₁`, la fibra
de Milnor, la persistencia `H₁`— deberían decir algo sobre la calidad del modelo como
descripción del Go. Un Hamiltoniano con estructura crítica "rica" sería un mejor modelo.
Con esos invariantes se construyó un orden de Pareto sobre 305 candidatos cúbicos, con 148
frentes, y se llamó **Frente 1** a la élite teórica resultante.

**Por qué quedó en pausa.** La hipótesis era falsable, y resultó falsa — dos veces:

1. Contrastado contra el ΔR² real del Experimento 07, el Frente 1 no solo dejó de ser la
   élite: fue el grupo de **peor** desempeño (0.055 a radio 9, contra 0.152–0.170 de los
   grupos "medios" y "tardíos"). El criterio no era neutro: seleccionaba activamente en la
   dirección equivocada.
2. El Experimento 08 explicó **por qué** tenía que pasar eso. El predictor real
   (`relaxation_field`) solo ve la proyección σ-invariante de 4 dimensiones; el análisis
   topológico, al evaluar `H(x,y)` directamente sin simetrizar, mezclaba esas 4 dimensiones
   relevantes con 3 que son **ruido puro** para la predicción. Se repitió entonces el
   análisis sobre el *polinomio reducido* —el objeto que el campo realmente evalúa— y el
   resultado también fue nulo (|ρ| ≤ 0.21, p > 0.31).

**Por qué "en pausa" y no "descartado".** Tres razones concretas:

- **La infraestructura sobrevivió intacta y sostiene todo lo posterior.** El catálogo de
  305 candidatos con sus coeficientes, el código de puntos críticos, el visor interactivo y
  el diagrama de Hasse siguen siendo la base sobre la que corren los Experimentos 07 y 08.
  Nada de eso se perdió.
- **La prueba tuvo un rango muestral limitado.** Las correlaciones se calcularon sobre los
  44 candidatos que tenían ΔR² medido, y esos 44 son **mayoritariamente aleatorios
  débiles**. Una hipótesis puede fallar sobre una población pobre sin que eso resuelva la
  pregunta sobre una población bien elegida.
- **Ahora sí sabemos cómo clasificar los polinomios cúbicos.** Cuando se corrió el
  Experimento 06 no existía la descomposición de Klein: no había manera de saber qué
  dimensiones del polinomio son relevantes y cuáles invisibles. Hoy sí — y el criterio que
  sí funciona (el sesgo de color `β`, con ρ = −0.71 contra el desempeño real) apareció
  justamente de mirar la estructura de simetría, no la de puntos críticos.

**Cómo se retomaría.** La vía natural es reconstruir el catálogo clasificado por las
coordenadas efectivas `(Σa, Σb, b₁₂, Σc)` —y eventualmente la quinta dimensión `x²y²`
señalada en la Guía conceptual—, muestrear de forma equilibrada dentro de esas clases en
lugar de uniformemente en los 7 coeficientes crudos, y recién entonces preguntar si la
topología de la variedad reducida separa a los buenos de los malos. Sería la primera prueba
sobre una población construida a propósito, en vez de sobre lo que quedó del muestreo
aleatorio. **La rama está en pausa esperando esa clasificación, no cerrada por refutación
definitiva.**


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
| Color bias, classified for all 307 catalog Hamiltonians | ~66% never cross zero (locked to one color regardless of the board); only ~6% are genuinely color-balanced |
| Color-balanced Hamiltonians predict better (n=64 evaluated) | mean ΔR² 0.257 (balanced) vs. 0.148 (biased), Welch's t-test $p=0.0007$; confound (quadratic-term weight) ruled out via regression |
| $H_{0202}$ — random, never-optimized, happens to be balanced | ΔR²=0.4195 (moyo), 0.466 (fuseki), 0.458 (joseki) — ties/beats $H_{OPT\_B}$ across categories with **zero** deliberate search |

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
   irreducible characters. Projecting `cubic_mixed` onto each via the
   **Reynolds operator** $P_\chi(H)=\frac{1}{|G|}\sum_{g\in G}\chi(g)(g\cdot H)$
   — the standard representation-theory tool for decomposing a
   function under a finite symmetry group (the same machinery behind
   Fourier analysis and even/odd decomposition) — refines the 4
   surviving combinations without changing how many there are.
4. **τ also predicts color bias**, independently of the σ-reduction:
   Hamiltonians with $\Sigma a=\Sigma c=0$ respond identically to
   swapping which color is "+1", so their field is provably
   color-balanced; when they don't cancel, the field is provably
   biased toward one color. Verified against the full 307-candidate
   catalog and confirmed empirically that **color-balanced
   Hamiltonians predict real territory better** (Welch's t-test,
   $p=0.0007$) — motivating a proposed "Fase C" that searches only
   within the balanced region instead of the unrestricted 4D space.
5. **Practical payoff:** searching directly in the 4 effective
   dimensions instead of the 7 raw ones (used for Fase B, Experiment
   07) is provably lossless for this objective — not just empirically
   convenient.

Full derivation — Cayley table, character table, the corrected
decomposition showing $H_{M1}$ itself is *not* purely invariant, the
Reynolds-operator justification (idempotency + completeness from
character orthogonality), and the color-bias/balance investigation —
lives entirely in Part II of
[`experiments/07_moyo_dataset/output/reports/informe_completo_07_08.tex`](experiments/07_moyo_dataset/output/reports/informe_completo_07_08.tex);
there is no separate Experiment 08 report file anymore.

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

Comparison with: Rojas-Domínguez, Barradas-Bautista & Alvarado (2019), *Atomic-Go*. IEEE Access.
