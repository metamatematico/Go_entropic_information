# Experimento 09 — Sistema axiomático para el juego de Go

Auditoría, reparación e integración de la formalización de **Emil Estuardo García
Bustamante** (2022), y ejecución del programa de derivación.

> Contexto y motivación —por qué se abrió esta rama y cómo se conecta con los
> experimentos 07 y 08— en la [Parte VI del README principal](../../README.md#parte-vi--experimento-09-axiomatización-del-go).

---

## Qué contiene el sistema

**Cuatro primitivas** no definidas: un conjunto `P` de puntos, una relación de
adyacencia `∼`, tres colores `Λ`, dos jugadores `℘`. Todo lo demás se define.

**Cinco grupos de axiomas:**

| Grupo | Contenido |
|---|---|
| T | Tablero: finitud, adyacencia irreflexiva y simétrica, conexidad, instancia 19×19 |
| C | Configuraciones: coloración de puntos; cadenas y regiones como componentes conexas |
| D | Dinámica: posición, jugadas, colocación, capturas, legalidad, alternancia, terminación |
| S | Escrutinio: puntuación por área y por territorio |
| E | Estrategias y valor |

**El sistema de reglas es un parámetro, no un axioma:**
`ℜ = ⟨ς, κ, ϵ, komi⟩` con `ς` ∈ {suicidio prohibido, permitido},
`κ` ∈ {ko simple, superko posicional, superko situacional}, `ϵ` ∈ {área, territorio}.
Cada teorema declara de qué componentes depende.

**Sobre esa base:** 33 teoremas demostrados y un catálogo de **171 conceptos del
Go** como objetivos de derivación, cada uno etiquetado con el grupo de axiomas o el
módulo de extensión que lo soporta.

**Cuatro módulos de extensión** (material que el sistema aún no contiene):

| Módulo | Contenido | Sostiene |
|---|---|---|
| M1 | Descomposición y valor | sente, gote, miai, joseki, final de partida |
| M2 | Juegos cíclicos | lucha de ko, valor con ciclos |
| M3 | **Magnitudes graduadas** | **influencia, moyo, espesor, aji, ligereza** |
| M4 | Clasificación de patrones | formas salvo simetría y traslación |

> **M3 es el módulo que toca directamente a los experimentos 07 y 08.** Ahí es
> donde el campo de Ising queda absorbido como objeto definido —campo de influencia
> `φ_j`, campo diferencial `Δ`, moyo como conjunto de nivel `M^θ_j`— sujeto a un
> criterio de calibración comprobable.

---

## Estado del programa

| Paso | Estado | Resultado o pendiente |
|---|---|---|
| 1. Cerrar el grupo D | cerrado | Abierto: la igualdad `C_alc = C_leg` en 19×19 |
| 2. Grupo y conexión garantizada | **cerrado en negativo** | La conexión incondicional no es transitiva: el grupo es un *parámetro*, no un derivado |
| 3. Benson dentro del sistema | cerrado en la suficiencia | La recíproca sigue importada con atribución |
| 4. Semeai | cerrado | Demostrado con y sin ojos, e instanciado en el sistema; caracterización del seki como corolario |
| 5. Módulo M2 y ko | parcial | Pendiente: valor de posiciones con ko no aislado |
| 6. Módulo M1 y final | cerrado sin ko | Pendiente: bloques con seguimiento forzado, infinitesimales |
| 7. Módulo M3 | **abierto, mejor delimitado** | El criterio disponible es vacuo en la apertura; el sustituto no puede apoyarse en el estrato 6 |
| 8. Módulo M4 | cerrado en negativo | La simetría global no reduce; se reorienta a patrones acotados |

**Estatus epistémico.** Sobreviven un solo enunciado *verificado sin demostrar* (la
cota de seis piedras, comprobada por exhaución en 6×6 y 7×7) y una sola importación
con atribución (la recíproca de Benson). El documento distingue explícitamente lo
*demostrado* de lo *verificado en un rango finito*.

---

## Archivos pendientes de integrar

Esta carpeta está creada pero **todavía no contiene el material del experimento**.
Falta versionar aquí:

| Archivo | Qué es | Destino sugerido |
|---|---|---|
| `sistema_axiomatico_go.pdf` / `.tex` | El documento completo: auditoría, sistema, 33 teoremas, catálogo, ejecución por agentes, tres rondas de enmiendas | `output/reports/` |
| `verificaciones.py` | Reproduce en un bloque ejecutable los cómputos de los teoremas 10.3, 10.5, 10.8, 5.12, 10.17, 10.26, 10.15 y 10.29, y las dos configuraciones de la Observación 10.14 | `src/` |

Nota sobre `verificaciones.py`: las comprobaciones **no sustituyen** a las
demostraciones. Acotan el riesgo de error en los enunciados y, en el caso del
Teorema 10.3, **constituyen la demostración misma**, por tratarse de una
enumeración finita.

---

## Referencias

- García Bustamante, E. E. (2022). *Hacia una teoría matemática del juego de Go:
  tácticas, estrategias, influencia y control de territorio*. Tesis de licenciatura
  en Matemáticas, Facultad de Ciencias, UNAM. Tutor: J. M. Alvarado Mentado.
- Benson, D. B. (1976). *Life in the game of Go*. Information Sciences 10, 17–29.
- Berlekamp, E. y Wolfe, D. (1994). *Mathematical Go: Chilling Gets the Last Point*.
- Robson, J. M. (1983). *The complexity of Go*. Proceedings IFIP, 413–417.
- Tromp, J. y Farnebäck, G. (2016). *Combinatorics of Go*.
