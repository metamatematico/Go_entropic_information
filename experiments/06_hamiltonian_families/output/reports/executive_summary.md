# La familia de polinomios Go y sus variedades asociadas
## Informe ejecutivo — Fibración de Milnor en estrategia de Go

*Generado automáticamente · 2026-07-15*
*Catálogo: 305 Hamiltonianos (5 referencias + 300 candidatos) · 296 pasan el filtro*

---

## La familia Go de Hamiltonianos cúbicos

### El modelo de espín en Go

En el modelo de espín de Go, cada intersección del tablero tiene un valor s ∈ {−1, 0, +1}:

| Espín | Significado |
|-------|-------------|
| s = −1 | Piedra negra |
| s = 0 | Intersección vacía |
| s = +1 | Piedra blanca |

Un **Hamiltoniano de interacción** H(sᵢ, sⱼ) asigna una energía a cada par de intersecciones vecinas (i, j). La energía total del tablero en una configuración dada es la suma sobre todos los pares adyacentes:

```
E = Σ_{<i,j>} H(sᵢ, sⱼ)
```

Solo existen 6 pares orientados relevantes (excluimos la dirección inversa como independiente):

`(−1,−1)  (−1,0)  (−1,1)  (1,−1)  (1,0)  (1,1)`

Estos 6 valores determinan completamente el comportamiento estratégico del modelo: cómo penaliza o favorece cada tipo de vecindad negro–negro, negro–vacío, negro–blanco, etc.

### ¿Por qué polinomios? La base canónica en {−1, 0, +1}

Sobre el conjunto discreto {−1, 0, +1}, todo polinomio en x satisface la identidad:

```
x³ = x   para todo x ∈ {−1, 0, +1}
```

(verificar: (−1)³=−1, 0³=0, 1³=1). Esto implica que los monomios de grado ≥ 3 en una misma variable son linealmente dependientes de los de menor grado. Los monomios **independientes** en (x,y) ∈ {−1,0,+1}² son exactamente:

```
1,  x,  y,  x²,  xy,  y²,  x²y,  xy²
```

Descartando el término constante (desplaza la energía globalmente sin efecto estratégico relativo), obtenemos **7 monomios base**. Cualquier función H: {−1,0,+1}² → ℝ puede expresarse como combinación lineal de estos 7 términos. Los polinomios cúbicos son, en este sentido, **la familia más general posible** de Hamiltonianos de interacción por par para Go.

### La plantilla cubic_mixed: el espacio completo de 7 parámetros

```
H(x,y) = a₁·x + a₂·y + b₁₁·x² + b₁₂·xy + b₂₂·y² + c₁₁₂·x²y + c₁₂₂·xy²
```

Cada coeficiente controla una dimensión independiente de la interacción:

| Parámetro | Monomio | Rol estratégico |
|-----------|---------|----------------|
| a₁ | x | Tendencia lineal de la piedra i (favorece negro o blanco puro) |
| a₂ | y | Tendencia lineal de la piedra j |
| b₁₁ | x² | Energía cuadrática de i — vale igual para −1 y +1 (simétrica en color) |
| b₁₂ | xy | Interacción directa i–j — el núcleo Ising clásico |
| b₂₂ | y² | Energía cuadrática de j |
| c₁₁₂ | x²y | Interacción cruzada: el color de j modulado por si i es vacío o no |
| c₁₂₂ | xy² | Interacción cruzada: el color de i modulado por si j es vacío o no |

Los términos c₁₁₂ y c₁₂₂ son los que generan **asimetría direccional**: distinguen si la piedra relevante está en la posición i o en j del par orientado. El modelo H_M1 de Mercado & Jiménez es exactamente este mecanismo con a₁=1, a₂=2, b₁₂=0, c₁₁₂=−1, c₁₂₂=−1.

### Los Hamiltonianos de referencia

Tres miembros especiales fijan el marco de comparación:

