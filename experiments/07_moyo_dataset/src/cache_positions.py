"""
cache_positions.py
===================
Corre KataGo UNA SOLA VEZ sobre N partidas y guarda, por posición
muestreada, todo lo que NO depende del Hamiltoniano: tablero, moyos
detectados (con su label_pct_black real) y features geométricas.

Esto separa la parte cara (KataGo + detección de moyo) de la parte
barata (relaxation_field, que sí depende de H) — necesario para poder
evaluar una función objetivo cientos de veces durante una optimización
sin volver a llamar a KataGo cada vez.

Salida: output/position_cache.pkl
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

from go_game_engine import GoBoard          # noqa: E402
from katago_engine import KataGoEngine, gtp_to_rc  # noqa: E402
from moyo_detector import detect_moyos, filter_moyos, MIN_MOYO_SIZE   # noqa: E402
from features import board_features          # noqa: E402
from build_dataset import parse_sgf_moves, sample_move_numbers, build_board  # noqa: E402

TOP_K_MOVES = 10


def region_uncertainty_features(ownership_stdev: np.ndarray, policy: np.ndarray,
                                 region_points: list, board_size: int = 19) -> dict:
    """Agregados de incertidumbre/política de KataGo sobre una región (moyo).
    ownership_stdev: grid (board_size,board_size). policy: grid (board_size,board_size)
    (ya sin el valor de pass)."""
    idx_r = [p[0] for p in region_points]
    idx_c = [p[1] for p in region_points]
    stdev_vals = ownership_stdev[idx_r, idx_c]
    policy_vals = policy[idx_r, idx_c]
    return {
        "ownership_stdev_mean": float(np.mean(stdev_vals)),
        "policy_mass": float(np.sum(policy_vals)),
    }


def top_moves_rc(move_infos: list, board_size: int = 19, top_k: int = TOP_K_MOVES) -> list:
    """Convierte las top-K jugadas candidatas (por 'order', 0=mejor) de
    moveInfos a coordenadas (fila,columna); descarta 'pass'."""
    cands = sorted(move_infos, key=lambda m: m.get("order", 999))[:top_k]
    pts = []
    for m in cands:
        mv = m.get("move")
        if not mv or mv.lower() == "pass":
            continue
        pts.append(gtp_to_rc(mv, board_size))
    return pts


def region_moveinfo_features(top_moves: list, region_points: list) -> dict:
    """Cuenta cuántas de las top-K jugadas candidatas caen dentro de la
    región (moyo) — señal de "frontera activa": si el motor todavía
    considera buenas jugadas ahí, el marco no está resuelto."""
    region_set = set(region_points)
    n_inside = sum(1 for p in top_moves if p in region_set)
    return {"n_top_moves_in_region": n_inside}


def filter_territory(regions: list, min_size: int = MIN_MOYO_SIZE) -> list:
    """Analogo a filter_moyos pero para regiones 'territory' (ownership
    asentado, >0.85) — categoria descartada hasta ahora, calculada gratis
    por el mismo detect_moyos()."""
    return [r for r in regions if r["kind"] == "territory" and r["size"] >= min_size]


def _region_entries(regions: list, board: np.ndarray, n_moves: int,
                     ownership_stdev_grid: np.ndarray, policy_grid: np.ndarray,
                     top_moves: list, board_size: int) -> list:
    out = []
    for region in regions:
        bf = board_features(board, region["points"], n_moves)
        unc = region_uncertainty_features(ownership_stdev_grid, policy_grid,
                                           region["points"], board_size)
        mv = region_moveinfo_features(top_moves, region["points"])
        out.append({
            "points": region["points"],
            "kind": region["kind"],
            "size": region["size"],
            "pct_black": region["pct_black"],
            "board_feats": bf,
            **unc,
            **mv,
        })
    return out


def cache_game(sgf_path: Path, engine: KataGoEngine, n_samples: int = 6,
               max_visits: int = 600, board_size: int = 19) -> list:
    moves = parse_sgf_moves(sgf_path)
    n_total_moves = len(moves)
    if n_total_moves < 30:
        return []

    sample_points = sample_move_numbers(len(moves), n_samples)
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

        regions = detect_moyos(board, ownership)
        moyos = filter_moyos(regions)
        territory = filter_territory(regions)
        if not moyos and not territory:
            continue

        moyo_entries = _region_entries(moyos, board, n_moves, ownership_stdev_grid,
                                        policy_grid, top_moves, board_size)
        territory_entries = _region_entries(territory, board, n_moves, ownership_stdev_grid,
                                             policy_grid, top_moves, board_size)

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
            "moyos": moyo_entries,
            "territory": territory_entries,
        })
    return entries


def main(n_games: int = 20, n_samples_per_game: int = 6,
         out_name: str = "position_cache", max_visits: int = 600):
    sgf_dir = PROJDIR / "data" / "sgf_partidas"
    sgf_files = sorted(sgf_dir.glob("*.sgf"))[:n_games]

    engine = KataGoEngine(katago_dir=str(PROJDIR / "tools" / "katago"))
    all_entries = []
    t0 = time.time()
    try:
        for i, sgf_path in enumerate(sgf_files):
            try:
                entries = cache_game(sgf_path, engine, n_samples_per_game, max_visits=max_visits)
                all_entries.extend(entries)
                n_moyos = sum(len(e["moyos"]) for e in entries)
                n_territory = sum(len(e["territory"]) for e in entries)
                print(f"[{i+1}/{len(sgf_files)}] {sgf_path.name}: "
                      f"{len(entries)} posiciones, {n_moyos} moyos, {n_territory} territorios "
                      f"({time.time()-t0:.0f}s transcurridos)")
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
    print(f"\nCache final: {len(all_entries)} posiciones, {n_moyos_total} moyos, "
          f"de {len(sgf_files)} partidas")
    print(f"Guardado en: {out_path}")
    return all_entries


if __name__ == "__main__":
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--n_games", type=int, default=20)
    ap.add_argument("--n_samples", type=int, default=6)
    ap.add_argument("--out_name", type=str, default="position_cache")
    ap.add_argument("--max_visits", type=int, default=600)
    args = ap.parse_args()
    main(n_games=args.n_games, n_samples_per_game=args.n_samples,
         out_name=args.out_name, max_visits=args.max_visits)
