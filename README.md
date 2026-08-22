# Go: información entrópica y axiomatización del juego

Investigación sobre si la estructura del juego de Go admite una descripción
matemática rigurosa, abordada por dos vías que convergen: **modelos de Ising
clásicos** que predicen el territorio real medido por un motor de IA, y un
**sistema axiomático** que define los conceptos del juego y da criterio para
decidir cuándo una definición es correcta.

Todo el proyecto es **clásico**, nunca cuántico.

---

## Índice

| Parte | Contenido |
|---|---|
| [Mapa del proyecto](#mapa-del-proyecto) | El arco completo y en qué estado está cada rama |
| [I. Guía conceptual](#parte-i--guía-conceptual-léase-primero) | Qué es un Hamiltoniano cúbico, de dónde salen los polinomios, qué devuelve KataGo |
| [II. Los dos modelos de partida](#parte-ii--los-dos-modelos-de-partida) | M1 y Alvarado |
| [III. El tronco (exp. 01–05)](#parte-iii--el-tronco-experimentos-0105) | Entropías, energías de enlace, temperatura efectiva |
| [IV. Experimento 06](#parte-iv--experimento-06-familias-de-hamiltonianos-y-orden-de-pareto) | Familias de Hamiltonianos y orden de Pareto — **en pausa** |
| [V. Experimentos 07 y 08](#parte-v--experimentos-07-y-08-predicción-de-moyo-y-su-fundamento-teórico) | Predicción de moyo contra KataGo, y la reducción de Klein |
| [VI. Experimento 09](#parte-vi--experimento-09-axiomatización-del-go) | **Axiomatización del Go** — la rama nueva |
| [Instalación y uso](#instalación) | Requisitos, estructura, comandos |

---

## Mapa del proyecto

```
Fases 01–05 — el tronco
  Entropías de Shannon y Boltzmann, energías de enlace, temperatura efectiva.
  19 patrones de apertura + 3 024 partidas profesionales.
  Caracteriza los modelos, pero no los pone a prueba contra territorio real.
        │
        ├──► Exp. 06 — variedades y orden de Pareto            [EN PAUSA]
        │      305 Hamiltonianos cúbicos ordenados por invariantes topológicos.
        │      La hipótesis era falsable y resultó falsa, dos veces.
        │      La infraestructura sobrevive y sostiene todo lo demás.
        │
        ├──► Exp. 07 — empírico                                 [ACTIVO]
        │      KataGo real sobre 20 partidas. ΔR² del campo del Hamiltoniano
        │      por encima de la geometría. Mejor resultado: ΔR² = 0.44 en
        │      hold-out, modelo completo R² = 0.73 (r ≈ 0.86).
        │            ▲   │
        │            │   ▼
        ├──► Exp. 08 — teórico                                  [ACTIVO]
        │      Grupo de Klein: por qué el campo solo ve 4 de los 7 coeficientes.
        │      Nació de una anomalía del 07 y le devolvió la garantía con la que
        │      el 07 encontró su mejor resultado.
        │
        └──► Exp. 09 — axiomatización                           [NUEVO]
               Sistema 𝔊 con 5 grupos de axiomas, 33 teoremas, y un catálogo de
               171 conceptos del Go como objetivos de derivación. Absorbe el
               campo de Ising como objeto definido, sujeto a una condición de
               consistencia comprobable — no como heurística paralela.
```

---

# Parte I — Guía conceptual (léase primero)

Esta parte explica, sin suponer conocimiento previo de física estadística, de
teoría de grupos ni de Go, qué se está haciendo y por qué.
Versión extendida: [`docs/reporte_conceptual_07_08.md`](docs/reporte_conceptual_07_08.md).

## 1. La pregunta

El objeto central del Go no es una pieza: es el **espacio vacío**. Ganar consiste
en rodear más territorio —intersecciones vacías controladas— que el rival. Ese
control es una propiedad difusa: hay zonas cuyo dueño ya es inapelable
(*territorio asentado*) y zonas grandes, delimitadas por piedras propias pero
todavía invadibles, que son una promesa en disputa (*moyo*).

La intuición que funda el proyecto es que esa influencia se comporta como un
**campo físico**: cada piedra irradia control que decae con la distancia, las
influencias opuestas compiten, y lo que ocurre en cada punto vacío emerge del
balance colectivo. La física estadística tiene un lenguaje hecho para eso —el
modelo de Ising— y la pregunta, formulada de manera falsable, es:

> ¿Un Hamiltoniano clásico de Ising captura algo **real** del territorio de Go,
> más allá de lo que ya explica la pura geometría del tablero?

No se trata de igualar a un motor de Go —que hace lectura táctica completa—,
sino de saber si un campo clásico de pocos parámetros agrega poder predictivo
genuino por encima de lo obvio.

## 2. Hamiltoniano y "modelo de Ising" no son lo mismo

Es la confusión más frecuente al leer este repositorio, y conviene despejarla
antes de seguir.

Un **Hamiltoniano** es simplemente una función que le asigna una energía a cada
configuración de un sistema. No es una fórmula concreta: es un *rol*. Su
importancia viene de que, una vez que se tiene, la mecánica estadística dice qué
observar: la probabilidad de una configuración decae exponencialmente con su
energía —el peso de Boltzmann `exp(-H/T)`— y de ahí sale todo lo medible.

El **modelo de Ising** es *una elección particular* de Hamiltoniano, la más
simple que describe imanes:

```
H_total = -J · Σ_⟨i,j⟩ s_i · s_j        con  s_i ∈ {−1, +1}
```

Es decir: "Ising" nombra la **forma funcional** del acoplamiento —el producto
`s_i·s_j`—, no el concepto de energía. Hablar de "el polinomio de Ising" mezcla
las dos cosas: lo que existe es un Hamiltoniano *cuyo acoplamiento* es bilineal.

Este proyecto **conserva la estructura de Hamiltoniano de Ising** (una suma de
energías sobre pares de vecinos) y **generaliza únicamente la función de
acoplamiento**:

```
H_total = Σ_⟨i,j⟩ H(s_i, s_j)

H(x,y) = a₁x + a₂y + b₁₁x² + b₁₂xy + b₂₂y² + c₁₁₂x²y + c₁₂₂xy²
```

Sigue siendo, formalmente, un Hamiltoniano de Ising clásico. Solo que el
acoplamiento es más rico que el simple producto.

## 3. Por qué un Hamiltoniano cúbico es legítimo — y qué gana

**Por qué se puede.** Nada en la mecánica estadística exige que la energía sea
bilineal. Los requisitos son dos: que `H` sea una función real bien definida de
la configuración, y que `exp(-H/T)` sea normalizable. Aquí el espacio de
configuraciones es **finito** —cada intersección toma un valor en `{−1, 0, +1}`
sobre un tablero de 19×19—, así que la función de partición es una suma finita y
está siempre bien definida. **Cualquier** función real es un Hamiltoniano
legítimo sobre este espacio. La restricción bilineal del Ising de libro de texto
no es una ley: es una elección de modelado heredada del magnetismo.

**Por qué hace falta.** El acoplamiento `s_i·s_j` solo sabe expresar "alinéate o
no te alinees", y arrastra dos propiedades que el magnetismo quiere pero el Go no:

| Propiedad de `s_i·s_j` | En un imán | En Go |
|---|---|---|
| Simétrico bajo inversión de signo: `(−s_i)(−s_j) = s_i·s_j` | correcto: norte y sur son intercambiables | **problema**: una posición concreta no es simétrica entre negro y blanco |
| El vacío no existe; con `s = 0` la energía es 0 siempre | no aplica | **problema**: el vacío es *el objeto del juego* — el territorio ES espacio vacío |

Con el modelo de Alvarado (`H = xy`), una intersección vacía aporta exactamente
cero: el vacío es **invisible**. Los términos lineales y cúbicos rompen justamente
esas dos limitaciones — los términos lineales `x`, `y` hacen que el vacío
**cargue energía**, y los términos impares en color permiten **distinguir negro
de blanco**.

**Por qué grado 3 y no más.** No es arbitrario: es *completo*. Sobre
`s ∈ {−1, 0, +1}` vale la identidad `s³ = s`, así que subir el grado en una misma
variable no agrega ninguna función nueva. Un par de espines tiene 3 × 3 = 9
estados posibles, de modo que el espacio de **todas** las interacciones de pares
imaginables es un espacio vectorial de dimensión exactamente **9**, con base

```
{ 1,  x,  x²,  y,  y²,  xy,  x²y,  xy²,  x²y² }
```

La plantilla `cubic_mixed` de 7 parámetros cubre **7 de esas 9 dimensiones**. Las
dos que faltan son la constante `1` —físicamente irrelevante, porque desplaza
todas las energías por igual y se cancela en el peso de Boltzmann— y el término
`x²y²`, que actúa como indicador de "ambas intersecciones ocupadas".

> **Consecuencia abierta, verificada simbólicamente.** Bajo la simetrización que
> usa el predictor, `x²y²` **sí es visible**: cae en la pieza `P₊₊` de la
> descomposición de Klein (Parte V). Las búsquedas de coeficientes realizadas
> hasta ahora exploran 4 dimensiones efectivas, cuando el espacio que el campo
> puede ver tiene **5**. Explorar la quinta está pendiente.

## 4. De dónde salen los dos polinomios de partida

El proyecto no empezó eligiendo polinomios al azar. Partió de dos Hamiltonianos
de origen independiente, que encarnan las dos posturas opuestas sobre las dos
preguntas del apartado anterior — qué hacer con el vacío y qué hacer con el color.
Ver la [Parte II](#parte-ii--los-dos-modelos-de-partida) para sus fórmulas y
propiedades.

Son, respectivamente, el caso mínimo y un caso deliberadamente enriquecido. Y
resultaron ser el punto de partida correcto por una razón empírica que solo
apareció después: de todos los candidatos probados —incluidos 69 generados al
azar— **únicamente estos dos mejoraban** al ampliar el radio de interacción, en
lugar de degradarse. Esa anomalía es la que motivó abandonar el muestreo
aleatorio y pasar a **optimizar coeficientes directamente**.

Dicho de otro modo: Alvarado y M1 no son dos modelos rivales a comparar, sino
**dos puntos conocidos dentro de un espacio continuo** que el proyecto explora.
Ambos son casos particulares de `cubic_mixed`.

## 5. Por qué usamos KataGo, y qué devuelve realmente

**Por qué hace falta un motor.** Para hacer ciencia sobre el territorio se
necesita una verdad de terreno: un número objetivo que diga cuánto controla cada
color cada zona. Y aquí está la dificultad de fondo: **a mitad de partida, el
territorio no es decidible por las reglas.** No es un hecho del tablero presente,
es una *predicción sobre cómo terminará la partida*. Las reglas del Go determinan
el territorio solo al final, tras el conteo.

Por eso se usa un motor de fuerza sobrehumana. **KataGo no es "la verdad" del
Go — es el mejor estimador disponible**, y se trata como cualquier ciencia
experimental trata su instrumento: se cuantifica su ruido y se reporta la
incertidumbre.

**Qué devuelve, literalmente.** Verificado sobre la instalación de este
repositorio (KataGo v1.16.5, red `kata1-b15c192`), el modo `analysis` responde con:

| Bloque | Contenido |
|---|---|
| raíz | `ownership` (361 números), `ownershipStdev`, `policy`, `moveInfos`, `rootInfo`, `turnNumber` |
| `rootInfo` | 18 campos numéricos: `winrate`, `scoreLead`, `scoreStdev`, `utility`, `visits`, … |
| `moveInfos` | 21 campos por jugada candidata: `prior`, `lcb`, `pv`, `ownership` por jugada, … |

**Ninguno de esos campos es un objeto de Go.** No existe una clave `moyo`, ni
`joseki`, ni `shape`, ni `influence`. Lo que hay son **números por intersección y
por jugada**.

La única excepción en todo el motor está en la interfaz GTP, no en `analysis`: el
comando `final_status_list` acepta exactamente tres argumentos —`dead`, `alive`,
`seki`— y ahí sí el motor se compromete con una **etiqueta discreta** del juego.

## 6. Cómo llegamos nosotros a "moyo"

¿Cómo sabe KataGo qué es un moyo? **No lo sabe, y no lo dice.**

Lo que la red aprendió es algo más simple: su cabeza de *ownership* está entrenada
para predecir, en cada una de las 361 intersecciones, **quién será el dueño de ese
punto al final de la partida**, en una escala continua de `−1` (negro) a `+1`
(blanco). Es un campo escalar. La red nunca vio la palabra "moyo" ni ningún
concepto de Go nombrado.

El moyo aparece en el paso siguiente, y es **construcción nuestra**
([`moyo_detector.py`](experiments/07_moyo_dataset/src/moyo_detector.py)):

1. Se toma el mapa de `ownership` que devuelve el motor.
2. Se agrupan los puntos **vacíos** por inundación (*flood-fill*) en regiones conexas.
3. Cada región se clasifica según su `ownership` promedio, contra umbrales **que
   elegimos nosotros**: `|own| > 0.85` → territorio asentado;
   `0.15 ≤ |own| ≤ 0.85` → **moyo**; `|own| < 0.15` → neutral (*dame*). Tamaño
   mínimo de región: 4 puntos.
4. La etiqueta a predecir, `pct_black`, es el porcentaje de control negro de la
   región, derivado del mismo campo.

Es decir: **"moyo" es un constructo operacional**, no una salida del motor. Los
umbrales `0.85` y `0.15` son decisiones de diseño.

| Categoría | Quién define la **región** | Quién pone la **etiqueta** |
|---|---|---|
| moyo | nuestros umbrales sobre `ownership` | `ownership` |
| territorio | nuestros umbrales sobre `ownership` | `ownership` |
| fuseki | los mismos umbrales, en jugadas 3–15 % | `ownership` |
| joseki | **geometría pura: las 4 esquinas**; el motor no interviene | `ownership` |

## 7. Qué queda licenciado afirmar

**Sí:** *un campo de Ising clásico predice, mejor que la geometría del tablero, el
`ownership` medio de las regiones vacías conexas dentro de una banda dada.* Ese es
el resultado, y es sólido: ΔR² = 0.44 sobre partidas nunca vistas por ninguna
búsqueda, para un modelo completo con R² = 0.73 (r ≈ 0.86).

**Todavía no:** *"el Hamiltoniano predice el moyo"* como concepto de Go, porque
ahí "moyo" es una elección de umbral. Falta la prueba de **sensibilidad a los
umbrales**, hoy bloqueada porque el cache guardó las regiones ya clasificadas pero
**no el `ownership` crudo**.

Hay evidencia de que la advertencia es pertinente: comparando dos corridas del
motor sobre **los mismos tableros** con distinto `maxVisits` (250 contra 600),
solo **131 de 262 regiones** conservan el mismo conjunto de puntos, mientras que
allí donde coinciden las etiquetas son casi idénticas (r = 0.974). **Lo inestable
es la capa de interpretación, no la medición.**

> Esta limitación es, precisamente, lo que motivó abrir el
> [Experimento 09](#parte-vi--experimento-09-axiomatización-del-go).

---

# Parte II — Los dos modelos de partida

### Modelo M1 — Mercado Sánchez & Jiménez Martínez

```
H(sᵢ, sⱼ) = sᵢ + 2sⱼ − sᵢ·sⱼ² − sᵢ²·sⱼ
```

- Espines: negro = −1, vacío = 0, blanco = +1
- 5 valores de enlace posibles: `{−2, −1, 0, +1, +2}`
- **Asimétrico**: `H(i→j) ≠ H(j→i)` en 6 de 9 pares
- **Vacío activo**: `H(0, xⱼ) ≠ 0` — las celdas vacías cargan energía
- Grado 3; plantilla `sparse_cubic` (sin términos `b`)

### Modelo Alvarado — Atomic-Go (Rojas-Domínguez, Barradas-Bautista & Alvarado, 2019)

```
H(xᵢ, xⱼ) = xᵢ · xⱼ        (µ = 0, wᵢⱼ = 1)
```

- Espines: negro = −1, vacío = 0, blanco = +1
- 3 valores de enlace posibles: `{−1, 0, +1}`
- **Simétrico**: `H(i→j) = H(j→i)` siempre
- **Vacío invisible**: `H(0, xⱼ) = 0` siempre
- Grado 2 — el acoplamiento de Ising puro

---

# Parte III — El tronco (experimentos 01–05)

Las primeras cinco fases establecieron la comparación entre M1 y Alvarado con
herramientas de mecánica estadística descriptiva —energías de enlace, entropías de
Shannon y de Boltzmann, temperatura efectiva— sobre 19 patrones de apertura y
3 024 partidas profesionales. Esa línea **caracteriza** los modelos, pero no los
pone a prueba contra territorio real; ese salto llega con el experimento 07.

**Hallazgos principales:**

1. **La entropía de Shannon de M1 supera a la de Alvarado en los 19 de 19
   patrones** (diferencia media: 1.92 nats).
2. **La interacción entre piedras del mismo color invierte el signo**: M1 da −1
   (atracción), Alvarado da +1 (repulsión).
3. **Correlación r = 0.83** entre modelos a lo largo de los patrones — las
   posiciones estructuralmente complejas lo son para ambos.
4. **El enfriamiento termodinámico no se captura**: `T_eff → ∞` a lo largo de las
   partidas reales, porque los dos colores cancelan `⟨E⟩ ≈ 0`.
5. **La entropía de Shannon crece** con el número de jugadas (más enlaces
   activos), no con la complejidad estratégica.
6. **La entropía de Boltzmann** se mantiene cerca del máximo por la misma razón
   (`T_eff` grande ⇒ distribución de Gibbs uniforme).

Informe científico completo: [REPORTE.md](REPORTE.md).

---

# Parte IV — Experimento 06: familias de Hamiltonianos y orden de Pareto

Búsqueda sistemática sobre 300 Hamiltonianos polinómicos cúbicos `H(x,y)`,
evaluados con 4 criterios intrínsecos de la superficie que cada polinomio define:

| Criterio | Símbolo | Qué mide |
|---|---|---|
| Vida topológica H₁ | `H₁_max` | 1-ciclos persistentes en la fibración de Milnor — complejidad táctica |
| Robustez | `Rob` | Fracción de perturbaciones de ±5 % que preservan el rango del candidato |
| Rango de energía | `ΔE` | `H(max) − H(min)` en `[−2,2]²` — contraste entre posiciones extremas |
| Nodos A₁ | `n_A₁` | Puntos críticos de silla donde la fibra `H⁻¹(c)` cambia de topología |

**296 candidatos** pasaron el filtro (97 %). El pelado de Pareto produjo **148
frentes**. El **Frente 1** —4 Hamiltonianos Pareto-óptimos, mutuamente
incomparables— era la élite teórica:

| ID | H₁_max | Rob | ΔE | A₁ |
|----|:------:|:---:|:--:|:--:|
| H_0094 | **0.188** | 1.0 | 31.3 | 1 |
| H_0113 | 0.173 | 1.0 | 35.4 | 1 |
| H_0045 | 0.166 | 1.0 | **43.4** | **2** |
| H_0042 | 0.120 | 1.0 | 33.5 | **2** |

**Estructura matemática (diagrama de Hasse):** el orden parcial es un conjunto
finito sin elemento máximo ni mínimo (sin supremo ni ínfimo); no es un retículo
(las uniones fallan para pares del Frente 1); por el teorema de Dilworth, la
anticadena máxima es 4 ⇒ el cubrimiento mínimo por cadenas es de **4 cadenas**.
475 relaciones de cobertura visualizadas en `hasse_diagram.png`.

Interpretación matemática y estratégica completa:
[`experiments/06_hamiltonian_families/output/reports/hasse_diagram_report.md`](experiments/06_hamiltonian_families/output/reports/hasse_diagram_report.md).

## Estado: en pausa — no es un experimento fallido

**Por qué se detuvo.** La hipótesis era razonable y falsable, y resultó falsa —
dos veces:

1. Contrastado contra el ΔR² real del experimento 07, el Frente 1 no solo dejó de
   ser la élite: fue el grupo de **peor** desempeño (0.055 a radio 9, contra
   0.152–0.170 de los grupos "medios" y "tardíos"). El criterio no era neutro:
   seleccionaba activamente en la dirección equivocada.
2. El experimento 08 explicó **por qué** tenía que pasar eso. El predictor real
   solo ve la proyección σ-invariante de 4 dimensiones; el análisis topológico, al
   evaluar `H(x,y)` directamente sin simetrizar, mezclaba esas 4 dimensiones
   relevantes con 3 que son **ruido puro** para la predicción. Se repitió el
   análisis sobre el *polinomio reducido* y el resultado también fue nulo
   (`|ρ| ≤ 0.21`, `p > 0.31`).

**Por qué "en pausa" y no "descartado".** Tres razones concretas:

- **La infraestructura sobrevivió intacta y sostiene todo lo posterior.** El
  catálogo de 305 candidatos con sus coeficientes, el código de puntos críticos, el
  visor interactivo y el diagrama de Hasse son la base sobre la que corren los
  experimentos 07 y 08.
- **La prueba tuvo un rango muestral limitado.** Las correlaciones se calcularon
  sobre los 44 candidatos con ΔR² medido, y esos 44 son mayoritariamente
  **aleatorios débiles**. Una hipótesis puede fallar sobre una población pobre sin
  que eso resuelva la pregunta sobre una población bien elegida.
- **Ahora sí sabemos cómo clasificar los polinomios cúbicos.** Cuando se corrió el
  experimento 06 no existía la descomposición de Klein: no había manera de saber
  qué dimensiones del polinomio son relevantes y cuáles invisibles. Hoy sí — y el
  criterio que sí funciona (el sesgo de color `β`, con ρ = −0.71 contra el
  desempeño real) apareció justamente de mirar la estructura de **simetría**, no la
  de puntos críticos.

**Cómo se retomaría.** Reconstruir el catálogo clasificado por las coordenadas
efectivas `(Σa, Σb, b₁₂, Σc)` —y eventualmente la quinta dimensión `x²y²`—,
muestrear de forma equilibrada dentro de esas clases en lugar de uniformemente en
los 7 coeficientes crudos, y recién entonces preguntar si la topología de la
variedad reducida separa a los buenos de los malos. **La rama está en pausa
esperando esa clasificación, no cerrada por refutación definitiva.**

---

# Parte V — Experimentos 07 y 08: predicción de moyo y su fundamento teórico

Son dos caras de la misma investigación, y su relación es de ida y vuelta:

- **El 07 es empírico.** Corre KataGo sobre partidas profesionales y mide cuánto
  agrega el campo del Hamiltoniano por encima de la geometría (ΔR²).
- **El 08 es teórico.** No corre KataGo ni predice nada nuevo: explica **por qué**
  el campo solo puede ver 4 de los 7 coeficientes del polinomio.
- **La ida:** una anomalía empírica del 07 —dos vectores de coeficientes muy
  distintos daban ΔR² idéntico a 4 decimales— exigió una explicación que el 08 dio
  en forma de teorema. **La vuelta:** ese teorema garantizó la reparametrización de
  7 a 4 dimensiones con la que el 07 encontró su mejor resultado.

## 5.1 Experimento 07 — diseño

**Métrica:** ΔR², la ganancia de R² al agregar el campo promediado del
Hamiltoniano sobre una región candidata, por encima de un modelo base que usa solo
geometría (distancia a la piedra negra más cercana, a la blanca, y al borde).

**Pipeline** — KataGo corre **una sola vez** por posición y se cachea; evaluar un
Hamiltoniano nuevo solo requiere el paso barato:

```
partida.sgf → muestrear posiciones → KataGo (ownership, 1 vez) → cache
                                                                    │
                                  47+ Hamiltonianos × relaxation_field(cache)
                                                                    │
                                                        ΔR² por Hamiltoniano
```

**El campo de relajación.** `H(x,y)` puntúa la interacción de un *par*, no de un
punto. Para cada punto vacío `p` se prueban 41 espines candidatos en `[−1,1]`, se
calcula la energía local sumando sobre los vecinos del kernel (ponderados por
`1/d²` hasta el radio Manhattan elegido) y se actualiza con el promedio de
Boltzmann. Las piedras quedan **fijas** como condiciones de frontera. El predictor
que entra a la regresión es `H_field_mean`: el promedio del campo ya relajado sobre
la región.

## 5.2 Experimento 07 — resultados

20 partidas profesionales reales, `kata1-b15c192`, OpenCL local:

| Hallazgo | Resultado |
|---|---|
| Criterios topológicos (Frente 1 del exp. 06) contra ΔR² real | **el peor** desempeño real de todos los grupos — no sirve para rankear candidatos |
| Búsqueda aleatoria (69 candidatos, 2 familias) | nunca supera a los derivados a mano; inestable entre radios |
| M1 / Alvarado, derivados a mano | los **únicos** candidatos cuyo ΔR² **mejora** al ampliar el radio |
| Fase A — optimización directa (`sparse_cubic`, 4 parámetros) | `H_OPT_A`: ΔR² = 0.317, IC 95 % [0.227, 0.380] — empate estadístico con M1 |
| Fase B — optimización en las 4 dimensiones efectivas (`cubic_mixed` completa) | `H_OPT_B`: ΔR² = 0.421, IC 95 % [0.339, 0.486] — traslape angosto, el resultado más fuerte |
| R² del modelo completo (geometría + `H_OPT_B`) | 0.733 ⇒ correlación r ≈ 0.86 contra el territorio real de KataGo |
| Validación hold-out (14 partidas nunca vistas por ninguna búsqueda) | ΔR² = 0.436; el optimismo por traslape es real pero modesto (0.06) y no altera la jerarquía |
| Auditoría de las señales de KataGo (7 campos probados) | solo `ownershipStdev` (vía ponderación) aporta señal real; `policy`, `moveInfos`, `scoreStdev`, `winrate` y `scoreLead` no |
| Sesgo de color, clasificado para los 307 del catálogo | ~66 % nunca cruzan cero (fijos a un color sin importar el tablero); solo ~6 % son genuinamente balanceados |
| Los balanceados predicen mejor (n = 64 evaluados) | ΔR² medio 0.257 (balanceados) contra 0.148 (sesgados), Welch p = 0.0007; confusor descartado por regresión |
| `H_0202` — aleatorio, jamás optimizado, resulta balanceado | ΔR² = 0.4195 en moyo — empata a `H_OPT_B`, que costó 102 minutos de búsqueda |
| Diagnóstico `β` de costo cero (campo en tablero vacío) | ρ = −0.71 (p < 10⁻⁵) contra el ΔR² real a radio 9 — el mejor predictor *a priori* del proyecto |
| Descomposición `F = F_eq + F_sesgo` | el componente de sesgo transporta ΔR² ≈ 0.001, no significativo: **es predictivamente inerte**, y por tanto corregible sin pérdida |

**Categorías de posición cubiertas:**

| # | Categoría | Estado |
|---|---|---|
| 1 | Moyo (territorio en disputa) | ✅ habilitada — la categoría difícil y central |
| 2 | Territorio asentado | ✅ habilitada — la geometría sola ya da R² = 0.670 |
| 3 | Fase de partida (15–90 %) | ✅ habilitada — caída monótona: 0.33 temprano → 0.10 tardío |
| 4 | Joseki (esquinas) | ✅ habilitada |
| 5 | Fuseki (apertura, 3–15 %) | ✅ habilitada — el mejor ΔR² por categoría |
| 6 | Grupos de piedras / vida-muerte | ⬜ pendiente — requiere mecanismo a nivel de grupo |
| 7 | Frontera activa / aji | ⬜ pendiente — requiere mecanismo a nivel de grupo |
| 8 | Sente/gote (tempo) | ✅ habilitada — señal real pero débil |

## 5.3 Experimento 08 — por qué el campo solo ve 4 de 7 parámetros

1. **σ (intercambio de posición)**, `(x,y) ↦ (y,x)` — motivada directamente por la
   simetrización `H(s,q) + H(q,s)` que el campo siempre usa. Un grupo de orden 2
   parte cualquier polinomio en una mitad invariante (sobrevive al promedio) y una
   anti-invariante (se cancela exactamente). No hay tercera opción.
2. Aplicado monomio por monomio: **4 de los 7 sobreviven**, 3 se cancelan
   idénticamente. Verificado simbólicamente (`sympy`) y empíricamente —
   Hamiltonianos construidos solo con la parte anti-invariante dan ΔR² = 0.000000
   exacto, a precisión de máquina, sobre datos reales.
3. **τ (intercambio de color)**, `(x,y) ↦ (−x,−y)` — una segunda simetría
   independiente. Juntas, `{e, σ, τ, στ}` forman el **grupo de Klein**
   (`Z₂ × Z₂`, no el cíclico `Z₄`: todo elemento no trivial tiene orden 2), que
   tiene exactamente 4 caracteres reales. Proyectar `cubic_mixed` sobre cada uno
   con el **operador de Reynolds** refina las 4 combinaciones supervivientes sin
   cambiar cuántas son.
4. **τ además predice el sesgo de color**: el sesgo es la proyección `P₊₋(H)`, no
   nula si y solo si `(Σa, Σc) ≠ (0,0)`. Es una **propiedad del polinomio**,
   calculable antes de tocar un tablero. La relajación no crea el sesgo: solo lo
   revela y lo amplifica.
5. **Rendimiento práctico:** buscar en las 4 dimensiones efectivas en vez de los 7
   coeficientes crudos es demostrablemente sin pérdida para este objetivo — no solo
   empíricamente cómodo.

**Advertencia de alcance:** toda esta reducción es exclusiva del campo de
relajación. El análisis topológico de `Γ(H)` evalúa `H(x,y)` directamente, sin
simetrizar — ahí los 7 coeficientes sí importan por separado. Esa asimetría es la
explicación estructural del fracaso del ranking del experimento 06.

## 5.4 Estado y verificación

El código de la Parte IV del informe (sesgo de color, `F_eq`, `β`) se incorporó al
repositorio y se verificó contra las cifras publicadas —las seis pruebas de
fidelidad pasan— con [`validate_prereq.py`](experiments/07_moyo_dataset/src/validate_prereq.py).
El siguiente experimento (matriz de transferencia entre categorías) está
**preregistrado** antes de correrse:
[`PREREGISTRO_RUTA_B.md`](experiments/07_moyo_dataset/PREREGISTRO_RUTA_B.md).

Informe completo, con cada tabla y cada salvedad estadística:
[`informe_completo_07_08.tex`](experiments/07_moyo_dataset/output/reports/informe_completo_07_08.tex).

---

# Parte VI — Experimento 09: axiomatización del Go

## 6.1 Por qué este camino

El camino recorrido en los experimentos anteriores **no da fiabilidad ni certeza
matemática completas**, y conviene decir con precisión dónde se rompe. Son tres
huecos, y ninguno se cierra midiendo mejor:

**(a) El objeto que predecimos es un constructo nuestro, no un objeto definido.**
"Moyo" significa, en el pipeline, *región vacía conexa cuyo `ownership` promedio
cae entre 0.15 y 0.85, con al menos 4 puntos*. Los umbrales son decisiones de
diseño. Nada en la teoría dice que sean ésos, y medimos que la clasificación es
frágil: la mitad de las regiones cambian de forma al cambiar el presupuesto de
búsqueda del motor.

**(b) La verdad de terreno es un estimador, no un teorema.** ΔR² mide concordancia
con una red neuronal. Que la red sea sobrehumana la vuelve el mejor instrumento
disponible, no una fuente de verdad matemática.

**(c) No hay criterio de corrección.** Dentro del 07–08 podemos decir "este
Hamiltoniano correlaciona mejor que aquél", pero nunca "esta definición de moyo es
correcta", porque no hay definición contra la cual serlo. **Ése es el hueco de
fondo**, y es exactamente el que un sistema axiomático llena: sin él no hay
criterio para decidir cuáles definiciones son correctas, cuáles reparables y
cuáles hay que descartar.

De ahí la decisión: abrir una rama que construya ese criterio, partiendo de la
formalización existente más cercana y **criticándola pieza por pieza**.

## 6.2 El punto de partida: la tesis de García Bustamante, y su auditoría

La base heredada es *Hacia una teoría matemática del juego de Go: tácticas,
estrategias, influencia y control de territorio*, tesis de licenciatura de **Emil
Estuardo García Bustamante** (Facultad de Ciencias, UNAM, 2022; tutor: J. M.
Alvarado Mentado). Define un vocabulario formal para el Go sobre teoría de gráficas
y demuestra cuatro teoremas. Su ambición declarada es *iniciar* una teoría.

> **La continuidad no es casual.** El tutor de esa tesis es el mismo Alvarado del
> modelo Atomic-Go que este proyecto usa como uno de sus dos polinomios de partida,
> y **la propia tesis ya emplea un Hamiltoniano de Ising** para cuantificar
> influencia en su capítulo 5. Las dos ramas de este repositorio —la de los campos
> de Ising y la axiomática— vienen del mismo linaje y convergen por construcción,
> no por analogía.

**El método de la auditoría** es el que da criterio: *una definición formal es
defectuosa si su extensión no coincide con la del concepto que nombra*, y eso se
prueba exhibiendo un objeto en la diferencia simétrica. Aplicado, produjo **21
hallazgos**: errores de tipo, definiciones mal puestas, tres demostraciones con
salto lógico, y —los de mayor consecuencia— **dos definiciones cuya extensión es
exactamente la inversa de la pretendida**.

El ejemplo canónico, porque muestra qué se gana con el rigor: con las definiciones
de la tesis, **una piedra negra aislada en el centro de un tablero vacío tiene dos
ojos** y es por tanto incapturable. En el juego real se captura en cuatro jugadas.
Simultáneamente, un ojo verdadero de un punto quedaba clasificado como *ojo falso*.
La falla no estaba en la idea —el texto en lenguaje natural dice lo correcto— sino
en su traducción a la relación de conexidad del tablero, que no es la pertinente.

**El balance, que la auditoría no oculta**: buena parte de la tesis se integra sin
cambio. La configuración como coloración de vértices con tres valores, la cadena
como componente conexa, la distinción entre libertades interiores y exteriores —que
es el germen exacto de la *región vital* de Benson, solo le faltaba el
encerramiento—, el semeai definido por la libertad compartida, y la reducción del
territorio a vida y muerte en vez de a cercado geométrico. En dos casos la
reparación mínima **reconstruyó, sin buscarlo, el criterio clásico de Benson (1976)**.

## 6.3 El sistema 𝔊

Cuatro primitivas no definidas —un conjunto `P` de puntos, una relación de
adyacencia `∼`, tres colores `Λ`, dos jugadores— y **cinco grupos de axiomas**:

| Grupo | Contenido |
|---|---|
| **T** | El tablero: finitud, adyacencia simétrica e irreflexiva, conexidad, y la instancia estándar 19×19 |
| **C** | Configuraciones: coloración de los puntos; cadenas y regiones como componentes conexas |
| **D** | Dinámica: posición, jugadas, colocación, resolución de capturas, legalidad, alternancia, terminación |
| **S** | Escrutinio: puntuación por área y por territorio |
| **E** | Estrategias y valor |

Un quinto elemento, el **sistema de reglas**, no es primitivo sino un **parámetro**:
`ℜ = ⟨ς, κ, ϵ, komi⟩` con `ς` ∈ {suicidio prohibido, permitido}, `κ` ∈ {ko simple,
superko posicional, superko situacional} y `ϵ` ∈ {área, territorio}. Cada teorema
declara de qué componentes depende. La parametrización es deliberada: el estatus del
*cuatro doblado en la esquina*, la puntuación del seki y la terminación misma
cambian de valor de verdad según `κ` y `ϵ`, de modo que fijar un sistema de reglas
equivaldría a demostrar teoremas que no son del Go sino de una de sus variantes.

Sobre esa base se demuestran **33 teoremas** y se organiza un **catálogo de 171
conceptos del Go como objetivos de derivación**.

## 6.4 El método: seis agentes disciplinarios

La ejecución se reparte entre seis agentes definidos **por disciplina, no por
tema**: Go, matemáticas, lógica, axiomática, teoría de modelos y teoría de la
demostración. Cada uno interroga el sistema completo desde su propio criterio de
corrección, y por eso ven cosas distintas del mismo objeto: donde el matemático
pregunta *si el teorema es cierto*, el lógico pregunta *si el enunciado está bien
formado*, el axiomático *si el axioma hace falta*, el teórico de modelos *en qué
tableros sigue valiendo*, el de la demostración *con qué medios se demuestra*, y el
jugador de Go *si lo demostrado es verdad del juego*.

El valor del dispositivo no es sociológico sino **epistémico**: una sola línea
argumental que escribe y revisa a la vez tiende a acomodarse a sí misma —introduce
a mitad de camino la hipótesis que hace falta para que su propia demostración
funcione. Seis criterios de corrección incompatibles no pueden acomodarse todos, y
lo que no cuadra aparece.

Funcionó, y de forma medible: de la confrontación salieron **8 enmiendas**, dos de
las cuales **refutan pasos del propio programa**. Una segunda ronda de revisión
externa produjo **9 enmiendas más**, dos sobre axiomas y dos sobre teoremas
centrales. Hay un patrón instructivo en quién encontró qué: los agentes internos,
que comparten con el autor la manera de mirar, encontraron fallos de **estructura**;
la revisión externa encontró fallos de **transcripción y de enumeración de casos**.
Son dos clases distintas de error y ninguna instancia sustituye a la otra.

## 6.5 Resultados

**Sobre el juego:**

- **Suficiencia del criterio de Benson**, demostrada dentro del sistema y válida
  para ambos valores del parámetro de suicidio.
- **La conexión incondicional no es transitiva** — de donde se sigue que *el grupo
  no admite definición como partición* y debe ser un **parámetro** del enunciado.
  Esto refutó un paso del programa original.
- **Resolución completa del semeai**, con y sin ojos, más su lema de instanciación:
  demuestra la regla práctica de que *las libertades compartidas cuentan solo para
  el bando con ojo*, y da de paso la **caracterización del seki** (hay seki con
  cualquiera de los dos turnos exactamente cuando `|a − b| ≤ s − 2`).
- **La repetición rompe la independencia local**, que es la razón teórica de la
  amenaza de ko: la amenaza no es un recurso psicológico sino la única manera de
  cambiar el estado global sin cambiar el local.
- **En tableros hasta 3×4, toda configuración legal es alcanzable**; el *paso* es
  lo que cierra la brecha.
- **La vida incondicional depende del parámetro de suicidio** — único concepto del
  documento que lo hace.

**Sobre el sistema:** consistencia, categoricidad, independencia de cuatro axiomas,
y un **teorema de transferencia** que identifica a la **escalera como la única
noción táctica que depende de la geometría del borde** (en un tablero toroidal la
clase de las escaleras es vacía; la de las redes no).

**Sobre lo tratable:** la estratificación de las definiciones en 8 estratos
demuestra que no hay circularidad, y sitúa la frontera entre lo tratable y lo
intratable **no donde la intuición del jugador la pone** —entre lo local y lo
global— sino entre los predicados sobre la *configuración* y los predicados sobre
el *árbol*. Dos ojos es barato aunque hable de vida; una escalera es cara aunque
quepa en un rincón.

## 6.6 El puente con los experimentos 07 y 08

Aquí está la razón de fondo por la que esta rama fortalece a las otras dos, y no
las sustituye.

**El campo de Ising deja de ser una heurística paralela.** El sistema define un
**campo de influencia** `φ_j(p) = Σ_q f(d(p,q))` sobre las piedras de `j`, su campo
diferencial `Δ = φ_N − φ_B`, y —esto es lo decisivo— el **moyo como conjunto de
nivel**:

```
M^θ_j  =  { p vacío :  ±Δ(p) > θ }
```

Nuestro `relaxation_field` es **un caso particular** de ese campo, con `f`
implícita en los pesos de interacción. Formulado así, deja de ser una heurística
que corre en paralelo a la teoría y pasa a ser **un objeto sujeto a una condición
de consistencia comprobable**.

**El umbral deja de ser arbitrario.** El sistema impone un **criterio de
calibración**: el par `(f, θ)` es *admisible* si el campo coincide con los
predicados ya decididos allí donde éstos deciden — concretamente, si todo punto de
una región encerrada por un grupo incondicionalmente vivo pertenece al moyo de ese
jugador. Es una condición formal, verificable, y sustituye la elección
`0.15 / 0.85` por algo que se puede satisfacer o violar. Existe al menos un par
admisible (demostrado).

**Y el sistema dice exactamente dónde todavía no ayuda.** El criterio de
calibración resulta **vacuo en la apertura**: no impone ninguna condición al campo
de un color mientras ese color no tenga al menos **seis piedras** formando una
familia incondicionalmente viva — y seis es el mínimo demostrado. Es decir: no
restringe nada precisamente en el fuseki, que es *donde el moyo es el concepto en
juego* y donde el experimento 07 mide su mejor ΔR². De ahí sale una condición dura
sobre el criterio que falta: **no puede apoyarse en predicados del estrato 6**,
porque en la apertura ninguno se aplica. El candidato propuesto —monotonía respecto
del valor— se formula sobre el estrato 4 y es **falsable sobre posiciones
resueltas**, de modo que admite trabajo empírico inmediato aunque la teoría no esté
cerrada.

**Las categorías 6 y 7 dejan de ser "mecanismo nuevo".** Lo que el experimento 07
declaró pendiente por requerir maquinaria desconocida —vida/muerte de grupos, aji—
aparece en el catálogo **con definición y con el nivel que lo soporta**: vivo,
muerto e indeterminado sobre el grupo E; aji y espesor sobre E + M3. Ya no es
territorio inexplorado: es una lista de objetivos de derivación con dependencias
declaradas.

**Ésa es la apuesta de esta rama.** Una buena axiomatización no es un adorno formal
sobre el trabajo empírico: es la infraestructura que permite **codificar otros
momentos, situaciones y objetos del Go** —los 171 del catálogo, de los que 142
están ausentes en la base heredada— con criterio de corrección, y volver después a
los experimentos 07 y 08 con predicados definidos en vez de umbrales elegidos. El
Hamiltoniano seguiría midiendo lo mismo; lo que cambia es que ahora habría **algo
matemáticamente definido contra lo cual medirlo**.

## 6.7 Estado y frentes abiertos

Honestidad sobre el estatus, que el propio documento impone: sobreviven **un solo
enunciado verificado sin demostrar** (la cota de seis piedras, comprobada por
exhaución en 6×6 y 7×7 pero no establecida para 19×19) y **una sola importación con
atribución** (la recíproca del criterio de Benson). Se distingue explícitamente lo
*demostrado* de lo *verificado en un rango finito* — distinción que degradó dos
resultados antes presentados como teoremas.

| Frente | Estado | Qué falta |
|---|---|---|
| Recíproca de Benson dentro de 𝔊 | el más barato | argumento de punto fijo; cierra la vida incondicional y elimina la última importación |
| Teoría del seki | alto rendimiento | derivarlo cierra 4 entradas del catálogo y una hipótesis del teorema de invasión |
| Valor de posiciones con ko | el más caro y productivo | qué es el valor cuando el ko **no** está aislado |
| Módulo M3 — magnitudes graduadas | el más incierto | el segundo criterio del campo; **es el frente que toca directamente a los exp. 07–08** |
| Módulo M4 — clasificación de patrones | reorientado | patrones de soporte acotado salvo simetría y traslación |

**Pendiente de integración al repositorio:** el documento del sistema axiomático y
su archivo `verificaciones.py` todavía no están versionados aquí. Ver
[`experiments/09_axiomatizacion/README.md`](experiments/09_axiomatizacion/README.md).

---

# Instalación

```bash
pip install numpy>=1.23 scipy>=1.10 matplotlib>=3.7 pandas scikit-learn sympy
```

Para los experimentos 07 y 08 hace falta además **KataGo** (binario + red
neuronal), que no se versiona en este repositorio por ser software de terceros.
Ver `experiments/07_moyo_dataset/` para las instrucciones de descarga (binario
OpenCL + red `kata1-b15c192`).

---

# Estructura del repositorio

```
Go_entropic_information/
│
├── src/                            # Núcleo del tronco (exp. 01–05)
│   ├── go_ising_classical.py       # Hamiltoniano M1, mapa de energía, config. del kernel
│   ├── go_entropy.py               # Entropías de Shannon y Boltzmann, T_eff
│   ├── go_game_engine.py           # Motor de reglas de Go + parser SGF
│   ├── go_visualization.py         # Gráficas de rejilla y comparación
│   └── board_utils.py              # Utilidades de tablero
│
├── scripts/
│   ├── pipeline/                   # Generación de datos
│   ├── analysis/                   # Análisis de patrones y partidas
│   └── viz/                        # Visualización y animaciones
│
├── data/
│   └── sgf_partidas/               # ~4 000 partidas profesionales .sgf (no versionadas)
│
├── docs/
│   └── reporte_conceptual_07_08.md # Fundamentos conceptuales, versión extendida
│
├── results/                        # Salidas del tronco (01–05)
│   ├── 01_patrones/                # 19 patrones base de apertura
│   ├── 02_enlaces_ising/           # Análisis de interacción por enlace
│   ├── 03_entropia/                # Shannon, Boltzmann y T_eff
│   ├── 04_trayectoria/             # Trayectoria jugada a jugada
│   ├── 05_partidas_reales/         # Análisis de 3 024 partidas profesionales
│   ├── 06_animaciones/             # Animaciones GIF de partidas reales
│   └── interactive/                # Visor interactivo de features
│
└── experiments/
    ├── 06_hamiltonian_families/    # Familias de Hamiltonianos y orden de Pareto [EN PAUSA]
    │   ├── pipeline.py             # Pipeline: generar, analizar, visualizar
    │   ├── src/
    │   │   ├── families.py         # Plantillas de polinomios (cubic_mixed, h_m1, …)
    │   │   ├── algebra.py          # Puntos críticos, nodos A₁, número de Milnor
    │   │   ├── topology.py         # TDA: H₀/H₁ con gudhi CubicalComplex
    │   │   └── catalog.py          # Catálogo y filtrado de candidatos
    │   └── output/
    │       ├── catalog.json        # 305 Hamiltonianos + métricas completas
    │       ├── figures/            # Pareto, atlas de variedades, diagrama de Hasse
    │       └── reports/            # Resumen ejecutivo e informe del Hasse
    │
    ├── 07_moyo_dataset/            # Predicción de moyo contra KataGo real [ACTIVO]
    │   ├── PREREGISTRO_RUTA_B.md   # Protocolo congelado del siguiente experimento
    │   ├── src/
    │   │   ├── katago_engine.py        # Wrapper del motor KataGo (modo analysis, JSON)
    │   │   ├── moyo_detector.py        # Flood-fill de regiones por banda de ownership
    │   │   ├── features.py             # board_features, relaxation_field, F_eq, β
    │   │   ├── early_regions.py        # Muestreo de fuseki (3–15 %) + regiones de joseki
    │   │   ├── cache_positions.py      # Corre KataGo 1 vez, cachea moyo/territorio
    │   │   ├── cache_early_positions.py# Idem para fuseki/joseki
    │   │   ├── optimize_coefficients.py# Fases A y B: differential_evolution sobre el cache
    │   │   ├── run_fase_b.py           # Fase B: búsqueda en las 4 dimensiones efectivas
    │   │   ├── analyze_results.py      # ΔR² incremental y prueba F
    │   │   ├── bootstrap.py            # Bootstrap por partida, marginal y pareado
    │   │   ├── evaluate.py             # DataFrame multi-Hamiltoniano × multi-predictor
    │   │   ├── validate_prereq.py      # Pruebas de fidelidad T1–T4
    │   │   ├── audit_ruta_b.py         # Auditorías previas A1–A3
    │   │   └── calibration.py          # Ajusta el campo crudo contra pct_black real
    │   └── output/
    │       ├── cache_*.pkl                        # Caches de posiciones (KataGo 1 vez)
    │       ├── hamiltonians_clasificados.{csv,json} # Los 307: simetría, sesgo, tipo, ΔR²
    │       └── reports/
    │           └── informe_completo_07_08.tex     # Informe unificado, fuente única de verdad
    │
    ├── 08_teoria_invariantes/      # Por qué el campo solo ve 4 de 7 parámetros [ACTIVO]
    │   └── src/
    │       └── klein.py            # Proyecciones de Reynolds, σ y τ, sesgo de color
    │
    └── 09_axiomatizacion/          # Sistema axiomático 𝔊 [NUEVO]
        └── README.md               # Alcance, estado y archivos pendientes de integrar
```

---

# Uso

### Tabla de interacción por enlace (4 representaciones)
```bash
python scripts/viz/viz_interaction_comparison.py
# → results/interaction_comparison.png
```

### Comparación de entropías (Shannon + Boltzmann + T_eff) para los 19 patrones
```bash
python scripts/viz/viz_entropy_comparison.py
# → results/entropy_comparison.png
```

### Partida animada con superposición de energía de un modelo
```bash
python scripts/viz/animation_game.py --model M1
# → results/<partida>_M1.gif
```

### Partida animada con comparación de entropía de ambos modelos
```bash
python scripts/viz/animation_entropy_compare.py
# → results/<partida>_entropy_compare.gif
```

### Experimento 06 — búsqueda de familias de Hamiltonianos
```bash
cd experiments/06_hamiltonian_families

python pipeline.py --generate      # 1. Catálogo (300 cubic_mixed + referencias)
python pipeline.py --analyze       # 2. Análisis de Pareto + todas las figuras
python pipeline.py --frente1       # 3. Hamiltonianos individuales del Frente 1
```

### Experimento 07 — pipeline de predicción de moyo
```bash
cd experiments/07_moyo_dataset/src

python cache_positions.py          # 1. KataGo 1 vez por posición → cache
python cache_early_positions.py    # 2. Fuseki (3–15 %) + joseki (esquinas)
python run_fase_b.py               # 3. Fase B: optimización en 4 dimensiones efectivas

python validate_prereq.py          # Verificación de fidelidad (T1–T4)
python audit_ruta_b.py             # Auditorías previas al siguiente experimento
```

### Experimento 08 — verificación simbólica de la descomposición de Klein
```bash
python experiments/08_teoria_invariantes/src/klein.py
```

---

# Resultados generados

| Archivo | Descripción |
|---|---|
| `interaction_comparison.png` | Mapas de calor, matriz de diferencias, barras y grafos de nodos |
| `entropy_comparison.png` | Shannon, Boltzmann y T_eff para la tabla + 19 patrones + dispersión |
| `bond_interaction_table.png` | Tabla de energía de enlace dirigida para ambos modelos |
| `bond_entropy_compare.png` | Comparación de entropía de Shannon por patrón |
| `*_entropy_compare.gif` | Animación de partida: S_Shannon, S_Boltzmann y T_eff en vivo |
| `*_M1.gif` | Animación de partida: tablero + superposición de energía M1 |
| `dashboard_M1/M2.png` | Tablero completo de energía y entropía por modelo |
| `hasse_diagram.png` | Diagrama de Hasse del orden parcial de 305 Hamiltonianos |
| `informe_completo_07_08.tex` | Informe unificado de los experimentos 07 y 08 |

---

# Autores y referencias

- **Leonardo Jiménez Martínez** — análisis entrópico, comparación de modelos,
  experimentos 06–09 (BIOMAT, Centro de Biomatemáticas Dr. Epifanio Jiménez Ávila)
- **Mario Mercado Sánchez** — desarrollo del modelo de Ising
  ([Ometitlan / Project-Quantum-Go](https://github.com/ometitlan/Project-Quantum-Go))

El sistema axiomático (experimento 09) se desarrolló en colaboración con
Claude Opus 5 (Anthropic).

**Referencias**

- García Bustamante, E. E. (2022). *Hacia una teoría matemática del juego de Go:
  tácticas, estrategias, influencia y control de territorio*. Tesis de licenciatura
  en Matemáticas, Facultad de Ciencias, UNAM. Tutor: J. M. Alvarado Mentado.
  — **base auditada del experimento 09**.
- Rojas-Domínguez, A., Barradas-Bautista, D. y Alvarado, M. (2019). *Atomic-Go*.
  IEEE Access. — **origen del modelo Alvarado**.
- Benson, D. B. (1976). *Life in the game of Go*. Information Sciences 10, 17–29.
- Berlekamp, E. y Wolfe, D. (1994). *Mathematical Go: Chilling Gets the Last Point*.
- Robson, J. M. (1983). *The complexity of Go*. Proceedings IFIP, 413–417.
- Tromp, J. y Farnebäck, G. (2016). *Combinatorics of Go*.
- Fischbach, M. A. y Walsh, C. T. (2024). *Problem choice and decision trees in
  science and engineering*. Cell, 187, 1828–1833.
- KataGo v1.16.5 — <https://github.com/lightvector/KataGo>
