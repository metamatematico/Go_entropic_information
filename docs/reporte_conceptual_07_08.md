# Reporte conceptual — Experimentos 07 y 08

**Qué es un Hamiltoniano cúbico de Go, de dónde salieron los polinomios de partida, y qué
significa exactamente "predecir un moyo" cuando el motor nunca dice la palabra "moyo".**

Proyecto `Go_entropic_information` · BIOMAT — Centro de Biomatemáticas
Leonardo Jiménez Martínez · UNAM

---

## Propósito de este documento

Este reporte no presenta resultados nuevos: presenta los **fundamentos conceptuales** de la
línea de investigación activa, en un registro didáctico y autocontenido. Está pensado para
alguien que llega al repositorio sin conocimiento previo de física estadística, de teoría de
grupos o de Go, y que necesita entender qué se está midiendo antes de mirar una sola cifra.

Los resultados cuantitativos viven en la monografía de los Experimentos 07+08 y en el
`README.md`. Aquí se responden cinco preguntas que esas fuentes dan por sabidas:

1. ¿Qué diferencia hay entre "un polinomio de Ising" y "un Hamiltoniano"?
2. ¿Por qué es legítimo un Hamiltoniano cúbico, y qué gana respecto del Ising clásico?
3. ¿De dónde salieron los polinomios de Alvarado y de Mercado & Jiménez, y por qué ellos?
4. ¿Por qué se usa KataGo, y qué devuelve realmente?
5. Si KataGo nunca dice "moyo", ¿de dónde sale el moyo que estamos prediciendo?

---

## 1. El problema y su dificultad de fondo

En el Go, dos jugadores colocan piedras alternadamente sobre una retícula de 19 × 19
intersecciones. Las piedras no se mueven. Se gana rodeando más **territorio** —intersecciones
vacías controladas— que el rival.

Esto tiene una consecuencia que separa al Go del ajedrez: **el objeto estratégico central es
una propiedad del espacio vacío**, no de las piezas. Los jugadores distinguen grados de
pertenencia de ese espacio:

- **Territorio asentado**: una zona cuyo dueño ya es prácticamente inapelable.
- **Moyo**: lo contrario de inapelable — un marco territorial grande, delimitado por piedras
  propias pero todavía invadible. Una promesa de territorio en disputa.
- **Neutral (*dame*)**: puntos que no serán de nadie.

La hipótesis física del proyecto es que la influencia territorial se comporta como un **campo**:
cada piedra irradia control que decae con la distancia, las influencias de colores opuestos
compiten, y el valor neto en cada punto vacío emerge del balance colectivo. La mecánica
estadística tiene un lenguaje construido exactamente para eso.

La pregunta, en su forma falsable:

> ¿Un Hamiltoniano clásico de Ising captura algo real del territorio de Go, **más allá** de lo
> que ya explica la sola geometría del tablero (distancia a las piedras, distancia al borde)?

La métrica es una sola: **ΔR²**, la ganancia de varianza explicada al agregar el campo del
Hamiltoniano por encima de un modelo base puramente geométrico. La base geométrica es
deliberadamente fuerte —captura el "sentido común" de que un punto cerca de piedras propias y
lejos de enemigas suele ser territorio propio—, de modo que ΔR² mide exactamente lo que el
Hamiltoniano **agrega**.

---

## 2. Hamiltoniano no es lo mismo que "modelo de Ising"

### 2.1 Qué es un Hamiltoniano

Un **Hamiltoniano** es una función que asigna una energía a cada configuración posible de un
sistema. No es una fórmula particular: es un **rol** dentro de una teoría.

Su importancia viene de lo que la mecánica estadística permite hacer con él. Postula que, a
temperatura `T`, la probabilidad de observar una configuración decae exponencialmente con su
energía —el **peso de Boltzmann** `exp(−E/T)`:

- a `T` baja, el sistema se ordena: casi solo importan las configuraciones de mínima energía;
- a `T` alta, el desorden térmico domina;
- lo que se observa macroscópicamente nunca es *una* configuración, sino un **promedio** sobre
  todas, pesado por Boltzmann.

Dado un Hamiltoniano, todo lo observable se sigue. Esa es su función.

### 2.2 Qué es el modelo de Ising

El **modelo de Ising** es *una elección concreta* de Hamiltoniano — históricamente, la más
simple que describe un material magnético. Cada sitio lleva un espín `s_i ∈ {−1, +1}` y la
energía total suma contribuciones de pares vecinos:

