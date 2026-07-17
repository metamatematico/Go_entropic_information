"""
dynamics.py
===========
Validación estratégica: mide si el Hamiltoniano predice jugadas
reales de partidas profesionales (SGF) mejor que una línea base aleatoria.

Metodología
-----------
Para cada jugada en las partidas SGF:
  1. Se coloca la piedra en un tablero simulado que aplica capturas reales
     (grupos rivales sin libertades se remueven; ver _place/_group_and_liberties).
  2. Se calculan los valores H(s0, s1) de los nuevos enlaces formados.
  3. Se define el "c objetivo" del Hamiltoniano como la media de sus
     valores críticos.
  4. Se compara si el valor H de la jugada real está más cerca del c objetivo
     que el valor H esperado bajo jugada aleatoria (muestra de vacíos).
  5. La significancia se evalúa con un test de permutación de signo
     (sign-flip) sobre las diferencias pareadas real-vs-aleatorio: NO es
     un bootstrap de la propia muestra, sino una verdadera hipótesis nula
     de "sin asociación" construida invirtiendo signos al azar.

Limitaciones conocidas (ver informe de validación)
---------------------------------------------------
  - H es un modelo puramente local (par de vecinos); Go depende de
    conectividad global (escaleras, vida/muerte, ko, territorio) que
    ningún Hamiltoniano de interacción por par puede capturar en principio.
  - No hay control por fuerza del jugador ni por fase de la partida.
  - c_target (media de valores críticos) es una elección de diseño no
    validada independientemente.
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


def _group_and_liberties(board: np.ndarray, r: int, c: int
                          ) -> Tuple[set, set]:
    """Grupo conectado (misma piedra) y sus libertades, vía flood-fill."""
    color = board[r, c]
    group: set = set()
    liberties: set = set()
    stack = [(r, c)]
    while stack:
        cr, cc = stack.pop()
        if (cr, cc) in group:
            continue
        group.add((cr, cc))
        for dr, dc in DIRS:
            nr, nc = cr + dr, cc + dc
            if 0 <= nr < 19 and 0 <= nc < 19:
                nv = board[nr, nc]
                if nv == 0:
                    liberties.add((nr, nc))
                elif nv == color and (nr, nc) not in group:
                    stack.append((nr, nc))
    return group, liberties


def _place(board: np.ndarray, r: int, c: int, player: int):
    """Coloca una piedra y aplica capturas según las reglas de Go
    (remueve grupos rivales adyacentes que se queden sin libertades)."""
    board[r, c] = player
    opponent = -player
    for dr, dc in DIRS:
        nr, nc = r + dr, c + dc
        if 0 <= nr < 19 and 0 <= nc < 19 and board[nr, nc] == opponent:
            group, liberties = _group_and_liberties(board, nr, nc)
            if not liberties:
                for gr, gc in group:
                    board[gr, gc] = 0


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

    # Test de permutación de signo (sign-flip): bajo H0 ("la jugada real
    # no está sistemáticamente más cerca de c_target que una aleatoria"),
    # el signo de cada delta_i es igual de probable + o -. Se generan
    # muchas asignaciones de signo al azar y se compara la mejora
    # observada contra esa distribución nula.
    n_perm = 2000
    rng2 = np.random.default_rng(0)
    perm_stats = np.empty(n_perm)
    for i in range(n_perm):
        signs = rng2.choice(np.array([-1.0, 1.0]), size=len(deltas))
        perm_stats[i] = -float(np.mean(deltas * signs))
    p_value = float(np.mean(perm_stats >= improvement))

    return {
        "n_games":    len(sgf_files),
        "n_moves":    len(deltas),
        "improvement": improvement,
        "p_value":    p_value,
        "c_target":   c_tgt,
    }
