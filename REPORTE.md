# Reporte de Hallazgos
## Análisis Comparativo de Modelos de Ising Aplicados al Juego de Go

**Autores del análisis:** Leonardo Jiménez Martínez & Mario Mercado Sánchez (repositorio Ometitlan)  
**Paper relacionado:** *"Pattern Acquisition and Comparative Analysis in the Game of Go"*,  
Jiménez Martínez & Sesma González — Journal of Go Studies, Vol. 19 No. 2, 2025  
**Fecha de análisis:** Julio 2026

---

## 1. Los dos modelos

### 1.1 Nuestro modelo M1 — Jiménez Martínez & Mercado Sánchez (Ometitlan)

Hamiltoniano por bono dirigido (i → j) a distancia Manhattan d=1:

```
H(sᵢ, sⱼ) = sᵢ + 2sⱼ − sᵢ·sⱼ² − sᵢ²·sⱼ
```

Parámetros: h₀=1, h₁=2, K=−1, L=−1. Mapeo de spins: Negro=−1, Vacío=0, Blanco=+1.

### 1.2 Modelo Alvarado — Atomic-Go

Bono por par adyacente (µ=0, wᵢⱼ=1):

```
H(xᵢ, xⱼ) = xᵢ · xⱼ
```

Referencia: Rojas-Domínguez, Barradas-Bautista & Alvarado,
*"Modeling the Game of Go by Ising Hamiltonian, Deep Belief Networks and Common Fate Graphs"*,
IEEE Access, 2019.

---

## 2. Tabla de interacción binaria (9 pares base)

Cada entrada es la energía de UN bono dirigido sᵢ→sⱼ evaluado de forma independiente.

### Nuestro modelo M1

|       | →● (−1) | →· (0) | →○ (+1) |
|-------|:-------:|:------:|:-------:|
| ●(−1) |   −1    |   −1   |   +1    |
| ·( 0) |   −2    |    0   |   +2    |
| ○(+1) |   −1    |   +1   |   +1    |

### Alvarado Atomic-Go

|       | →● (−1) | →· (0) | →○ (+1) |
|-------|:-------:|:------:|:-------:|
| ●(−1) |   +1    |    0   |   −1    |
| ·( 0) |    0    |    0   |    0    |
| ○(+1) |   −1    |    0   |   +1    |

### Diferencia (M1 − Alvarado)

|       | →● (−1) | →· (0) | →○ (+1) |
|-------|:-------:|:------:|:-------:|
| ●(−1) |   −2    |   −1   |   +2    |
| ·( 0) |   −2    |    0   |   +2    |
| ○(+1) |    0    |   +1   |    0    |

---

## 3. Diferencias estructurales entre modelos

### 3.1 Vacío activo vs. vacío invisible

- **M1**: H(0, xⱼ) = 2xⱼ ≠ 0 cuando xⱼ ≠ 0. Las celdas vacías adyacentes a piedras
  tienen energía propia. El vacío está "polarizado" por las piedras vecinas.
  Interpretación en Go: el espacio alrededor de un grupo forma parte de su influencia.
- **Alvarado**: 0·xⱼ = 0 siempre. El vacío es completamente invisible.
  Interpretación: solo el contacto directo piedra–piedra produce interacción.

### 3.2 Asimetría vs. simetría

- **M1**: 6 de los 9 pares son asimétricos, H(i→j) ≠ H(j→i).
  El bono ●→· vale −1 pero ·→● vale −2.
  El orden en que se nombra el par importa.
- **Alvarado**: xᵢ·xⱼ = xⱼ·xᵢ siempre. Todos los pares son simétricos.

### 3.3 Rango de valores

- **M1**: {−2, −1, 0, +1, +2} — 5 valores distintos.
- **Alvarado**: {−1, 0, +1} — 3 valores distintos.

### 3.4 Signo de la interacción mismo-color

- **M1**: ●●=−1, ○○=+1. Las negras se atraen entre sí; las blancas también (−1).
  Negro–Blanco se repele (+1).
- **Alvarado**: ●●=+1, ○○=+1. Mismo color se **repele**. ●○=−1 se **atrae**.
  Los signos están **invertidos** respecto a M1.

> Este es el desacuerdo cualitativo más importante: los dos modelos discrepan
> en el signo de la interacción entre piedras del mismo color.

---

## 4. Entropía de la tabla de interacción (9 pares como distribución)

Tratando los 9 pares como muestras equiprobables:

| Métrica | M1 | Alvarado |
|---------|:---:|:-------:|
| Valores distintos | 5 | 3 |
| S_Shannon (nats) | **1.465** | 0.995 |
| S_max = ln(k) (nats) | ln(5) = 1.609 | ln(3) = 1.099 |
| S / S_max | **0.91** | **0.91** |
| S_Boltzmann (T_eff) | 2.197 ≈ ln(9) | 2.197 ≈ ln(9) |
| T_eff de la tabla | ∞ | ∞ |

**Hallazgo**: Ambos modelos tienen la misma entropía relativa (S/Sₘₐₓ = 0.91),
pero M1 tiene mayor entropía absoluta por tener más valores posibles.