```
H_total = −J · Σ_⟨i,j⟩ s_i · s_j
```

Con `J > 0`, dos vecinos alineados **restan** energía (configuración favorecida) y dos opuestos
la suman. Eso es todo el modelo.

### 2.3 Dónde está la confusión

"Ising" nombra la **forma funcional del acoplamiento** —el producto `s_i·s_j`—, no el concepto
de energía. Por eso la expresión "el polinomio de Ising" mezcla dos niveles: lo que existe es
un *Hamiltoniano* cuya *función de acoplamiento* resulta ser bilineal.

Distinguirlos importa porque el proyecto opera exactamente sobre esa distinción:

| Se conserva | Se generaliza |
|---|---|
| La **estructura**: la energía total es una suma de interacciones sobre pares de vecinos | La **función de acoplamiento**: en vez de fijarla a `s_i·s_j`, se permite cualquier polinomio |

El objeto resultante:

```
H_total = Σ_⟨i,j⟩ H(s_i, s_j)

H(x, y) = a₁x + a₂y + b₁₁x² + b₁₂xy + b₂₂y² + c₁₁₂x²y + c₁₂₂xy²      ← plantilla `cubic_mixed`
```

Sigue siendo, formalmente y en todo rigor, un **Hamiltoniano de Ising clásico**: una suma de
energías par a par sobre el tablero. Solo que el acoplamiento es más rico que el producto. El
espacio de espines es `s ∈ {−1, 0, +1}` (negro, vacío, blanco) y el modelo es **enteramente
clásico** en todo el proyecto, nunca cuántico.

---

## 3. Por qué un Hamiltoniano cúbico es legítimo — y qué gana

### 3.1 Por qué se puede

Nada en la mecánica estadística exige que la energía sea bilineal. Los requisitos son dos:

1. que `H` sea una función real bien definida de la configuración;
2. que el peso `exp(−H/T)` sea normalizable, es decir, que la función de partición exista.

En este sistema el espacio de configuraciones es **finito**: cada una de las 361 intersecciones
toma un valor en `{−1, 0, +1}`. La función de partición es entonces una **suma finita**, y está
siempre bien definida. Por lo tanto **cualquier** función real sobre ese espacio es un
Hamiltoniano legítimo.

La restricción bilineal del Ising de libro de texto **no es una ley de la física**: es una
elección de modelado heredada del magnetismo, donde resulta apropiada. En Go no lo es.

### 3.2 Por qué hace falta

El acoplamiento `s_i·s_j` solo sabe expresar "alinéate o no te alinees", y arrastra dos
propiedades que el magnetismo quiere pero el Go no:

**(a) Es simétrico bajo inversión global de signo.** `(−s_i)·(−s_j) = s_i·s_j`. En un imán es
correcto: "norte" y "sur" son etiquetas intercambiables. En Go, la *regla* es simétrica entre
negro y blanco, pero una *posición concreta* no lo es —hay un jugador en turno, hay un
diferencial de puntos, hay komi—, y el modelo necesita poder expresar esa asimetría.

**(b) El vacío no existe.** Con `s = 0`, el producto `s_i·s_j` da cero: una intersección vacía
no aporta energía y no participa. En magnetismo no hay "sitio vacío". En Go, **el vacío es el
objeto del juego**: el territorio *es* espacio vacío. Un modelo que no puede asignarle energía
al vacío no puede, literalmente, hablar de territorio.

Los términos que agrega la plantilla cúbica rompen exactamente esas dos limitaciones:

| Término | Qué habilita |
|---|---|
| `a₁x`, `a₂y` (lineales) | El vacío **carga energía**: `H(0, y) ≠ 0`. Un punto vacío deja de ser invisible |
| `c₁₁₂x²y`, `c₁₂₂xy²` (cúbicos) | Componentes **impares en color**: permiten distinguir negro de blanco |
| `b₁₂xy` | El acoplamiento de Ising puro, conservado como caso particular |
| `b₁₁x²`, `b₂₂y²` | Componentes **pares en color**: sensibilidad a la ocupación, indiferente al color |

### 3.3 Por qué grado 3 y no más — el argumento de completitud

Podría objetarse que grado 3 es tan arbitrario como grado 2. No lo es: **es completo**.

