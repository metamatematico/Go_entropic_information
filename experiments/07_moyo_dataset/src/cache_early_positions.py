"""
cache_early_positions.py
=========================
Analogo a cache_positions.py pero para jugadas TEMPRANAS (3%-15% de
la partida, justo el rango que sample_move_numbers() excluye a
propósito) — cubre dos categorías nuevas:

  - fuseki: mismo mecanismo de detect_moyos/filter_moyos/filter_territory
    de siempre (ownership-based, todo el tablero), solo que en este
    momento temprano en vez del rango medio ya usado.
  - joseki: regiones fijas de esquina (early_regions.joseki_regions),
    independientes de ownership.

Reutiliza directamente las funciones de cache_positions.py (misma
KataGoEngine, mismos agregados de incertidumbre/moveInfos) para no
duplicar lógica ya verificada.
"""

import sys
import pickle
import time
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
PROJDIR = HERE.parent.parent.parent

sys.path.insert(0, str(PROJDIR / "src"))
sys.path.insert(0, str(HERE))

from katago_engine import KataGoEngine                          # noqa: E402
from moyo_detector import detect_moyos, filter_moyos            # noqa: E402
from build_dataset import parse_sgf_moves, build_board          # noqa: E402
from early_regions import sample_early_move_numbers, joseki_regions  # noqa: E402
from cache_positions import (filter_territory, _region_entries,      # noqa: E402
                              top_moves_rc)


def cache_game_early(sgf_path: Path, engine: KataGoEngine, n_samples: int = 4,
                      max_visits: int = 600, board_size: int = 19) -> list:
    moves = parse_sgf_moves(sgf_path)
    n_total_moves = len(moves)
    if n_total_moves < 30:
        return []

    sample_points = sample_early_move_numbers(n_total_moves, n_samples)
    if not sample_points:
        return []

    results = engine.analyze(moves, analyze_turns=sample_points, max_visits=max_visits,
                              include_ownership_stdev=True, include_policy=True)

    entries = []
    for n_moves in sample_points:
        if n_moves not in results:
            continue
        res = results[n_moves]
        board = build_board(moves, n_moves)
        ownership = res["ownership"]
        root = res["rootInfo"]
        score_lead = root["scoreLead"]
        score_stdev = root.get("scoreStdev")
        winrate = root.get("winrate")

        ownership_stdev_grid = np.array(res["ownershipStdev"], dtype=float).reshape(board_size, board_size)
        policy_grid = np.array(res["policy"][:board_size * board_size], dtype=float).reshape(board_size, board_size)
        policy_pass = float(res["policy"][board_size * board_size])
        top_moves = top_moves_rc(res.get("moveInfos", []), board_size)

        # fuseki: mismo detect_moyos/filter_moyos/filter_territory de siempre
        regions = detect_moyos(board, ownership)
        moyos = filter_moyos(regions)
        territory = filter_territory(regions)

        # joseki: regiones fijas de esquina, independientes de ownership
        joseki = joseki_regions(board, ownership, board_size)

        if not moyos and not territory and not joseki:
            continue

        moyo_entries = _region_entries(moyos, board, n_moves, ownership_stdev_grid,
                                        policy_grid, top_moves, board_size)
        territory_entries = _region_entries(territory, board, n_moves, ownership_stdev_grid,
                                             policy_grid, top_moves, board_size)
        joseki_entries = _region_entries(joseki, board, n_moves, ownership_stdev_grid,
                                          policy_grid, top_moves, board_size)
        for je, jr in zip(joseki_entries, joseki):
            je["corner"] = jr["corner"]

        entries.append({
            "game": sgf_path.name,
            "move": n_moves,
            "n_total_moves": n_total_moves,
            "phase_frac": n_moves / n_total_moves,
            "score_lead": score_lead,
            "score_stdev": score_stdev,
            "winrate": winrate,
            "policy_pass": policy_pass,
            "board": board,
            "moyos": moyo_entries,          # fuseki, tipo moyo
            "territory": territory_entries,  # fuseki, tipo territorio
            "joseki": joseki_entries,
        })
    return entries


def main(n_games: int = 20, n_samples_per_game: int = 4,
         out_name: str = "cache_early", max_visits: int = 600):
    sgf_dir = PROJDIR / "data" / "sgf_partidas"
    sgf_files = sorted(sgf_dir.glob("*.sgf"))[:n_games]

    engine = KataGoEngine(katago_dir=str(PROJDIR / "tools" / "katago"))
    all_entries = []
    t0 = time.time()
    try:
        for i, sgf_path in enumerate(sgf_files):
            try:
                entries = cache_game_early(sgf_path, engine, n_samples_per_game, max_visits=max_visits)
                all_entries.extend(entries)
                n_moyos = sum(len(e["moyos"]) for e in entries)
                n_territory = sum(len(e["territory"]) for e in entries)
                n_joseki = sum(len(e["joseki"]) for e in entries)
                print(f"[{i+1}/{len(sgf_files)}] {sgf_path.name}: "
                      f"{len(entries)} posiciones, {n_moyos} moyos, {n_territory} territorios, "
                      f"{n_joseki} joseki ({time.time()-t0:.0f}s transcurridos)")
            except Exception as e:
                print(f"[{i+1}/{len(sgf_files)}] {sgf_path.name}: ERROR {e}")
    finally:
        engine.close()

    out_dir = HERE.parent / "output"
    out_dir.mkdir(exist_ok=True)
    out_path = out_dir / f"{out_name}.pkl"
    with open(out_path, "wb") as f:
        pickle.dump(all_entries, f)

    n_moyos_total = sum(len(e["moyos"]) for e in all_entries)
    n_territory_total = sum(len(e["territory"]) for e in all_entries)
    n_joseki_total = sum(len(e["joseki"]) for e in all_entries)
    print(f"\nCache final: {len(all_entries)} posiciones, {n_moyos_total} moyos (fuseki), "
          f"{n_territory_total} territorios (fuseki), {n_joseki_total} joseki, "
          f"de {len(sgf_files)} partidas")
    print(f"Guardado en: {out_path}")
    return all_entries


if __name__ == "__main__":
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--n_games", type=int, default=20)
    ap.add_argument("--n_samples", type=int, default=4)
    ap.add_argument("--out_name", type=str, default="cache_early")
    ap.add_argument("--max_visits", type=int, default=600)
    args = ap.parse_args()
    main(n_games=args.n_games, n_samples_per_game=args.n_samples,
         out_name=args.out_name, max_visits=args.max_visits)
