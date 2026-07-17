# Diagrama de Hasse del Orden Parcial Pareto
## Interpretación matemática y estratégica para el juego de Go

*Experimento 06 — Familia de Hamiltonianos cúbicos*
*296 candidatos · 148 frentes · 475 relaciones de cobertura*

---

## 0. La familia de candidatos: ¿qué son estos Hamiltonianos?

### Go como sistema de espines

Cada intersección del tablero de Go tiene un valor de espín s ∈ {−1, 0, +1} (negro, vacío, blanco). La energía de interacción entre dos intersecciones vecinas i y j está dada por un **Hamiltoniano de par** H(sᵢ, sⱼ). La energía total del tablero es la suma sobre todos los pares adyacentes:

```
E = Σ_{<i,j>} H(sᵢ, sⱼ)
```

El modelo de evaluación estratégica se reduce completamente a la elección de H: qué tipo de vecindades favorece o penaliza.

### Por qué polinomios cúbicos

Sobre {−1, 0, +1}, se cumple x³ = x para todo x. Por eso los monomios de grado ≥ 3 en una sola variable no aportan información nueva. Los **monomios independientes** en (x,y) ∈ {−1,0,+1}² son exactamente 7 (sin contar la constante):

```
x,  y,  x²,  xy,  y²,  x²y,  xy²
```

Cualquier función H: {−1,0,+1}² → ℝ se expresa como combinación lineal de estos 7 términos. Esto hace que los polinomios cúbicos sean la **familia completa** — no existe una familia más general para este espacio de estados.

### La plantilla cubic_mixed

El experimento exploró la plantilla:

```
H(x,y) = a₁·x + a₂·y + b₁₁·x² + b₁₂·xy + b₂₂·y² + c₁₁₂·x²y + c₁₂₂·xy²
```

Los coeficientes se muestrearon aleatoriamente (seed=42, 300 muestras) con:
- a₁, a₂, b₁₁, b₁₂, b₂₂ ∈ [−3, 3]
- c₁₁₂, c₁₂₂ ∈ [−1, 1]

Cada nodo del diagrama de Hasse representa uno de los 296 candidatos que pasaron el filtro de calidad (de los 305 analizados, incluyendo 3 referencias: H_M1, Alvarado y el cúbico armónico).

### Qué mide cada criterio de calidad

Los 4 criterios del orden Pareto evalúan propiedades distintas e independientes:

| Criterio | Cómo se calcula | Qué mide para Go |
|----------|----------------|-----------------|
| **H₁_max** | Vida máxima de un generador H₁ en la filtración por subniveles de H sobre [−2,2]², normalizada por el rango | Capacidad del Hamiltoniano de detectar **estructuras cíclicas de influencia**: grupos que rodean a otros, cadenas de conexión, seki |
| **Robustez** | Fracción de 12 perturbaciones ±5% de los coeficientes que mantienen H₁_max > 0.20 | **Estabilidad estructural**: las propiedades del modelo no son artefactos de coeficientes exactos; funcionarán bajo ruido numérico o variación de parámetros |
| **ΔE** | H(x*,y*) máximo − H(x*,y*) mínimo sobre [−2,2]² | **Contraste energético**: separación entre las posiciones de máxima y mínima energía; mayor ΔE = mayor poder para discriminar posiciones fuertes de débiles |
| **n_A₁** | Número de puntos críticos con det(Hess H) < 0 (nodos de silla) | **Transiciones de régimen**: cada nodo A₁ es un valor crítico c* donde la topología de la fibra H⁻¹(c) cambia; más nodos = más puntos de inflexión estratégica en la partida |

Los dos primeros criterios (H₁_max, Robustez) miden riqueza y estabilidad topológica. Los dos últimos (ΔE, n_A₁) miden potencia discriminativa y complejidad estructural. Los 4 son genuinamente independientes: ningún candidato maximiza los 4 simultáneamente (de ahí que el poset no tenga supremo).

---

## 1. Qué es este diagrama

