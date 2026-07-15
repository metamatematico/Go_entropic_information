# Resumen ejecutivo: Familia de polinomios Go
*Generado: 2026-07-14*

## Descripción
Pipeline de búsqueda, análisis y validación de Hamiltonianos polinómicos
para modelar estrategia en Go mediante la teoría de la fibración de Milnor.

## Top 2 candidatos

| ID | Template | Expresión | H₁_max | Robustez | Mejora estratégica | Score |
|---|---|---|---|---|---|---|
| H_0000 | h_m1 | `-1.0*x**2*y - 1.0*x*y**2 + 1.0*x + 2.0*y` | 0.000 | 0.333 | 0.0000 | 0.1900 |
| H_0001 | quadratic | `x*y` | 0.000 | 0.000 | 0.0000 | 0.0900 |

## Criterios de filtrado
- Vida máxima H₁ normalizada > 0.20
- Profundidad de pozo ΔE > 0.50
- Separación entre valores críticos > 0.30
- Robustez: ≥80% de perturbaciones ±5% mantienen el score

## Invariantes clave
- **Nodo A₁**: punto crítico no degenerado → fibra singular (pinchada)
- **H₁ persistente**: agujero topológico en los subniveles → pozo estratégico
- **Fibración de Milnor**: familia {H⁻¹(c) : c ∈ ℝ} parametrizada por el hamiltoniano