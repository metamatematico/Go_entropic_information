# Preregistro — Ruta B: especialistas por categoría y matriz de transferencia

**Fecha de congelación:** 2026-07-31
**Estado del repositorio:** `7bd96e0` + los módulos de prerrequisito descritos en §0
**Autores:** Leonardo Jiménez Martínez
**Estatus:** congelado antes de correr cualquier búsqueda. Toda desviación posterior se registra en §10.

Este documento fija, **antes** de ver un solo resultado, qué se va a correr, cómo se va a
medir y qué contará como confirmación o refutación. El proyecto lleva tres inversiones de
ranking documentadas al cambiar la metodología de medición sin cambiar los datos; multiplicar
comparaciones (4 categorías × varios candidatos) sin fijar las reglas de antemano
multiplicaría ese riesgo. El preregistro es la contramedida.

---

## §0. Estado verificado antes de empezar

Estos prerrequisitos ya se cumplieron y quedan como línea base. Reproducibles con
`python src/validate_prereq.py --n-boot 500`; salida en `output/validate_prereq.json`.

**Código nuevo incorporado al repositorio** (la Parte IV se había producido fuera de él):

| Módulo | Contenido |
|---|---|
| `experiments/08_teoria_invariantes/src/klein.py` | proyecciones de Reynolds $P_{\pm\pm}$, acción de $\sigma$/$\tau$, sesgo de color $P_{+-}$, coeficientes efectivos, verificación simbólica |
| `experiments/07_moyo_dataset/src/features.py` | `equivariant_fields()` ($F$, $F_{eq}$, $F_{bias}$) y `beta_empty_board()` |
| `experiments/07_moyo_dataset/src/bootstrap.py` | bootstrap por partida, marginal **y pareado** |
| `experiments/07_moyo_dataset/src/evaluate.py` | DataFrame con varios Hamiltonianos × varios predictores sobre las mismas filas |
| `experiments/07_moyo_dataset/src/validate_prereq.py` | las pruebas T1–T4 de esta sección |

**T1 — $\beta(H)$ en tablero vacío** (r=1, 15 barridos, 9×9): $H_{M1}$ −0.6599, Alvarado
−0.0000, $H_{OPT\_A}$ +0.5110, $H_{OPT\_B}$ +0.4017. Publicado: −0.66, 0.00, +0.51, +0.40. ✓
La regla $\mathrm{sign}(\beta) = -\mathrm{sign}(\Sigma_a)$ se cumple en los cuatro.

**T2 — Equivariancia**: $\max|F(-B)+F(B)|$ vale 5.97e−15 para Alvarado (precisión de máquina)
y 0.63–1.56 para los otros tres. Dicotomía exacta, sin casos intermedios, y coincide con
`klein.has_color_bias` en los cuatro. ✓

**T3 — Descomposición de Klein**: suma de proyecciones $=H$ exacto y $\sigma\tau=\tau\sigma$
verificados simbólicamente sobre `cubic_mixed` genérico. Normas por pieza reproducidas. ✓
**Corrección detectada:** la Figura 4 del informe da $|P_{--}(H_{OPT\_A})| = 0.82$; el valor
correcto es **0.917**. El 0.82 sale de dividir $\Delta_a$ entre 2 dos veces (el informe
reporta $\Delta_a \approx -0.340$ en su §14, cuando su propia definición
$\Delta_a=a_1-a_2$ da $-0.6796$ — que es lo que el repositorio ya guarda correctamente en
`hamiltonians_clasificados.json`). No altera ninguna conclusión: $P_{--}$ es justamente la
pieza que el campo nunca ve.

**T4 — $\Delta R^2$ sobre moyo** (r=9, 8 barridos, `cache_full20`, 864 regiones, 500 réplicas):

| predictor | medido | publicado |
|---|---|---|
| $H_{M1}$ · $F$ | 0.2981 | 0.298 ✓ |
| $H_{M1}$ · $F_{eq}$ | 0.3568 | 0.357 ✓ |
| $H_{M1}$ · $F_{bias}$ | 0.0011 | 0.001 ✓ |
| $H_{OPT\_B}$ · $F$ | 0.4534 | 0.453 ✓ |
| $H_{OPT\_B}$ · $F_{eq}$ | 0.4567 | 0.457 ✓ |
| $H_{OPT\_B}$ · $F_{bias}$ | 0.0007 | 0.001 ✓ |