Sobre el espacio de espines de Go vale la identidad
```
s³ = s        para todo s ∈ {−1, 0, +1}
```
de modo que elevar el grado en una misma variable **no produce ninguna función nueva**: `x³` es
literalmente la misma función que `x`.

Más aún, el argumento se puede cerrar por completo. Un par de espines tiene `3 × 3 = 9` estados
posibles, así que el espacio de **todas las funciones de interacción de pares imaginables** es
un espacio vectorial real de dimensión exactamente **9**. Y los nueve monomios

```
{ 1,  x,  x²,  y,  y²,  xy,  x²y,  xy²,  x²y² }
```

forman una **base** de ese espacio (verificado numéricamente: la matriz de evaluación sobre los
9 pares tiene rango 9). No existe ninguna interacción de pares, por exótica que sea, que quede
fuera de su envolvente lineal.

La plantilla `cubic_mixed` de 7 parámetros cubre **7 de esas 9 dimensiones**. Las dos ausentes:

| Ausente | Qué es | ¿Importa? |
|---|---|---|
| `1` (constante) | desplaza todas las energías por igual | **No**: se cancela exactamente en el promedio de Boltzmann |
| `x²y²` | indicador de "ambas intersecciones ocupadas" | **Sí** — ver abajo |

> ### Consecuencia abierta
> Bajo la simetrización que usa el predictor (§5.2), el término `x²y²` **sí es visible**: la
> descomposición de Klein lo coloca en la pieza `P₊₊` (verificado simbólicamente con `sympy`).
> Es decir, el campo de relajación puede ver **5** dimensiones efectivas, mientras que todas
> las búsquedas de coeficientes realizadas hasta ahora (Fases A y B) exploran solo **4**:
> `(Σa, Σb, b₁₂, Σc)`. Explorar la quinta es una extensión natural del espacio de búsqueda y
> está pendiente.

---

## 4. De dónde salen los dos polinomios de partida

El proyecto no comenzó eligiendo polinomios al azar. Partió de dos Hamiltonianos con origen
independiente y anterior a este pipeline, que encarnan las dos posturas opuestas sobre las dos
preguntas de §3.2 —qué hacer con el vacío y qué hacer con el color:

### 4.1 Modelo Alvarado — Atomic-Go

```
H(x, y) = x · y
```

Proviene de Rojas-Domínguez, Barradas-Bautista & Alvarado (2019), *Atomic-Go*, IEEE Access. Es
el acoplamiento de Ising **puro**, sin modificaciones: 3 valores de enlace `{−1, 0, +1}`,
perfectamente **simétrico** en el orden de los argumentos, y con el **vacío invisible**
(`H(0, y) = 0` siempre). Es el caso mínimo — la hipótesis nula estructural.

### 4.2 Modelo M1 — Mercado Sánchez & Jiménez Martínez

```
H(x, y) = x + 2y − x²y − xy²
```

Proviene de una derivación teórica previa del grupo, ajena a este pipeline. Tiene 5 valores de
enlace `{−2, −1, 0, +1, +2}`, es **asimétrico** en el orden de los argumentos (`H(i→j) ≠ H(j→i)`
en 6 de los 9 pares), y tiene el **vacío activo**. Es el caso deliberadamente enriquecido.

### 4.3 Por qué estos dos, y por qué resultaron ser el arranque correcto

La justificación inicial era conceptual: son los dos extremos de la decisión de modelado. Pero
apareció después una razón **empírica** mucho más fuerte.

De todos los Hamiltonianos probados en la primera ronda del Experimento 07 —incluidos **69
generados al azar** (44 de `cubic_mixed` de 7 parámetros y 25 de `sparse_cubic` de 4)—
**únicamente Alvarado y M1 mejoraban** su ΔR² al ampliar el radio de interacción del kernel, en
lugar de degradarse:

| Hamiltoniano | ΔR² (radio 1) | ΔR² (radio 9) | Cambio |
|---|---|---|---|
| M1 | 0.242 | 0.309 | **+0.067** |
| Alvarado | 0.169 | 0.255 | **+0.086** |
| Aleatorios (44, media) | 0.130–0.216 | 0.055–0.170 | degradan |
| Aleatorios (25, media) | 0.102 | 0.056 | degradan |

