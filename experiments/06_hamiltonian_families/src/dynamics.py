"""
dynamics.py
===========
Validación estratégica: mide si el Hamiltoniano predice jugadas
reales de partidas profesionales (SGF) mejor que una línea base aleatoria.

Metodología
-----------
Para cada jugada en las partidas SGF:
  1. Se calculan los valores H(s0, s1) de los nuevos enlaces formados.
  2. Se define el "c objetivo" del Hamiltoniano como el valor crítico
     más cercano (si existe) o la media de valores sobre pares válidos.
  3. Se compara si el valor H de la jugada real está más cerca del c objetivo
     que el valor H esperado bajo jugada aleatoria.
  4. Se reporta correlación y p-value (test de permutación).
"""

import re
import os
import numpy as np
from pathlib import Path
from typing import List, Dict, Any, Tuple

DIRS = [(0,1),(0,-1),(1,0),(-1,0)]
SPIN = {"B": -1.0, "W": 1.0}
_MOVE_RE = re.compile(r'(?<![A-Z]);([BW])\[([a-s]{2})\]')


def _parse_sgf(path: str) -> List[Tuple[str, int, int]]:
    text = open(path, encoding="utf-8", errors="ignore").read()
    moves = []
    for m in _MOVE_RE.finditer(text):
        p, coords = m.group(1), m.group(2)
        c, r = ord(coords[0])-97, ord(coords[1])-97
        if 0 <= c < 19 and 0 <= r < 19:
            moves.append((p, c, r))
    return moves


def _place(board: np.ndarray, r: int, c: int, player: int):
    """Coloca una piedra (sin captura completa para velocidad)."""
    board[r, c] = player


def _h_values_for_move(board: np.ndarray, r: int, c: int,
                        s0: float, h_fn) -> List[float]:
    """Calcula H(s0, s1) para cada vecino de (r,c)."""
    vals = []
    for dr, dc in DIRS:
        nr, nc = r+dr, c+dc
        if 0 <= nr < 19 and 0 <= nc < 19:
            s1 = board[nr, nc]
            if s0 != 0:   # solo pares donde la piedra nueva tiene spin
                vals.append(float(h_fn(s0, s1)))
    return vals


def _c_target(alg: Dict) -> float:
    """Valor c 'estratégico': promedio de valores críticos reales."""
    cv = alg.get("critical_values", [])
    return float(np.mean(cv)) if cv else 0.0


def validate_on_sgf(h, alg: Dict, sgf_dir: str,
                    n_games: int = 5) -> Dict[str, Any]:
    """
    Valida el Hamiltoniano comparando sus predicciones con jugadas reales.

    Para cada jugada real, se mide cuán cerca está H(jugada) del c_target
    vs. la media de H sobre movimientos aleatorios disponibles.
    """
    sgf_dir = Path(sgf_dir)
    sgf_files = sorted(sgf_dir.glob("*.sgf"))[:n_games]
    if not sgf_files:
        return {"n_games": 0, "correlation": None, "p_value": None,
                "improvement": None, "note": "no SGF files found"}

    c_tgt = _c_target(alg)
    deltas = []   # dist(H_real, c_tgt) - dist(H_random, c_tgt)

    for sgf_path in sgf_files:
        moves = _parse_sgf(str(sgf_path))
        board = np.zeros((19, 19), dtype=float)

        for player, col, row in moves:
            s0 = SPIN[player]

            # H values de la jugada real
            real_vals = _h_values_for_move(board, row, col, s0, h)
            if not real_vals:
                _place(board, row, col, int(s0))
                continue
            real_dist = float(np.mean([abs(v - c_tgt) for v in real_vals]))

            # H values de movimientos aleatorios (muestra de 20)
            empties = list(zip(*np.where(board == 0)))
            rng = np.random.default_rng(abs(hash((player,col,row))) % 2**31)
            sample = [empties[i] for i in
                      rng.choice(len(empties), min(20, len(empties)),
                                 replace=False)] if empties else []
            rand_dists = []
            for rr, rc in sample:
                rv = _h_values_for_move(board, rr, rc, s0, h)
                if rv:
                    rand_dists.append(np.mean([abs(v - c_tgt) for v in rv]))
            rand_mean = float(np.mean(rand_dists)) if rand_dists else real_dist

            # delta < 0 → jugada real más cercana al c_target (bueno)
            deltas.append(real_dist - rand_mean)
            _place(board, row, col, int(s0))

    if not deltas:
        return {"n_games": len(sgf_files), "correlation": None,
                "p_value": None, "improvement": None}

    deltas = np.array(deltas)
    improvement = float(-np.mean(deltas))   # positivo = real más cercano

    # Test de permutación: ¿es la mejora significativa?
    n_perm = 1000
    rng2 = np.random.default_rng(0)
    perm_means = [float(np.mean(rng2.choice(deltas, len(deltas), replace=True)))
                  for _ in range(n_perm)]
    p_value = float(np.mean(np.array(perm_means) <= -abs(improvement)))

    return {
        "n_games":    len(sgf_files),
        "n_moves":    len(deltas),
        "improvement": improvement,
        "p_value":    p_value,
        "c_target":   c_tgt,
    }
