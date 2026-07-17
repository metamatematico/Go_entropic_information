"""
katago_engine.py
=================
Wrapper del motor de análisis de KataGo (protocolo JSON por stdin/stdout).

Uso
---
engine = KataGoEngine(katago_dir="tools/katago")
result = engine.analyze(moves=[("B", (3, 3)), ("W", (15, 15))],
                         analyze_turns=[2], max_visits=200)
# result[0]["rootInfo"]["scoreLead"], result[0]["ownership"], result[0]["moveInfos"]
engine.close()
"""

import json
import subprocess
from pathlib import Path
from typing import List, Tuple, Dict, Any, Optional

# Alfabeto GTP: 19 letras, sin la 'I'
_GTP_COLS = "ABCDEFGHJKLMNOPQRST"


def sgf_rc_to_gtp(row: int, col: int, board_size: int = 19) -> str:
    """Convierte (fila, columna) 0-indexado (fila 0 = arriba, SGF) a coordenada GTP.

    GTP numera filas desde abajo (fila 1 = borde inferior) y usa columnas
    A-T saltándose la 'I'.
    """
    gtp_col = _GTP_COLS[col]
    gtp_row = board_size - row
    return f"{gtp_col}{gtp_row}"


def gtp_to_rc(coord: str, board_size: int = 19) -> Tuple[int, int]:
    """Inversa de sgf_rc_to_gtp: coordenada GTP -> (fila, columna) 0-indexado."""
    col = _GTP_COLS.index(coord[0].upper())
    gtp_row = int(coord[1:])
    row = board_size - gtp_row
    return row, col


class KataGoEngine:
    """Lanza katago.exe en modo `analysis` y envía consultas JSON por stdin."""

    def __init__(self, katago_dir: str, model_file: str = "kata1-b15c192.txt.gz",
                 config_file: str = "analysis_example.cfg",
                 board_size: int = 19, rules: str = "japanese", komi: float = 6.5):
        self.dir = Path(katago_dir)
        self.board_size = board_size
        self.rules = rules
        self.komi = komi
        self._query_id = 0

        exe = self.dir / "katago.exe"
        if not exe.exists():
            raise FileNotFoundError(f"No se encontró katago.exe en {self.dir}")

        self.proc = subprocess.Popen(
            [str(exe), "analysis", "-model", model_file, "-config", config_file],
            stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
            text=True, bufsize=1, cwd=str(self.dir),
        )

    def analyze(self, moves: List[Tuple[str, Tuple[int, int]]],
                analyze_turns: List[int],
                max_visits: int = 300,
                include_ownership: bool = True) -> Dict[int, Dict[str, Any]]:
        """
        moves: lista de (color, (fila, columna)) en orden de juego, 0-indexado,
               fila 0 = arriba (convención SGF ya usada en el resto del proyecto).
        analyze_turns: índices de jugada (0 = posición inicial, k = después de
               la jugada k-ésima) donde se pide el análisis.
        Devuelve dict turno -> respuesta JSON de KataGo.
        """
        self._query_id += 1
        qid = f"q{self._query_id}"
        gtp_moves = [[color, sgf_rc_to_gtp(r, c, self.board_size)]
                     for color, (r, c) in moves]

        query = {
            "id": qid,
            "moves": gtp_moves,
            "rules": self.rules,
            "komi": self.komi,
            "boardXSize": self.board_size,
            "boardYSize": self.board_size,
            "analyzeTurns": analyze_turns,
            "maxVisits": max_visits,
            "includeOwnership": include_ownership,
        }
        self.proc.stdin.write(json.dumps(query) + "\n")
        self.proc.stdin.flush()

        results = {}
        for _ in analyze_turns:
            line = self.proc.stdout.readline()
            if not line:
                err = self.proc.stderr.read()
                raise RuntimeError(f"KataGo cerró stdout inesperadamente. stderr:\n{err}")
            data = json.loads(line)
            results[data["turnNumber"]] = data
        return results

    def close(self):
        try:
            self.proc.stdin.close()
        except Exception:
            pass
        self.proc.terminate()
        try:
            self.proc.wait(timeout=5)
        except Exception:
            self.proc.kill()

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        self.close()