Ninguno de los 69 candidatos aleatorios replicó esa propiedad. Ese contraste —coeficientes
*elegidos* mejoran con el radio, coeficientes *muestreados* se degradan— es lo que motivó
abandonar el muestreo aleatorio y pasar a **optimizar coeficientes directamente** contra la
señal real, dentro de la familia cúbica que ambos modelos habitan.

*(El mecanismo detrás de ese contraste quedó sin explicación durante mucho tiempo, y resultó
ser el sesgo de color: los candidatos aleatorios están mayoritariamente sesgados hacia un
color, y el daño del sesgo se amplifica al ampliar el radio.)*

**La lectura correcta:** Alvarado y M1 no son dos modelos rivales a comparar, sino **dos puntos
conocidos dentro de un espacio continuo** que el proyecto explora. Ambos son casos particulares
de `cubic_mixed` — Alvarado con `b₁₂ = 1` y el resto en cero; M1 con `a₁ = 1, a₂ = 2,
c₁₁₂ = c₁₂₂ = −1`.

---

## 5. Por qué usamos KataGo, y qué devuelve realmente

### 5.1 Por qué hace falta un motor

Para hacer ciencia sobre el territorio se necesita una **verdad de terreno**: un número
objetivo que diga cuánto controla cada color cada zona.

Y aquí está la dificultad de fondo, que conviene enunciar sin rodeos: **a mitad de partida, el
territorio no es decidible por las reglas del Go.** No es un hecho del tablero presente — es
una *predicción sobre cómo terminará la partida*. Las reglas determinan el territorio
únicamente al final, tras el conteo. No existe fórmula, árbitro ni tabla que lo resuelva antes.

Por eso el proyecto recurre a un motor de fuerza sobrehumana. Con una advertencia honesta:
**KataGo no es "la verdad" del Go — es el mejor estimador disponible.** Tiene ruido interno
propio: sus estimaciones varían entre corridas y con el presupuesto de búsqueda (`maxVisits`).
El experimento lo trata como cualquier ciencia experimental trata el ruido de su instrumento:
lo cuantifica, verifica que las conclusiones no dependan de una corrida particular, y reporta
la incertidumbre.

*(De hecho, ponderar la regresión por la propia incertidumbre del motor, `1/ownershipStdev²`,
resultó ser la única mejora real entre las siete señales auditadas de KataGo.)*

### 5.2 Qué devuelve el motor, literalmente

Verificado sobre la instalación de este repositorio — **KataGo v1.16.5**, red
`kata1-b15c192`, backend OpenCL. En modo `analysis` (protocolo JSON por stdin/stdout), la
respuesta contiene:

| Bloque | Campos |
|---|---|
| **raíz** (8) | `ownership` (361 números), `ownershipStdev`, `policy`, `moveInfos`, `rootInfo`, `turnNumber`, `isDuringSearch`, `id` |
| **`rootInfo`** (18) | `winrate`, `scoreLead`, `scoreStdev`, `scoreSelfplay`, `utility`, `visits`, `weight`, `currentPlayer`, `rawLead`, `rawWinrate`, `rawScoreSelfplay`, `rawScoreSelfplayStdev`, `rawStScoreError`, `rawStWrError`, `rawVarTimeLeft`, `rawNoResultProb`, `symHash`, `thisHash` |
| **`moveInfos`** (21 por jugada candidata) | `move`, `visits`, `winrate`, `scoreMean`, `scoreLead`, `scoreSelfplay`, `scoreStdev`, `prior`, `lcb`, `utility`, `utilityLcb`, `order`, `pv`, `pvVisits`, `pvEdgeVisits`, `edgeVisits`, `edgeWeight`, `weight`, `playSelectionValue`, `ownership`, `ownershipStdev` |

**Ninguno de esos campos es un objeto de Go.** No existe una clave `moyo`, ni `joseki`, ni
`shape`, ni `influence`, ni `sente`. No hay ninguna salida en la que KataGo nombre una
estructura o situación del juego. Lo que hay son **números por intersección y por jugada
candidata**.

**La única excepción en todo el motor** está en la interfaz GTP —no en `analysis`—: el comando
`final_status_list` acepta exactamente tres argumentos, `dead`, `alive` y `seki`, y ahí sí el
motor se compromete con una **etiqueta discreta** del juego. Es la única categorización de Go
que KataGo emite por sí mismo. (Verificado: sobre una partida completa del corpus devolvió 29
piedras muertas, 126 vivas, 0 en seki.) Notablemente, **`dame` no está** entre los argumentos
aceptados.