**Hallazgo 1 — la "ruta de evaluación" era el cache.** El Cuadro 8 del informe atribuyó la
diferencia entre 0.453 y 0.421 a "detalles de la ruta de evaluación" sin identificarlos. Son
el cache: de los cuatro caches de 20 partidas, solo `cache_full20` reproduce las cifras de la
Parte IV.

| cache | posiciones | moyos | $H_{M1}$·$F$ | $H_{OPT\_B}$·$F$ |
|---|---|---|---|---|
| `cache_full20` | 115 | 864 | 0.2981 | 0.4534 |
| `cache_full20_rich` | 113 | 864 | 0.2967 | 0.4394 |
| `cache_full20_cats` | 120 | 872 | 0.2774 | 0.4210 |

La brecha entre rutas (0.03 en $H_{OPT\_B}$) es del mismo orden que el optimismo por traslape
búsqueda–validación (0.06). **Fijar el cache es una decisión de preregistro, no un detalle.**

**Hallazgo 2 — las regiones no son estables entre corridas de KataGo.** Comparando
`cache_faseA` (maxVisits=250) contra el subconjunto de las mismas 6 partidas de
`cache_full20_cats` (maxVisits=600): las posiciones y los tableros son **idénticos**, pero
solo **131 de 262 regiones conservan el mismo conjunto de puntos**. Donde la región coincide,
la etiqueta es casi la misma (mediana 0.3 pts, media 1.1, $r=0.974$). Es decir: la variabilidad
no está en `ownership`, está en las fronteras del *flood-fill*, que se mueven y parten o funden
regiones. Consecuencia dura: **ningún $\Delta R^2$ es comparable entre caches distintos**, y
toda comparación de este preregistro vive dentro de un solo cache.

**Hallazgo 3 — la categoría `neutral` NO es gratis.** El cache guarda `board`, `moyos` y
`territory`, pero **no** guarda `ownership`. Reconstruir la banda neutral exige volver a correr
KataGo, no solo reprocesar. Queda **fuera** de la Ruta B y se difiere a la ronda de partidas
nuevas.

---

## §1. Preguntas e hipótesis

Cada hipótesis se enuncia con dirección predicha y criterio de refutación fijado de antemano.

**H1 — Especialización.** Un Hamiltoniano optimizado sobre una categoría supera, *en esa
categoría*, al mejor generalista disponible.
*Predicción:* $\Delta R^2(H_{OPT\_cat}) > \Delta R^2(H_{OPT\_B})$ en hold-out, para cada
categoría distinta de moyo.
*Refutada si:* el IC 95 % pareado de la diferencia contiene el cero en ≥3 de las 4 categorías.

**H2 — Costo de la transferencia.** Los especialistas se degradan fuera de su categoría.
*Predicción:* la pérdida media fuera de la diagonal de la matriz es > 0.
*Refutada si:* la pérdida media fuera de la diagonal es ≤ 0, o su IC contiene el cero.

**H3 — Existe un generalista.** Hay un $H$ cuyo $\Delta R^2$ mínimo entre las 4 categorías
queda a menos de $\delta = 0.05$ del especialista de cada categoría.
*Predicción:* existe. $\delta = 0.05$ se fija ahora, por ser ~1/3 del ancho típico de los IC
(0.13–0.15) — una brecha menor no es distinguible con 20 partidas.
*Refutada si:* ningún candidato evaluado cumple la condición.

**H4 — Geometría del óptimo (la pregunta de fondo).** Los especialistas se agrupan en el
espacio efectivo $(\Sigma_a,\Sigma_b,b_{12},\Sigma_c)$, indicando una sola física con ajuste
fino por categoría, en vez de físicas distintas.
*Predicción:* la distancia media por pares entre los 4 especialistas, en coordenadas
normalizadas por el rango de búsqueda, es menor que la de 4 puntos uniformes en la misma caja
(línea base analítica; se compara contra 10 000 cuaternas simuladas, semilla 20260731).
*Refutada si:* la distancia media observada no queda por debajo del percentil 5 de la
distribución simulada.

