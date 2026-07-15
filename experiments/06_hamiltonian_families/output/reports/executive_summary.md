# La familia de polinomios Go y sus variedades asociadas
## Informe ejecutivo — Fibración de Milnor en estrategia de Go

*Generado automáticamente · 2026-07-14*
*Catálogo: 305 Hamiltonianos (5 referencias + 300 candidatos) · 296 pasan el filtro*

---

## Resumen de la búsqueda

Plantillas exploradas:
  - `cubic_mixed`: 300 muestras
  - `h_m1`: 2 muestras
  - `quadratic`: 2 muestras
  - `sym_cubic`: 1 muestras

| Métrica              | Valor  |
|----------------------|--------|
| Total analizados     | 305  |
| Pasan el filtro      | 296   |
| Tasa de éxito        | 97.0 % |
| Top candidatos       | 10   |

---

## Top 10 candidatos

| ID | Template | Expresión | A₁ | Δc | ΔE | Rob. | Mejora | p-val | Score |
|---|---|---|:---:|:---:|:---:|:---:|:---:|:---:|:---:|
| H_0094 | cubic_mixed | `-0.781435417770884*x**2*y - 2.77817563` | 1 | 9.914 | 31.3 | 1.000 | +0.0000 | — | **0.4593** |
| H_0022 | cubic_mixed | `0.850240236753594*x**2*y - 2.379582193` | 1 | 16.779 | 23.5 | 1.000 | +0.0000 | — | **0.4575** |
| H_0113 | cubic_mixed | `-0.778741064875593*x**2*y - 2.94444130` | 1 | 22.326 | 35.4 | 1.000 | +0.0000 | — | **0.4559** |
| H_0045 | cubic_mixed | `0.849683738036124*x**2*y - 2.389968582` | 2 | 13.381 | 43.4 | 1.000 | +0.0000 | — | **0.4544** |
| H_0275 | cubic_mixed | `0.697584226272177*x**2*y - 2.670390064` | 1 | 20.716 | 33.5 | 1.000 | +0.0000 | — | **0.4540** |
| H_0168 | cubic_mixed | `-0.692948955890772*x**2*y - 2.13654782` | 1 | 8.888 | 29.3 | 1.000 | +0.0000 | — | **0.4213** |
| H_0042 | cubic_mixed | `-0.650717058128295*x**2*y - 2.30705961` | 2 | 5.229 | 50.9 | 1.000 | +0.0000 | — | **0.4171** |
| H_0104 | cubic_mixed | `0.122978788828769*x**2*y - 2.067350615` | 1 | 4.593 | 26.2 | 1.000 | +0.0000 | — | **0.4126** |
| H_0222 | cubic_mixed | `-0.745447603341922*x**2*y - 2.11544427` | 2 | 2.430 | 25.7 | 1.000 | +0.0000 | — | **0.4113** |
| H_0301 | cubic_mixed | `0.349625504811739*x**2*y - 1.798899416` | 0 | ∞ | 31.5 | 1.000 | +0.0000 | — | **0.4074** |

> **A₁**: nodos A₁ detectados · **Δc**: separación mínima entre c* ·
> **ΔE**: rango energético en [−2,2]² · **Rob.**: fracción de perturbaciones ±5% estables

---

## Criterios de selección

Un candidato pasa si cumple **al menos 2 de 3**:

| Criterio       | Umbral  | Qué mide                                      |
|----------------|:-------:|-----------------------------------------------|
| H₁_max (τ₁)   | > 0.20 | Loops topológicos en subniveles de H          |
| ΔE             | > 0.50 | Rango energético (profundidad del pozo)       |
| δ_crit         | > 0.30 | Separación mínima entre valores críticos c*   |

**Score total** = 0.45 × TDA + 0.30 × Robustez + 0.25 × Mejora estratégica

---

## Invariantes matemáticos

| Invariante         | Definición                              | Rol en Go                        |
|--------------------|-----------------------------------------|----------------------------------|
| Nodo A₁            | det(Hess H) < 0 en punto crítico        | Fibra singular → tensión crítica |
| Número de Milnor μ | # nodos A₁; μ ≤ (d−1)²                 | Complejidad topológica           |
| Genus g de fibra   | g=(d−1)(d−2)/2; cúbico → g=1 (toro)    | Tipo topológico de cada estado   |
| c* (valor crítico) | H(punto crítico)                        | Umbral de cambio topológico      |
| Separación Δc      | min|c*ᵢ − c*ⱼ|                          | Resolución entre regímenes       |

---

*Pipeline: `experiments/06_hamiltonian_families/` · Catálogo: `output/catalog.json`*