---

## 6. Cómo llegamos nosotros a "moyo"

### 6.1 KataGo no sabe qué es un moyo

Es la pregunta que ordena todo este documento: si el motor no dice "moyo", ¿cómo sabe qué es
uno? **No lo sabe, y no lo dice.**

Lo que la red aprendió es algo más simple y más útil. Su cabeza de *ownership* está entrenada
para predecir, en cada una de las 361 intersecciones, **quién será el dueño de ese punto al
final de la partida**, en una escala continua de `−1` (negro) a `+1` (blanco). Es un **campo
escalar**, nada más. La red nunca vio la palabra "moyo" ni ningún concepto de Go nombrado:
aprendió a estimar un número por punto a partir de millones de partidas de autojuego, y su
señal de entrenamiento fue el resultado real del conteo final, no una taxonomía humana.

Que ese campo *se parezca* a lo que un jugador llama influencia no es porque la red conozca la
teoría del Go, sino porque la teoría del Go es una descripción humana aproximada de la misma
regularidad que la red estimó directamente.

### 6.2 El moyo es construcción nuestra

El moyo aparece en el paso siguiente, íntegramente del lado del pipeline
(`experiments/07_moyo_dataset/src/moyo_detector.py`):

1. Se toma el mapa de `ownership` que devolvió el motor.
2. Se agrupan los puntos **vacíos** por inundación (*flood-fill*) en regiones conexas.
3. Cada región se clasifica según su `ownership` **promedio**, contra umbrales que **elegimos
   nosotros**:

   | Banda | Constante en el código | Categoría |
   |---|---|---|
   | `|own| > 0.85` | `SETTLED_THRESHOLD` | territorio asentado |
   | `0.15 ≤ |own| ≤ 0.85` | — | **moyo** |
   | `|own| < 0.15` | `NEUTRAL_THRESHOLD` | neutral (*dame*) |

   con un tamaño mínimo de región de 4 puntos (`MIN_MOYO_SIZE`).
4. La etiqueta que se busca predecir, `pct_black`, es el porcentaje de control negro de la
   región — derivada del mismo campo.

Es decir: **"moyo" es un constructo operacional** — una región conexa de puntos vacíos cuyo
promedio de `ownership` cae en una banda elegida. Los umbrales `0.85`, `0.15` y el tamaño
mínimo `4` son decisiones de diseño: no son hechos del Go ni salidas de KataGo.

### 6.3 Cuánto hay de motor y cuánto de interpretación, por categoría

| Categoría | Quién define la **región** | Quién pone la **etiqueta** |
|---|---|---|
| moyo | nuestros umbrales sobre `ownership` | `ownership` |
| territorio | nuestros umbrales sobre `ownership` | `ownership` |
| fuseki | los mismos umbrales, aplicados en jugadas 3–15 % | `ownership` |
| joseki | **geometría pura: las 4 esquinas fijas**; el motor no interviene | `ownership` |

Joseki es el caso extremo: esas regiones existirían igual sin motor alguno — solo la etiqueta
viene de KataGo. **Ninguna de las cuatro categorías es una categoría de KataGo.**

Definir un constructo operacional es práctica científica normal y no invalida nada. Pero obliga
a ser preciso sobre qué queda afirmado, que es el asunto de la sección siguiente.

---

## 7. Qué queda licenciado afirmar, y qué no

**Licenciado, y sólido:**

> Un campo de Ising clásico predice, mejor que la geometría del tablero, el `ownership` medio de
> las regiones vacías conexas dentro de una banda dada.

Ese es el resultado del Experimento 07: ΔR² = 0.44 sobre 14 partidas nunca vistas por ninguna
búsqueda de coeficientes, para un modelo completo con R² = 0.73, equivalente a una correlación
r ≈ 0.86 contra el territorio estimado por KataGo.

**Todavía no licenciado:**

> "El Hamiltoniano predice el moyo", entendido como concepto de Go.

Porque ahí "moyo" es una elección de umbral. La prueba que falta es de **sensibilidad a los
umbrales**: si ΔR² aguanta mover `0.85` / `0.15` / tamaño mínimo, el constructo es robusto; si
se mueve apreciablemente, parte del resultado es artefacto de la banda elegida.

### 7.1 Dos hallazgos que hacen pertinente la advertencia