El diagrama de Hasse es la representación visual de un **orden parcial**: una forma de comparar candidatos que no obliga a elegir un único "mejor" sino que admite la existencia de múltiples óptimos incomparables entre sí.

Cada nodo del diagrama es un **Hamiltoniano polinómico cúbico** H(x,y) que asigna un valor de energía a cada configuración de espines de Go. La imagen dentro de cada nodo muestra la variedad Γ(H) = {z = H(x,y)} ⊂ ℝ³ — la "forma" topológica de ese Hamiltoniano.

---

## 2. La relación de orden: qué significa "dominar"

Cada candidato H tiene cuatro valores que miden su calidad como función de evaluación estratégica:

| Criterio | Símbolo | Qué mide |
|----------|---------|----------|
| Vida máxima H₁ | H₁_max | Ciclos topológicos en la fibración de Milnor — complejidad táctica |
| Robustez | Rob | Fracción de perturbaciones ±5% que mantienen al candidato activo |
| Rango energético | ΔE | H(máx) − H(mín) en [−2,2]² — contraste entre posiciones extremas |
| Nodos A₁ | n_A₁ | Puntos críticos de silla donde la fibra H⁻¹(c) cambia de topología |

Se dice que **H_i domina a H_j** si:

```
H_i ≥ H_j  en los 4 criterios simultáneamente
H_i > H_j  en al menos uno
```

Es decir: H_i es al menos igual de bueno en todo, y estrictamente mejor en algo. No existe ningún trade-off — H_i gana o empata en cada dimensión.

---

## 3. El algoritmo de capas (Pareto peeling)

El diagrama se construye por capas, como pelando una cebolla:

```
Frente 1 = { H : ningún otro H' domina a H }
           → eliminar Frente 1
Frente 2 = { H restante : ningún otro H' restante domina a H }
           → eliminar Frente 2
Frente k = repetir hasta vaciar el conjunto
```

Resultado en nuestros datos: **148 frentes** para 296 candidatos. La mayoría de frentes tienen 1-3 candidatos, lo que indica que el espacio de criterios es altamente diverso — casi cada Hamiltoniano tiene un perfil único en las 4 dimensiones.

---

## 4. Qué es una relación de cobertura (arista del Hasse)

No se dibuja una arista por cada par donde H_i domina a H_j. Solo se dibuja la **cobertura directa**: H_i cubre a H_j si:

```
H_i domina a H_j
Y no existe ningún H_k tal que:  H_i domina a H_k  y  H_k domina a H_j
```

Es decir: el paso de H_i a H_j es un salto irreducible — no hay intermediario. Esto da el diagrama más compacto que representa fielmente la estructura de dominancia.

El diagrama tiene **475 coberturas** entre 296 candidatos. Las aristas que cruzan muchos frentes de golpe (como las líneas doradas largas desde el Frente 1) representan saltos donde no existe ningún intermediario en ese subespacio de criterios.

---

## 5. Cómo leer el diagrama visualmente

### Posición vertical
- **Arriba** = Frente 1 (los mejores: nadie los domina)
- **Abajo** = Frentes tardíos (dominados por más y más candidatos)
- Cada nivel horizontal es un frente Pareto

### Posición horizontal
Dentro de cada frente, los nodos se colocan usando la **heurística baricéntrica**: cada nodo se alinea con el promedio horizontal de sus predecesores (los que lo dominan). Esto minimiza los cruces de aristas.

### Colores de las aristas