| ID | Expresión | Plantilla | Por qué es referencia |
|----|-----------|-----------|----------------------|
| H_M1 | x + 2y − xy² − x²y | sparse_cubic | Modelo asimétrico con vacío activo; Mercado & Jiménez |
| Alvarado | xy | quadratic | Modelo simétrico canónico con vacío invisible; Atomic-Go (Rojas-Domínguez et al., 2019) |
| Armónico | x³+y³ − 3xy − 3(x²y+xy²) | sym_cubic | Función armónica (Δf=0) y simétrica f(x,y)=f(y,x); 2 nodos A₁ |

### ¿Por qué 300 muestras aleatorias?

El espacio de coeficientes de cubic_mixed es ℝ⁷. Un muestreo en cuadrícula con solo 3 valores por eje daría 3⁷ = 2187 combinaciones, con alta redundancia. El muestreo aleatorio uniforme cubre el espacio de forma más eficiente:

- a₁, a₂, b₁₁, b₁₂, b₂₂ ∈ [−3, 3]  (términos dominantes)
- c₁₁₂, c₁₂₂ ∈ [−1, 1]  (términos cúbicos — perturbación del núcleo cuadrático)

Con semilla fija (seed=42) el muestreo es completamente reproducible. Los rangos reflejan que los términos cúbicos actúan como correcciones de interacción de tercer orden, no como el término dominante de la energía.

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
| Top candidatos       | 5   |

---

## Top 5 candidatos

| ID | Template | Expresión | A₁ | Δc | ΔE | Rob. | Mejora | p-val | Score |
|---|---|---|:---:|:---:|:---:|:---:|:---:|:---:|:---:|
| H_0094 | cubic_mixed | `-0.781435417770884*x**2*y - 2.77817563` | 1 | 9.914 | 31.3 | 1.000 | +0.0000 | — | **0.4593** |
| H_0022 | cubic_mixed | `0.850240236753594*x**2*y - 2.379582193` | 1 | 16.779 | 23.5 | 1.000 | +0.0000 | — | **0.4575** |
| H_0113 | cubic_mixed | `-0.778741064875593*x**2*y - 2.94444130` | 1 | 22.326 | 35.4 | 1.000 | +0.0000 | — | **0.4559** |
| H_0045 | cubic_mixed | `0.849683738036124*x**2*y - 2.389968582` | 2 | 13.381 | 43.4 | 1.000 | +0.0000 | — | **0.4544** |
| H_0275 | cubic_mixed | `0.697584226272177*x**2*y - 2.670390064` | 1 | 20.716 | 33.5 | 1.000 | +0.0000 | — | **0.4540** |

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

## Consistencia topológica vs. corrección estratégica

> **La topología de la fibra no dice qué jugadas de Go son objetivamente buenas.  
> Dice qué Hamiltonianos son consistentes en sus preferencias estratégicas a través del rango de temperatura.**

Al variar la temperatura de T=∞ a T=0, el sistema recorre el intervalo [E_min, E_max] sobre los 6 pares Go. Un **nodo A₁ dentro de ese intervalo** produce una transición de fase: el par más favorecido puede cambiar abruptamente. Un **nodo A₁ fuera del intervalo** (c* < E_min) garantiza que la preferencia varía suavemente — el modelo es predecible.

| Nodo A₁ respecto a [E_min, E_max] | Efecto |
|---|---|
| c* < E_min (fuera) | Preferencia monótona y suave. Modelo **consistente**. |
| c* ∈ [E_min, E_max] (dentro) | Transición de fase estratégica. Modelo **inconsistente**. |

Los candidatos del **Frente 1** tienen todos sus nodos A₁ con c* ≪ E_min: el oval topológico que contiene los 6 pares Go nunca cruza un valor crítico. La persistencia H₁ > 0 certifica esta consistencia; robustez = 1.0 garantiza que no depende de coeficientes exactos. Los modelos de frentes bajos fallan porque algún nodo A₁ cae dentro del rango Go, introduciendo una inconsistencia térmica.

---

*Pipeline: `experiments/06_hamiltonian_families/` · Catálogo: `output/catalog.json`*