**H5 — $\beta$ predice estabilidad de categoría.** El diagnóstico de costo cero que ya predice
la estabilidad de radio ($\rho=-0.71$) también predice la consistencia entre categorías.
*Predicción:* $|\beta|$ correlaciona positivamente con el coeficiente de variación de
$\Delta R^2$ entre categorías (Spearman, una cola).
*Refutada si:* $\rho \le 0$ o $p > 0.05$.
*(Exploratoria: se reporta pase lo que pase; no entra en el control de §6.)*

---

## §2. Decisiones congeladas

Todo lo de esta tabla queda fijo. Cambiar cualquier fila después de ver resultados es una
desviación y se registra en §10.

| Parámetro | Valor | Justificación |
|---|---|---|
| **Predictor** | $F_{eq}$ (`equivariant_fields`) | Recomendación Fase C′: nunca pierde, a veces gana (T4: +0.059 en $H_{M1}$, sin cambio en $H_{OPT\_B}$), y vuelve interpretable el 0 |
| **Métrica** | $\Delta R^2$ sobre base geométrica de 3 columnas | Único parámetro fijo del proyecto |
| **Base geométrica** | `dist_to_nearest_black`, `dist_to_nearest_white`, `dist_to_edge` | Idéntica a todo el experimento |
| **Radio** | 9 | Estándar del informe |
| **Barridos — búsqueda** | 4 | Idéntico a Fases A y B, para comparabilidad directa |
| **Barridos — validación** | 8 | Idéntico a Fases A y B |
| **Temperatura** | $T=1.0$ | Nunca se varió en el proyecto; se mantiene fija y se anota como parámetro no explorado |
| **Malla de espines** | 41 puntos en $[-1,1]$ | Valor del repositorio |
| **Espacio de búsqueda** | $(\Sigma_a,\Sigma_b,b_{12},\Sigma_c)$ | Garantía del Exp. 08 |
| **Cotas** | `BOUNDS_4D` = $[-6,6]^2\times[-3,3]\times[-2,2]$ | Idénticas a Fase B. **$b_{12}$ se mantiene en $[-3,3]$** aunque Fase B tocó el borde: ampliarlo rompe comparabilidad y es su propia corrida (Ruta E) |
| **Optimizador** | `differential_evolution`, `maxiter=15`, `popsize=8`, `seed=42`, `workers=1`, `polish=True`, `tol=1e-4` | Idénticos a Fase B |
| **Siembra** | $H_{M1}$ → (3, 0, 0, −2); $H_{OPT\_A}$ → (−1.0012, 0, 0, 0.8607); Alvarado → (0, 0, 1, 0) | Idéntica a Fase B |
| **Inferencia** | bootstrap **pareado** por partida, 500 réplicas, `seed=1` | §5 |
| **Cache — moyo, territorio** | `cache_full20_cats` | Único con territorio; maxVisits=600 |
| **Cache — fuseki, joseki** | `cache_early20` | Único con jugadas 3–15 % y esquinas |

**Categorías y claves de región** (verificadas contra los caches):

| Categoría | Cache | Clave | Búsqueda (6 partidas) | Hold-out (14 partidas) |
|---|---|---|---|---|
| moyo | `cache_full20_cats` | `moyos` | 36 pos / 262 reg | 84 pos / 610 reg |
| territorio | `cache_full20_cats` | `territory` | 36 pos / 65 reg | 84 pos / 247 reg |
| fuseki | `cache_early20` | `moyos` | 24 pos / 138 reg | 56 pos / 355 reg |
| joseki | `cache_early20` | `joseki` | 24 pos / 96 reg | 56 pos / 224 reg |

---

## §3. Diseño: búsqueda y hold-out

**La partición se fija ahora y no se toca.** Las 6 partidas de búsqueda son exactamente las
que usaron Fases A y B, verificadas presentes en ambos caches (6/6):

