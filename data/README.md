# data/

## sgf_partidas/  (no incluida en el repo)

Contiene **4 000 archivos SGF** de partidas profesionales de Go descargados de
[gokifu.com](https://gokifu.com), correspondientes al **Campeonato chino femenino 2020**.

- Formato: SGF4 estándar, tablero 19×19 (`SZ[19]`)
- Jugadoras: profesionales chinas (Yu Zhiying, Cai Bihan, etc.)
- Partidas utilizables: **3 024** (976 descartadas por formato no estándar)

### Reproducir los datos procesados

```bash
# Extraer patrones de apertura de los primeros 30 movimientos
python scripts/pipeline/extract_sgf_patterns.py
# Genera: results/tables/sgf_openings.csv, sgf_patterns.csv
#         results/figures/sgf/sgf_heatmap.png, sgf_histogram.png, sgf_top_openings.png
```

Los archivos resultantes (`results/tables/sgf_*.csv`) sí están en el repo.