**(a) La capa de interpretación es menos estable que la medición.** Comparando dos corridas del
motor sobre **exactamente los mismos tableros** con distinto presupuesto de búsqueda
(`maxVisits` 250 contra 600):

- solo **131 de 262 regiones** conservan el mismo conjunto de puntos;
- allí donde la región sí coincide, las etiquetas son casi idénticas: correlación **r = 0.974**,
  mediana de diferencia **0.3 puntos porcentuales**.

La conclusión es nítida: **el `ownership` de KataGo es estable; el flood-fill con umbral fijo
sobre un campo continuo con ruido no lo es.** Las fronteras se mueven y las regiones se parten
o se funden. Corolario metodológico: **ningún ΔR² es comparable entre caches distintos**.

**(b) El cache guardó la interpretación y descartó la medición.** Los archivos de cache
almacenan `board`, las regiones ya clasificadas y sus agregados (`pct_black`,
`ownership_stdev_mean`, `policy_mass`), pero **no guardan el `ownership` crudo**. Por lo tanto,
reclasificar con otros umbrales —o habilitar la banda `neutral`— exige **volver a correr el
motor**, no reprocesar.

Es, en la lectura actual, el defecto de diseño más consecuente del pipeline, y el arreglo hacia
adelante es trivial: almacenar los 361 flotantes por posición (kilobytes). Queda anotado como
prioridad de la próxima corrida de KataGo.

---

## 8. Los dos experimentos activos

### 8.1 Experimento 07 — empírico

Corre KataGo **una sola vez por posición** sobre 20 partidas profesionales, cachea tablero +
regiones + geometría, y luego evalúa cientos de Hamiltonianos reutilizando ese cache (el paso
caro es el motor; evaluar un campo es barato). Mide ΔR² por encima de la base geométrica.

De ahí salieron las dos rondas de optimización directa de coeficientes: **Fase A** sobre
`sparse_cubic` (4 coeficientes, la forma de M1) y **Fase B** sobre `cubic_mixed` completa,
reparametrizada en las 4 dimensiones efectivas. El mejor resultado del proyecto,
`H_OPT_B`, salió de Fase B.

### 8.2 Experimento 08 — teórico

No corre KataGo ni predice nada nuevo. Toma **un solo hallazgo** surgido dentro del 07 —que dos
vectores de coeficientes muy distintos daban ΔR² idéntico a cuatro decimales— y explica **por
qué** tiene que ser así, de manera sistemática.

El argumento en una línea: el predictor nunca evalúa `H` en un solo orden de argumentos, sino
siempre la suma simétrica `H(s,q) + H(q,s)`. Esa suma es, literalmente, promediar sobre la
simetría de posición `σ: (x,y) → (y,x)`, y un promedio así **aniquila exactamente** la parte
antisimétrica. De los 7 coeficientes, sobreviven 4 combinaciones —`Σa`, `Σb`, `b₁₂`, `Σc`— y
mueren 3 —`Δa`, `Δb`, `Δc`— sin importar su magnitud.

Añadiendo una segunda simetría, la de color `τ: (x,y) → (−x,−y)`, las dos generan el **grupo de
Klein** `Z₂ × Z₂`, y la proyección de Reynolds descompone cualquier Hamiltoniano en cuatro
piezas. La pieza `P₊₋` —impar en color, visible al campo— resulta ser exactamente el **sesgo de
color**: la componente que hace que un Hamiltoniano prefiera un color aun sin información
posicional alguna.

**La ida y vuelta entre ambos experimentos** es lo que da coherencia a la línea: la anomalía
empírica del 07 exigió una explicación que el 08 dio en forma de teorema; y ese teorema
garantizó la reparametrización de 7 a 4 dimensiones con la que Fase B encontró el mejor
resultado empírico del proyecto.

---

## 9. El Experimento 06, y por qué está en pausa

**De qué trataba.** Si un Hamiltoniano `H(x,y)` define una superficie `z = H(x,y)`, sus
propiedades matemáticas intrínsecas —puntos críticos, nodos `A₁`, fibra de Milnor, persistencia
`H₁`— deberían decir algo sobre su calidad como modelo de Go. Con esos invariantes se ordenaron
305 candidatos cúbicos por dominancia de Pareto (148 frentes), y al mejor grupo se lo llamó
**Frente 1**.

**Por qué se detuvo.** La hipótesis era falsable, y falló dos veces:

1. Contrastado contra el ΔR² real, el Frente 1 fue el grupo de **peor** desempeño (0.055 a
   radio 9, contra 0.152–0.170 de los grupos medios y tardíos). El criterio no era neutro:
   seleccionaba en la dirección equivocada.
2. El Experimento 08 explicó el mecanismo: el análisis topológico evalúa `H(x,y)` **sin
   simetrizar**, de modo que mezcla las 4 dimensiones que el predictor ve con las 3 que son
   ruido puro para él. Se repitió el análisis sobre el polinomio *reducido* —el objeto que el
   campo realmente evalúa— y el resultado también fue nulo (|ρ| ≤ 0.21, p > 0.31).

**Por qué "en pausa" y no "descartado".**

- **La infraestructura sobrevivió y sostiene todo lo posterior.** El catálogo de 305 candidatos
  con coeficientes, el código de puntos críticos, el visor interactivo y el diagrama de Hasse
  son la base sobre la que corren los Experimentos 07 y 08.
- **El rango muestral de la prueba fue limitado.** Las correlaciones se calcularon sobre los 44
  candidatos con ΔR² medido, y esos 44 son mayoritariamente **aleatorios débiles**. Una
  hipótesis puede fallar sobre una población pobre sin que quede resuelta sobre una bien
  elegida.
- **Ahora sí sabemos cómo clasificar los polinomios cúbicos.** Cuando se corrió el 06 no
  existía la descomposición de Klein: no había forma de saber qué dimensiones del polinomio son
  relevantes y cuáles invisibles. Hoy sí — y significativamente, el criterio que **sí** predice
  (el sesgo de color `β`, con ρ = −0.71 contra el desempeño real) apareció de mirar la
  estructura de **simetría**, no la de puntos críticos.

**Cómo se retomaría.** Reconstruir el catálogo clasificado por las coordenadas efectivas
`(Σa, Σb, b₁₂, Σc)` —y eventualmente la quinta dimensión `x²y²` de §3.3—, muestrear de forma
equilibrada dentro de esas clases en vez de uniformemente en los 7 coeficientes crudos, y recién
entonces preguntar si la topología de la variedad reducida separa a los buenos de los malos.
Sería la primera prueba sobre una población construida a propósito. **La rama espera esa
clasificación; no está cerrada por refutación definitiva.**

---

## 10. Glosario mínimo

| Término | Significado |
|---|---|
| **Moyo** | Marco territorial grande y aún disputado. En el pipeline: región vacía conexa con `ownership` medio en `[0.15, 0.85]` |
| **`ownership`** | Mapa de KataGo: control esperado al final de la partida, por intersección, en `[−1, +1]` |
| **`pct_black`** | Porcentaje de control negro de una región. La variable objetivo |
| **Espín** | Valor `s ∈ {−1, 0, +1}` por intersección: negro, vacío, blanco |
| **Hamiltoniano `H(x,y)`** | Polinomio de interacción de pares. Plantilla `cubic_mixed` (7 coeficientes) o `sparse_cubic` (4, sin términos `b`) |
| **Peso de Boltzmann** | `exp(−E/T)`: probabilidad relativa de una configuración de energía `E` a temperatura `T` |
| **Campo de relajación `F`** | Aproximación iterativa al espín esperado por punto vacío; las piedras quedan fijas como frontera |
| **ΔR²** | Ganancia de R² del campo sobre el modelo base de 3 variables geométricas. Métrica única del proyecto |
| **σ, τ** | Involuciones de posición `(x,y) → (y,x)` y de color `(x,y) → (−x,−y)`; generan el grupo de Klein |
| **Sesgo de color** | La proyección `P₊₋(H)`; no nulo ⟺ `(Σa, Σc) ≠ (0,0)` |
| **β(H)** | Campo relajado medio en tablero vacío: diagnóstico del sesgo, de costo cero |

---

## Referencias

- Rojas-Domínguez, A., Barradas-Bautista, D. y Alvarado, M. (2019). *Atomic-Go*. IEEE Access.
- Fischbach, M. A. y Walsh, C. T. (2024). *Problem choice and decision trees in science and
  engineering*. Cell, 187, 1828–1833.
- Jiménez Martínez, L. (2026). *Predicción de moyos con Hamiltonianos clásicos de Ising:
  informe completo, experimentos 07+08*. Documento interno del proyecto.
- KataGo v1.16.5 — <https://github.com/lightvector/KataGo>