```
31mn-gokifu-20200319-Gu_Lingyi-Tao_Xinran.sgf
31pr-gokifu-20200323-Li_Xiaoxi-Lu_Jia.sgf
31ps-gokifu-20200323-Tang_Yi-Wang_Shuang.sgf
31pt-gokifu-20200324-Wang_Chenxing-Tang_Yi.sgf
31pu-gokifu-20200324-Lu_Jia-Cao_Youyin.sgf
31pv-gokifu-20200324-Chen_Yiming-Li_Xiaoxi.sgf
```

Las otras 14 son hold-out: **ningún optimizador las toca**, en ninguna categoría. Mantener las
mismas 6 preserva la comparabilidad con $H_{OPT\_A}$/$H_{OPT\_B}$ y deja el mismo hold-out de
la §19 del informe.

**Nota de interpretación fijada de antemano:** $H_{OPT\_B}$ fue optimizado sobre estas 6
partidas *en moyo*. Por eso, en moyo no es un control limpio, y en las otras tres categorías es
un generalista *transferido* — no uno ajustado a ellas. El único control nunca optimizado sobre
estos datos es $H_{M1}$, y por eso se reporta en todas las celdas.

**Resultado primario:** todo lo declarado se declara sobre las **14 partidas hold-out**. Las 6
de búsqueda se reportan solo para cuantificar el optimismo, nunca para concluir.

---

## §4. Plan de análisis: la matriz de transferencia

Filas = candidatos; columnas = categorías; celda = $\Delta R^2$ con $F_{eq}$ en hold-out,
con IC 95 % pareado por partida.

Candidatos: $H_{M1}$ (control), Alvarado, $H_{OPT\_A}$, $H_{OPT\_B}$, $H_{0202}$ (aleatorio
balanceado), y los 4 especialistas nuevos $H_{OPT\_moyo}$, $H_{OPT\_terr}$, $H_{OPT\_fuseki}$,
$H_{OPT\_joseki}$. Total 9 × 4 = 36 celdas.

**Salidas primarias**
1. La matriz completa (punto + IC pareado).
2. Diagonal contra fila: pérdida de cada especialista fuera de su categoría (H2).
3. El maximin: $\arg\max_H \min_{cat} \Delta R^2$ (H3).
4. Posición de los 4 especialistas en $(\Sigma_a,\Sigma_b,b_{12},\Sigma_c)$ (H4).

**Salidas secundarias (exploratorias, sin control de §6)**
5. $|\beta|$ contra el CV entre categorías (H5).
6. $F$ contra $F_{eq}$ por categoría, para ver si la ganancia de simetrizar depende de la categoría.
7. La predicción falsable pendiente del informe: bajo $F_{eq}$, la brecha
   balanceados/sesgados (0.257 vs 0.148) debe encogerse.

---

## §5. Inferencia

Toda comparación entre dos candidatos se hace con **bootstrap pareado por partida**: en cada
réplica se remuestrean las partidas una sola vez y se calcula $\Delta R^2$ de ambos candidatos
sobre *ese mismo* remuestreo; el IC se construye sobre la diferencia.

Se abandona el criterio de "IC marginales que se traslapan". Es el test equivocado y
conservador de más: los candidatos se evalúan sobre las mismas partidas, así que la
variabilidad común entre partidas se cancela al restar. T4 ya lo muestra — $F$ contra $F_{eq}$
en $H_{M1}$ tiene IC marginales muy traslapados (\[0.225, 0.368\] y \[0.275, 0.429\]) y sin
embargo la diferencia pareada es \[−0.071, −0.021\], sin cruzar el cero.

Se reporta siempre el par (punto, IC pareado). **Se retiran de las tablas principales los
p-valores por fila** (prueba $F$), que suponen independencia entre regiones de la misma partida.

---

## §6. Control de comparaciones múltiples

**Familia primaria:** las 4 pruebas de H1 (especialista vs $H_{OPT\_B}$, una por categoría).
Se aplica **Holm–Bonferroni** con $\alpha=0.05$ sobre esas 4. Una categoría solo se declara
si sobrevive la corrección.