**Hallazgo**: La S_Boltzmann de ambos es ln(9) porque T_eff = ∞:
la media de los 9 valores es cero en ambos casos (las interacciones se compensan).

---

## 5. Entropía de Shannon por bono — 19 patrones de apertura

Entropía de Shannon calculada sobre todos los bonos dirigidos del tablero:
S = −Σ pᵢ ln pᵢ donde pᵢ = |Eᵢ| / Σ|Eⱼ|.

| ID  | Descripción | S_M1 | S_Alvarado | Δ |
|-----|-------------|-----:|----------:|--:|
| 1b  | 4-4 hoshi | 2.023 | 0.000 | +2.023 |
| 2b  | 3-4 komoku | 2.023 | 0.000 | +2.023 |
| 3b  | Approach bajo a 3-4 | 2.716 | 0.000 | +2.716 |
| 4b  | Invasión san-san | 2.716 | 0.000 | +2.716 |
| 5b  | Joseki san-san (gote) | 3.342 | 2.303 | +1.040 |
| 6b  | Extensión blanca | 3.525 | 2.485 | +1.040 |
| 7b  | Approach bajo a 4-4 | 2.716 | 0.000 | +2.716 |
| 8b  | Approach a cercado | 3.121 | 0.000 | +3.121 |
| 9b  | Joseki san-san variante | 3.406 | 2.079 | +1.327 |
| 10b | Salto doble komoku | 2.716 | 0.000 | +2.716 |
| 11b | Approach alto a komoku | 2.716 | 0.000 | +2.716 |
| 12b | Joseki san-san 6 jugadas | 3.578 | 2.303 | +1.275 |
| 13b | Approach 5ta línea | 2.716 | 0.000 | +2.716 |
| 14b | Joseki + extensión 3ra | 3.679 | 2.639 | +1.040 |
| 15b | Joseki hane blanco | 3.342 | 2.303 | +1.040 |
| 16b | Approach cercado (raro) | 3.121 | 0.000 | +3.121 |
| 17b | Tras hane blanco | 3.525 | 2.485 | +1.040 |
| 18b | Joseki poco frecuente | 3.119 | 2.079 | +1.040 |
| 19b | Continuación patrón 9b | 3.525 | 2.485 | +1.040 |

**Resumen:**
- M1 > Alvarado en **19/19 patrones** (brecha siempre positiva).
- Brecha media: **1.92 nats**.
- Alvarado da S=0 en patrones con solo 1-2 piedras y sin contacto entre ellas
  (todos sus bonos son cero → no hay distribución que medir).
- Correlación entre modelos: **r = 0.83** — los patrones complejos son complejos
  para los dos.

---

## 6. Entropía de Boltzmann y temperatura efectiva — 19 patrones

S_B = −Σ pᵢ ln pᵢ con pᵢ = e^(−Eᵢ/T_eff) / Z,
T_eff = σ²(E) / |⟨E⟩| calculada sobre bonos no nulos del mismo patrón.

| ID  | S_B M1 | S_B Alvarado | T_eff M1 | T_eff Alvarado |
|-----|-------:|-------------:|---------:|---------------:|
| 1b  | 1.410 | 5.781 | 0.17 | 0.00 |
| 5b  | 5.779 | 5.760 | 7.23 | 1.07 |
| 6b  | 5.774 | 5.778 | 4.06 | 2.67 |
| 14b | 5.767 | 5.780 | 2.93 | 6.86 |

Valores representativos; tabla completa en la consola de `viz_entropy_comparison.py`.

**Hallazgos:**
- **S_B ≈ ln(N) ≈ 5.78** para la mayoría de patrones (N = número de bonos del tablero).
  Esto ocurre porque T_eff es grande → distribución de Gibbs plana.
- **Excepción: patrón 1b** (una sola piedra). T_eff = 0.17, S_B = 1.41.
  Una sola piedra crea pocas interacciones concentradas → sistema "frío".
- **Correlación S_Shannon vs S_Boltzmann**: r = 0.72 para M1, r = −0.20 para Alvarado.
  Para M1 ambas entropías se mueven juntas. Para Alvarado, no.

---

## 7. Análisis sobre partida real (GIF: Gu Lingyi vs Tao Xinran, 164 jugadas)

### 7.1 Evolución de S_Shannon

| Momento | S_Shannon M1 | S_Shannon Alvarado |
|---------|:------------:|:-----------------:|
| Jugada 0 (tablero vacío) | ≈ 0 | ≈ 0 |
| Jugada 30 | 5.24 | 3.69 |
| Jugada 60 | 5.84 | 4.75 |
| Jugada 90 | 6.18 | 5.27 |
| Jugada 120 | 6.41 | 5.58 |
| Jugada 160 | 6.60 | 5.82 |

**Ambas curvas crecen monotónicamente.** La brecha ΔS = S_M1 − S_Alvarado se reduce
conforme avanza la partida: empieza en ~1.7 nats y termina en ~0.8 nats.
Los modelos **convergen** al llenarse el tablero porque la proporción de bonos
piedra–piedra (que ambos evalúan) crece relativa a los bonos vacío–piedra (que solo M1 evalúa).

