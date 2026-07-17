"""
build_dataset.py
=================
Ensambla el dataset piloto "futures": para una muestra de partidas
reales, en varias posiciones de cada una, detecta moyos (ground truth
de KataGo) y extrae dos familias de features (tablero crudo + campo
de relajación de H) para dos Hamiltonianos de referencia — uno del
Frente 1 y uno del Frente 140 del diagrama de Hasse (experimento 06).

Salida: output/futures_pilot.parquet + output/manifest.json
"""

import sys
import re
import json
import time
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
PROJDIR = HERE.parent.parent.parent  # raíz del proyecto

sys.path.insert(0, str(PROJDIR / "src"))
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(PROJDIR / "experiments" / "06_hamiltonian_families" / "src"))

from go_game_engine import GoBoard          # noqa: E402
from families import Hamiltonian            # noqa: E402
from algebra import analyze                 # noqa: E402
from katago_engine import KataGoEngine       # noqa: E402
from moyo_detector import detect_moyos, filter_moyos   # noqa: E402
from features import (board_features, relaxation_field,   # noqa: E402
                      region_field_features, topology_features)

_MOVE_RE = re.compile(r'(?<![A-Z]);([BW])\[([a-s]{2})\]')

# ── Los dos Hamiltonianos piloto originales: Frente 1 vs Frente 140 ───────────
PILOT_HAMILTONIANS = {
    "H_0045_F1": ("frente1", Hamiltonian("cubic_mixed", {
        "a1": -0.7583, "a2": 0.1425, "b11": -2.3900, "b12": 2.0008,
        "b22": -2.6882, "c112": 0.8497, "c122": -0.8018,
    })),
    "H_0013_F140": ("tardios", Hamiltonian("cubic_mixed", {
        "a1": 1.5900, "a2": 0.8083, "b11": 0.3215, "b12": 0.3552,
        "b22": -1.1763, "c112": -0.9384, "c122": -0.1266,
    })),
}


def load_hamiltonians_from_json(path: Path) -> dict:
    """Carga {h_id: (grupo, Hamiltonian)} desde un JSON con estructura
    {"grupo": {"h_id": {"template":..., "coefficients":...}}}."""
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    out = {}
    for group, hams in data.items():
        for h_id, spec in hams.items():
            out[h_id] = (group, Hamiltonian(spec["template"], spec["coefficients"]))
    return out


def parse_sgf_moves(path: Path):
    text = path.read_text(encoding="utf-8", errors="ignore")
    moves = []
    for m in _MOVE_RE.finditer(text):
        p, coords = m.group(1), m.group(2)
        c, r = ord(coords[0]) - 97, ord(coords[1]) - 97
        if 0 <= c < 19 and 0 <= r < 19:
            moves.append((p, (r, c)))
    return moves


def sample_move_numbers(n_total_moves: int, n_samples: int = 6) -> list:
    """Jugadas equiespaciadas entre el 15% y el 90% de la partida
    (evita aperturas triviales y posiciones ya terminadas)."""
    if n_total_moves < 30:
        return []
    lo, hi = int(0.15 * n_total_moves), int(0.90 * n_total_moves)
    return sorted(set(np.linspace(lo, hi, n_samples).astype(int).tolist()))


def build_board(moves, n_moves: int) -> np.ndarray:
    board = GoBoard(size=19)
    for color, (r, c) in moves[:n_moves]:
        board.place_stone(color, (r, c), validate=False)
    numeric = np.zeros((19, 19))
    numeric[board.board == 'B'] = -1
    numeric[board.board == 'W'] = 1
    return numeric