H2 y H3 son pruebas únicas, sin corrección. H4 es una prueba única contra línea base simulada.
H5 y las salidas 5–7 son exploratorias: se reportan con su $p$ crudo y **etiquetadas como
exploratorias**, y no sustentan ninguna declaración.

**Compromiso de reporte completo:** se reportan las 36 celdas de la matriz, converjan o no las
búsquedas, salgan o no en la dirección predicha. Si un especialista sale peor que el
generalista, se reporta.

---

## §7. Auditorías obligatorias antes del análisis principal

Se corren **primero**; sus resultados pueden invalidar el uso de una categoría.

**A1 — ¿La base geométrica de joseki está degenerada?** Las regiones joseki son las 4 esquinas
fijas, definidas por geometría pura y no por `ownership`. Si `dist_to_edge` y las distancias a
piedras son casi constantes entre ellas, el modelo base no discrimina y el $\Delta R^2$ de
joseki mide contra un rival artificialmente débil — no comparable con moyo.
*Criterio:* si $R^2_{\text{geom sola}} < 0.05$ en joseki, la categoría se reporta **con
advertencia explícita** y queda fuera de H3 y H4.

**A2 — ¿Cuánta señal hay que capturar en territorio?** El informe midió $R^2$ geométrico de
0.670 en territorio. Se recalcula bajo este protocolo y se reporta junto a cada $\Delta R^2$,
porque una ganancia de 0.11 sobre una base de 0.67 no significa lo mismo que sobre una de 0.31.

**A3 — Verificación de la reparametrización, por categoría.** Antes de cada búsqueda, evaluar
$H_{M1}$ mapeado a $(3,0,0,-2)$ y confirmar que reproduce el $\Delta R^2$ de sus coeficientes
crudos en esa categoría. Es la misma verificación que hizo Fase B; si falla en alguna
categoría, esa búsqueda no se lanza.

---

## §8. Lo que este preregistro NO hará

- **No amplía las cotas de $b_{12}$.** Corrida separada (Ruta E), sin mezclar con esta matriz.
- **No incorpora partidas nuevas.** La Ruta C es independiente y posterior; mezclarlas rompería
  la partición congelada en §3.
- **No incluye la categoría neutral** (Hallazgo 3: exige KataGo nuevo).
- **No incluye vida/muerte ni aji**: requieren un mecanismo a nivel de grupo, no una extensión
  del campo por punto.
- **No usa ponderación por `ownershipStdev`.** Es una segunda metodología de medición que ya
  invirtió un ranking una vez; mezclarla aquí confundiría el efecto de categoría con el de
  ponderación. Se difiere a su propia corrida.
- **No re-optimiza $T$ ni `n_sweeps`.** Quedan fijos y anotados como no explorados.

**Un resultado nulo es un resultado.** Si H1 se refuta (los especialistas no superan al
generalista), la conclusión —que una sola física de Ising sirve para todas las categorías— es
más fuerte e interesante que la alternativa, y se publica igual.

---

## §9. Costos medidos

Medidos en esta máquina, no estimados: una relajación a r=9 con 8 barridos toma 0.56 s;
una evaluación completa del objetivo sobre el conjunto de búsqueda, con $F_{eq}$ (dos
relajaciones por posición):

| Categoría | 4 barridos | 8 barridos |
|---|---|---|
| moyo / territorio (36 pos) | 19.8 s | 37.2 s |
| fuseki / joseki (24 pos) | 16.6 s | 33.7 s |

Con el presupuesto de Fase B (692 evaluaciones) y 4 barridos: **≈3.2–3.8 h por categoría,
≈14 h las cuatro**. Corre en segundo plano. La matriz de evaluación final (9 candidatos × 4
categorías sobre las 20 partidas, 8 barridos) son ≈2 h más.

`workers=1` es obligatorio: el objetivo cierra sobre un `Hamiltonian` con función `lambdify`
de sympy, que no es serializable para multiproceso.

---

## §10. Registro de desviaciones

Toda diferencia entre lo ejecutado y lo escrito arriba se anota aquí, con fecha y motivo, en
vez de editar el cuerpo del documento.

| Fecha | Sección | Desviación | Motivo |
|---|---|---|---|
| — | — | — | — |