| Color | Frentes de origen | Significado |
|-------|:-----------------:|-------------|
| **Oro** (#FFD700) | F1 | Coberturas desde los 4 candidatos óptimos |
| **Cian** (#44DDFF) | F2 | Segundo nivel del orden |
| **Naranja** (#FF9944) | F3 | Tercer nivel |
| **Violeta** (#CC88FF) | F4–F8 | Frentes intermedios |
| **Verde menta** (#88FFAA) | F9–F20 | Zona media |
| **Azul acero** (#6699CC) | F21+ | Frentes tardíos |

### Los nodos
- **Versión 2D**: heatmap de H(x,y) — muestra la distribución de energía
- **Versión 3D**: superficie Γ(H) = {z=H(x,y)} — muestra la forma topológica
- **Estrellas naranjas** sobre la superficie: nodos A₁ (puntos de silla, transiciones críticas)
- **Borde dorado**: Frente 1 · **Borde cian**: Frente 2 · **Borde naranja**: Frente 3

---

## 6. Propiedades matemáticas del poset

### No existe supremo ni ínfimo

El **supremo** (elemento máximo) sería un candidato que dominara a todos los demás en los 4 criterios simultáneamente. Ese punto teórico tiene coordenadas:

```
sup teórico = (H₁=0.188, Rob=1.0, ΔE=50.9, A₁=2)
```

Ningún candidato de los 296 explorados alcanza esos cuatro valores a la vez. Por tanto **no existe supremo en el poset**.

El **ínfimo** tampoco existe: ningún candidato tiene los mínimos simultáneos en las 4 dimensiones.

### El poset no es una retícula

Para que el poset fuera una **retícula (lattice)**, todo par de elementos debería tener:
- Un **join** (cota superior mínima): el "menor" elemento que domina a ambos
- Un **meet** (cota inferior máxima): el "mayor" elemento dominado por ambos

Se verificó computacionalmente que **ninguno de los 6 pares del Frente 1** tiene un join dentro del poset. El join existiría solo en la completación teórica (el supremo externo). Por tanto el poset **no es retícula**.

### Teorema de Dilworth: 4 cadenas mínimas

El **Teorema de Dilworth** establece:

> En todo poset finito, el tamaño de la anticadena máxima = el mínimo número de cadenas necesarias para cubrir el poset.

La anticadena máxima es el Frente 1, con **4 elementos**. Por tanto:

**El poset se descompone en exactamente 4 cadenas.**

Estas 4 cadenas son las cuatro columnas aproximadamente verticales visibles en el diagrama de Hasse. Cada columna es una secuencia de candidatos donde cada uno domina al siguiente en al menos un criterio.

### Clasificación formal

El poset es un **poset finito sin cota superior ni inferior**, con:
- Anticadena máxima de tamaño 4 (Frente 1)
- Descomposición mínima en 4 cadenas (Dilworth)
- 148 antichains en su estratificación por frentes Pareto
- No es retícula (fallan join y meet para pares del Frente 1)

---

## 7. El Frente 1: los 4 candidatos óptimos de Pareto

```
H_0094 · score=0.459 · H₁=0.188, Rob=1.0, ΔE=31.3, A₁=1
H_0113 · score=0.456 · H₁=0.173, Rob=1.0, ΔE=35.4, A₁=1
H_0045 · score=0.454 · H₁=0.166, Rob=1.0, ΔE=43.4, A₁=2
H_0042 · score=0.417 · H₁=0.120, Rob=1.0, ΔE=33.5, A₁=2
```

Son mutuamente incomparables — forman una **anticadena**:

- H_0094 tiene el mayor H₁_max pero solo 1 nodo A₁
- H_0045 tiene el mayor ΔE y 2 nodos A₁ pero menor H₁
- H_0042 tiene 2 nodos A₁ (máximo) pero el menor H₁ del grupo
- H_0113 es intermedio en todo — ninguno lo domina

Ninguno es "el mejor" en todos los sentidos. Son los **mejores compromisos posibles** dado el espacio explorado.

---

## 8. Qué significa esto para el juego de Go

### La energía H(s₀, s₁) como función de evaluación

En el modelo spin de Go, cada intersección tiene un espín s ∈ {−1, 0, +1} (negro, vacío, blanco). El Hamiltoniano H(s₀, s₁) asigna una energía a cada par de intersecciones vecinas. Hamiltonianos con mayor riqueza topológica (H₁_max alto) pueden distinguir más finamente entre posiciones estratégicas.

### Qué significa cada criterio para la estrategia

**H₁_max — complejidad táctica:**
Mide el tiempo de vida del generador H₁ en la filtración de sublevel sets. Un H₁_max alto indica que la función de energía genera bucles topológicos persistentes al subir el umbral c. En términos de Go: el Hamiltoniano puede detectar **estructuras cíclicas de influencia** en el tablero — grupos que "rodean" a otros, cadenas de conexión, patrones de seki.

**Robustez — estabilidad del modelo:**
Un candidato robusto (Rob ≈ 1.0) mantiene su carácter cualitativo ante pequeñas variaciones de sus coeficientes. Los 4 del Frente 1 tienen Rob = 1.0: sus propiedades topológicas son **estructuralmente estables**, no artefactos de coeficientes precisos.

**ΔE — contraste energético:**
El rango H(máx) − H(mín) en [−2,2]² mide cuánto separa el Hamiltoniano las posiciones extremas. En Go: la diferencia energética entre una posición fuerte (conexión, territorio establecido) y una posición débil (grupos amenazados, ko). Mayor ΔE = **mayor poder discriminativo** entre posiciones buenas y malas.

**Nodos A₁ — transiciones estratégicas:**
Un nodo A₁ es un punto crítico donde det(Hess H) < 0 — una silla en la superficie de energía. Matemáticamente, al cruzar el valor crítico c* correspondiente, la fibra H⁻¹(c) cambia de topología: un toro (género 1) colapsa en una figura-8 (fibra singular). Estratégicamente, esto marca un **momento de cambio de régimen**: la estructura topológica del tablero cambia cualitativamente. Con 2 nodos A₁ (H_0042, H_0045), el modelo puede detectar **dos transiciones distintas** por partida.

### Las 4 cadenas de Dilworth y los 4 estilos de juego

La descomposición de Dilworth en 4 cadenas tiene una lectura estratégica:

```
Cadena 1 (H_0094 → ...): linaje con H₁ máximo — detecta estructuras cíclicas
Cadena 2 (H_0113 → ...): linaje equilibrado — compromiso entre todos los criterios  
Cadena 3 (H_0045 → ...): linaje con ΔE máximo y 2 A₁ — mayor contraste y sensibilidad
Cadena 4 (H_0042 → ...): linaje con A₁ múltiple — dos transiciones de régimen
```

Cada cadena representa una **familia de modelos relacionados por dominancia**: bajar en una cadena significa perder algo (un criterio se degrada) pero manteniendo el "estilo" general del modelo padre. Los candidatos de distintas cadenas son **estratégicamente incomparables**: sirven para propósitos distintos y no hay motivo matemático para preferir uno sobre otro sin contexto adicional.

### Los saltos largos en el diagrama (aristas que cruzan muchos frentes)

Las líneas doradas que cruzan 30-40 frentes de golpe revelan algo importante: entre H_0094 (Frente 1) y ciertos candidatos del Frente 40, **no existe ningún candidato intermedio** que domine a uno y sea dominado por el otro en los 4 criterios. El espacio de Hamiltonianos cúbicos tiene "vacíos" — regiones donde no existen compromisos graduales entre ciertos perfiles de calidad.

En términos de Go: no siempre existe una secuencia de modelos de evaluación que transite suavemente entre "detecta bien los ciclos" y "detecta bien el contraste energético". A veces el salto es abrupto.

### Qué mide la geometría: consistencia, no corrección

Un punto crucial sobre la interpretación de los invariantes topológicos:

> **La geometría de la fibra no determina qué jugadas de Go son buenas o malas.  
> Lo que mide es si el Hamiltoniano es consistente en sus preferencias estratégicas a través del rango de temperatura relevante.**

El argumento: al variar la temperatura de T=∞ a T=0, el sistema recorre el intervalo de energías [E_min, E_max] sobre los 6 pares Go. Un **nodo A₁ dentro de ese intervalo** (c* ∈ [E_min, E_max]) produce una **transición de fase estratégica**: la fibra H⁻¹(c) cambia de topología al cruzar c*, y el par más favorecido puede cambiar abruptamente. El modelo no sabe qué configuración preferir en la zona de la transición.

Un **nodo A₁ fuera del intervalo Go** (c* < E_min) garantiza que la preferencia varía de forma suave y monótona a medida que T→0: no hay saltos de régimen dentro del dominio estratégico.

| Situación del nodo A₁ | Efecto sobre la estrategia |
|---|---|
| c* < E_min (fuera, abajo) | Preferencia suave y monótona con T. Los 6 pares Go están en una sola zona topológica estable. Modelo **consistente**. |
| c* ∈ [E_min, E_max] (dentro) | Transición de fase: el par favorecido puede cambiar bruscamente al variar T. Modelo **inconsistente** en ese rango. |
| c* > E_max (fuera, arriba) | Todos los pares Go están por debajo de la transición: misma consistencia que el primer caso. |

**El Frente 1 es óptimo precisamente por esto.** Los 4 candidatos tienen sus nodos A₁ con c* ≪ E_min. El oval topológico que contiene todos los pares Go nunca cruza un valor crítico: la fibra H⁻¹(c) para c ∈ [E_min, E_max] es siempre suave y de la misma topología. La persistencia H₁ > 0 es el certificado cuantitativo de esta propiedad; la robustez = 1 garantiza que no depende de los coeficientes exactos.

Los candidatos de frentes bajos fallan porque alguno de sus nodos A₁ cae dentro del rango Go, introduciendo una inconsistencia térmica: a temperatura alta prefieren un par, a temperatura baja prefieren otro, con un cambio abrupto en el medio.

### El supremo ausente como objetivo de diseño

El hecho de que el supremo teórico `(H₁=0.188, Rob=1.0, ΔE=50.9, A₁=2)` no exista como candidato real es una guía de diseño: **ese punto es el Hamiltoniano ideal**. Ningún Hamiltoniano cúbico muestreado lo alcanza, lo que sugiere que:

1. El espacio de búsqueda necesita ampliarse (más muestras, otros templates)
2. O bien ese punto es matemáticamente imposible con polinomios cúbicos de la forma explorada
3. O se requiere una familia diferente (polinomios de grado 4, o combinaciones no lineales)

El diagrama de Hasse convierte esa imposibilidad en algo visible: el "vacío" en la cima del diagrama es el lugar donde debería estar el supremo pero no está.

---

## 9. Resumen

| Concepto | Significado matemático | Significado en Go |
|----------|----------------------|-------------------|
| Frente 1 | Anticadena de elementos maximales del poset | Los 4 Hamiltonianos con el mejor compromiso posible entre todos los criterios |
| Arista del Hasse | Cobertura directa: dominancia sin intermediario | Salto irreducible de calidad entre dos modelos de evaluación |
| 148 frentes | Estratificación del poset | 148 niveles de calidad estratégica |
| 4 cadenas (Dilworth) | Descomposición mínima del poset en cadenas totales | 4 "linajes" de modelos relacionados por dominancia — 4 estilos de evaluación |
| Sin supremo | No existe elemento que domine a todos | No existe el Hamiltoniano perfecto en el espacio explorado |
| Sin ínfimo | No existe elemento dominado por todos | No existe el peor Hamiltoniano absoluto |
| No es retícula | Los joins no existen dentro del poset | No siempre hay un "mejor compromiso" entre dos modelos incomparables |
| Nodo A₁ | Punto de silla: det(Hess H) < 0 | Transición crítica donde la topología del tablero cambia cualitativamente |
| H₁_max alto | Ciclos topológicos persistentes en la fibración | Capacidad de detectar estructuras cíclicas de influencia en el tablero |
| ΔE alto | Gran rango en [−2,2]² | Alto poder discriminativo entre posiciones fuertes y débiles |

---

*Pipeline: `experiments/06_hamiltonian_families/`*
*Figuras: `output/figures/hasse_diagram.png` (2D) · `output/figures/hasse_diagram_3d.png` (3D)*
*Catálogo: `output/catalog.json` · 305 entradas totales*