### 7.2 S_Shannon no mide lo que parece

S_Shannon crece simplemente porque **hay más bonos activos** con cada jugada,
no porque la posición sea estratégicamente más compleja. Es un efecto de densidad.

### 7.3 Ausencia de enfriamiento termodinámico

**Hallazgo central:** Ni S_Shannon ni S_Boltzmann ni T_eff muestran el enfriamiento
que cabría esperar al final de la partida.

Razón: T_eff = σ²(E)/|⟨E⟩| → ∞ durante toda la partida porque los dos colores
producen interacciones de signos contrarios que se compensan → ⟨E⟩ ≈ 0.

Un sistema de Ising ferromagnético real se enfría cuando los espines se alinean
(un solo signo domina → |⟨E⟩| crece → T_eff baja). En Go esto no puede ocurrir:
la regla del juego garantiza la coexistencia de dos colores → ⟨E⟩ siempre cerca de cero.

---

## 8. Interpretación física comparada

| Aspecto | M1 | Alvarado |
|---------|:---|:---------|
| El vacío es | Campo polarizado por las piedras | Espacio neutro invisible |
| Influencia | Medida (el vacío adyacente lleva energía) | No medida |
| Atracción mismo color | Sí (●●= −1) | No (●●= +1, repulsión) |
| Asimetría | Sí: el origen y el destino importan | No |
| Qué ve el modelo | Influencia territorial + contacto | Solo contacto directo |

### Interpretación en términos de Go

- **M1** captura el concepto de *influencia*: las intersecciones vacías cercanas a un
  grupo quedan "cargadas" energéticamente. Esto es análogo a la presión que ejerce
  un grupo sobre el territorio circundante.

- **Alvarado** captura únicamente el *contacto directo* entre piedras. Una piedra aislada
  no ejerce ninguna influencia medible sobre el tablero vacío.

---

## 9. Límites del marco actual

1. **T_eff no captura el enfriamiento estratégico de Go.**
   La temperatura del juego en Go (valor del mayor movimiento disponible)
   decrece durante la partida, pero T_eff = σ²/|⟨E⟩| no lo refleja porque
   el denominador siempre es cercano a cero.

2. **S_Shannon crece mecánicamente con el número de jugadas.**
   Parte del crecimiento es simplemente más bonos activos, no más complejidad
   posicional. Para aislar la complejidad sería necesario normalizar por
   el número de bonos o medir entropía por unidad de bono activo.

3. **S_Boltzmann no distingue modelos al nivel de la tabla completa.**
   Ambos dan S_B ≈ ln(9) porque T_eff = ∞ (media cero). Solo en patrones
   con piedras aisladas (T_eff bajo) aparece diferenciación.

4. **El enfriamiento estratégico requiere una variable diferente:**
   entropía de la distribución de ownership (a quién pertenece cada intersección),
   que sí debería disminuir al establecerse el territorio.

---

## 10. Conclusiones

1. **Los modelos coinciden cualitativamente en complejidad** (r = 0.83 entre sus
   entropías de Shannon por patrón) pero discrepan en magnitud y en física.

2. **M1 siempre asigna mayor entropía que Alvarado** (19/19 patrones, brecha media
   1.92 nats) porque incluye las interacciones de las celdas vacías.

3. **El desacuerdo de mayor impacto físico** es el signo invertido de la interacción
   mismo-color: M1 considera que piedras del mismo color se atraen; Alvarado, que
   se repelen.

4. **El marco de Ising de dos colores no captura el enfriamiento termodinámico de Go.**
   La analogía es parcialmente válida (energía, entropía de distribución) pero falla
   en el enfriamiento porque la coexistencia obligatoria de dos colores mantiene
   ⟨E⟩ ≈ 0 permanentemente.

5. **M1 es físicamente más rico** al incluir el efecto de campo del vacío (influencia),
   pero comparte con Alvarado el límite termodinámico de no poder capturar
   el enfriamiento estratégico del juego.

---

## Archivos generados

| Archivo | Contenido |
|---------|-----------|
| `results/interaction_comparison.png` | 4 representaciones de la tabla de interacción |
| `results/bond_interaction_table.png` | Tabla de bonos dirigidos con inversas |
| `results/bond_interaction_graph.png` | Grafo de nodos con flechas coloreadas |
| `results/entropy_comparison.png` | Shannon + Boltzmann + T_eff, 19 patrones + dispersión |
| `results/bond_entropy_compare.png` | Barras de S_Shannon por los 19 patrones |
| `results/bond_distribution.png` | Distribución de bonos para patrones seleccionados |
| `results/energy_grid_M1/M2.png` | Grilla de mapas de energía por patrón |
| `results/dashboard_M1/M2.png` | Dashboard completo por modelo |
| `results/*_M1.gif` | Animación de partida con overlay de energía |
| `results/*_entropy_compare.gif` | Animación con S_Shannon, S_Boltzmann, T_eff en tiempo real |