def process_game(sgf_path: Path, engine: KataGoEngine, hamiltonians: dict,
                  topo_cache: dict, n_samples: int = 6, radius: int = 1) -> list:
    moves = parse_sgf_moves(sgf_path)
    if len(moves) < 30:
        return []

    sample_points = sample_move_numbers(len(moves), n_samples)
    if not sample_points:
        return []

    results = engine.analyze(moves, analyze_turns=sample_points, max_visits=250)

    rows = []
    for n_moves in sample_points:
        if n_moves not in results:
            continue
        board = build_board(moves, n_moves)
        ownership = results[n_moves]["ownership"]
        score_lead = results[n_moves]["rootInfo"]["scoreLead"]

        regions = detect_moyos(board, ownership)
        moyos = filter_moyos(regions)
        if not moyos:
            continue

        # Campo de relajacion de cada H, una vez por posicion (se reusa
        # para todos los moyos detectados en esa posicion)
        fields = {}
        for h_id, (group, h) in hamiltonians.items():
            fields[h_id] = relaxation_field(h, board, radius=radius, n_sweeps=8)

        for region in moyos:
            row = {
                "game": sgf_path.name,
                "move_number": n_moves,
                "score_lead": score_lead,
                "moyo_kind": region["kind"],
                "moyo_size": region["size"],
                "label_pct_black": region["pct_black"],
            }
            row.update(board_features(board, region["points"], n_moves))
            for h_id, (group, h) in hamiltonians.items():
                rf = region_field_features(fields[h_id], region["points"])
                row.update({f"{h_id}_{k}": v for k, v in rf.items()})
                row.update({f"{h_id}_{k}": v for k, v in topo_cache[h_id].items()})
                row[f"{h_id}_group"] = group
            rows.append(row)
    return rows


def main(n_games: int = 20, n_samples_per_game: int = 6,
         hamiltonians_json: str = None, out_name: str = "futures_pilot",
         radius: int = 1):
    sgf_dir = PROJDIR / "data" / "sgf_partidas"
    sgf_files = sorted(sgf_dir.glob("*.sgf"))[:n_games]

    if hamiltonians_json:
        hamiltonians = load_hamiltonians_from_json(Path(hamiltonians_json))
    else:
        hamiltonians = PILOT_HAMILTONIANS

    topo_cache = {h_id: topology_features(analyze(h))
                  for h_id, (group, h) in hamiltonians.items()}

    engine = KataGoEngine(katago_dir=str(PROJDIR / "tools" / "katago"))
    all_rows = []
    t0 = time.time()
    try:
        for i, sgf_path in enumerate(sgf_files):
            try:
                rows = process_game(sgf_path, engine, hamiltonians,
                                    topo_cache, n_samples_per_game, radius=radius)
                all_rows.extend(rows)
                print(f"[{i+1}/{len(sgf_files)}] {sgf_path.name}: "
                      f"{len(rows)} filas ({time.time()-t0:.0f}s transcurridos)")
            except Exception as e:
                print(f"[{i+1}/{len(sgf_files)}] {sgf_path.name}: ERROR {e}")
    finally:
        engine.close()

    df = pd.DataFrame(all_rows)
    out_dir = HERE.parent / "output"
    out_dir.mkdir(exist_ok=True)
    parquet_path = out_dir / f"{out_name}.parquet"
    df.to_parquet(parquet_path, index=False)

    manifest = {
        "n_games": len(sgf_files),
        "n_rows": len(df),
        "n_samples_per_game": n_samples_per_game,
        "hamiltonians": {h_id: {"group": group, **h.to_dict()}
                         for h_id, (group, h) in hamiltonians.items()},
        "moyo_thresholds": {"settled": 0.85, "neutral": 0.15,
                            "note": "sin estandar en la literatura; eleccion propia, documentada"},
        "katago_model": "kata1-b15c192-s1672170752-d466197061",
        "katago_max_visits": 250,
        "relaxation_n_sweeps": 8,
        "manhattan_radius": radius,
        "schema": list(df.columns) if len(df) else [],
    }
    (out_dir / f"{out_name}_manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"\nDataset final: {len(df)} filas de {len(sgf_files)} partidas, "
          f"{len(hamiltonians)} Hamiltonianos")
    print(f"Guardado en: {parquet_path}")
    return df


if __name__ == "__main__":
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--n_games", type=int, default=20)
    ap.add_argument("--n_samples", type=int, default=6)
    ap.add_argument("--hamiltonians_json", type=str, default=None)
    ap.add_argument("--out_name", type=str, default="futures_pilot")
    ap.add_argument("--radius", type=int, default=1)
    args = ap.parse_args()
    main(n_games=args.n_games, n_samples_per_game=args.n_samples,
         hamiltonians_json=args.hamiltonians_json, out_name=args.out_name,
         radius=args.radius)
