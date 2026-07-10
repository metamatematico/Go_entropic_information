"""
go_game_engine.py
=================
Motor del juego de Go con reglas completas:
capturas, Ko, suicidio, historial y replay de partidas SGF.
"""

import numpy as np
from typing import Tuple, List, Dict, Set, Optional, Union
from dataclasses import dataclass
from copy import deepcopy


# ============================================================================
# ESTRUCTURAS DE DATOS
# ============================================================================

@dataclass
class MoveInfo:
    """Informacion sobre un movimiento."""
    color: str
    position: Tuple[int, int]
    captured_stones: int = 0
    is_legal: bool = True
    reason: str = ""
    comment: str = ""


@dataclass
class GameInfo:
    """Metadatos de la partida."""
    black_player: str = ""
    white_player: str = ""
    black_rank: str = ""
    white_rank: str = ""
    date: str = ""
    komi: float = 6.5
    board_size: int = 19
    result: str = ""
    winner: Optional[str] = None


# ============================================================================
# MOTOR DE JUEGO
# ============================================================================

class GoBoard:
    """
    Motor del juego de Go con reglas completas.

    Atributos:
        size        - Tamanio del tablero (19, 13, 9...)
        board       - Array numpy con '.' vacio, 'B' negro, 'W' blanco
        captures    - Piedras capturadas por cada jugador
        move_history  - Historial de movimientos
        board_history - Historial de estados (para Ko)
    """

    def __init__(self, size: int = 19,
                 initial_matrix: Optional[Union[np.ndarray, List[List[str]]]] = None):
        if size < 2:
            raise ValueError("El tamanio del tablero debe ser al menos 2")
        self.size = size
        self.board = np.full((size, size), '.', dtype='<U1')
        self.captures: Dict[str, int] = {'B': 0, 'W': 0}
        self.move_history: List[MoveInfo] = []
        self.board_history: List[np.ndarray] = []
        self._group_cache: Dict[Tuple[int, int], Set[Tuple[int, int]]] = {}
        self._liberty_cache: Dict[Tuple[int, int], int] = {}

        if initial_matrix is not None:
            arr = np.array(initial_matrix, dtype='<U1')
            if arr.ndim != 2 or arr.shape[0] != arr.shape[1]:
                raise ValueError("initial_matrix debe ser cuadrada")
            if arr.shape[0] != size:
                raise ValueError(f"initial_matrix de tamanio {arr.shape[0]} no coincide con size={size}")
            if not np.isin(arr, ['.', 'B', 'W']).all():
                raise ValueError("initial_matrix debe contener solo '.', 'B', 'W'")
            self.board[:, :] = arr

    # -------------------------------------------------------------------------
    # COLOCAR PIEDRA
    # -------------------------------------------------------------------------

    def place_stone(self, color: str, position: Tuple[int, int],
                    validate: bool = True) -> Tuple[bool, str]:
        """
        Coloca una piedra con validacion completa (Ko, suicidio, limites).

        Returns:
            (exito, mensaje)
        """
        if color not in ('B', 'W'):
            return False, "Color invalido. Usa 'B' o 'W'"
        row, col = position
        if not (0 <= row < self.size and 0 <= col < self.size):
            return False, f"Posicion fuera del tablero: {position}"
        if self.board[row, col] != '.':
            return False, f"Posicion {position} ya esta ocupada"

        previous_board = self.board.copy()
        self.board[row, col] = color
        captured = self._perform_captures(row, col, color)

        if validate:
            is_legal, reason = self._validate_move(row, col, color, previous_board)
            if not is_legal:
                self.board = previous_board
                return False, reason

        self.captures[color] += captured
        self.board_history.append(previous_board)
        self.move_history.append(MoveInfo(color=color, position=position,
                                          captured_stones=captured, is_legal=True))
        self._invalidate_cache()
        return True, f"Piedra colocada. {captured} captura(s)."

    def _perform_captures(self, row: int, col: int, color: str) -> int:
        opponent = 'W' if color == 'B' else 'B'
        total = 0
        for nx, ny in self._get_neighbors(row, col):
            if self.board[nx, ny] == opponent and not self._has_liberties(nx, ny):
                total += self._remove_group(nx, ny)
        return total

    def _validate_move(self, row: int, col: int, color: str,
                        previous_board: np.ndarray) -> Tuple[bool, str]:
        if not self._has_liberties(row, col):
            return False, "Movimiento suicida (sin libertades)"
        if self.board_history and np.array_equal(self.board, self.board_history[-1]):
            return False, "Violacion de Ko"
        return True, "Movimiento legal"

    # -------------------------------------------------------------------------
    # GRUPOS Y LIBERTADES
    # -------------------------------------------------------------------------

    def _get_neighbors(self, row: int, col: int) -> List[Tuple[int, int]]:
        result = []
        for dr, dc in ((-1, 0), (1, 0), (0, -1), (0, 1)):
            nr, nc = row + dr, col + dc
            if 0 <= nr < self.size and 0 <= nc < self.size:
                result.append((nr, nc))
        return result

    def _get_group(self, row: int, col: int) -> Set[Tuple[int, int]]:
        if (row, col) in self._group_cache:
            return self._group_cache[(row, col)]
        color = self.board[row, col]
        if color == '.':
            return set()
        group: Set[Tuple[int, int]] = set()
        stack = [(row, col)]
        while stack:
            r, c = stack.pop()
            if (r, c) in group:
                continue
            if self.board[r, c] == color:
                group.add((r, c))
                stack.extend(self._get_neighbors(r, c))
        for pos in group:
            self._group_cache[pos] = group
        return group

    def _has_liberties(self, row: int, col: int) -> bool:
        for gr, gc in self._get_group(row, col):
            for nr, nc in self._get_neighbors(gr, gc):
                if self.board[nr, nc] == '.':
                    return True
        return False

    def count_liberties(self, row: int, col: int) -> int:
        liberties: Set[Tuple[int, int]] = set()
        for gr, gc in self._get_group(row, col):
            for nr, nc in self._get_neighbors(gr, gc):
                if self.board[nr, nc] == '.':
                    liberties.add((nr, nc))
        return len(liberties)

    def _remove_group(self, row: int, col: int) -> int:
        group = self._get_group(row, col)
        for gr, gc in group:
            self.board[gr, gc] = '.'
        return len(group)

    # -------------------------------------------------------------------------
    # HISTORIAL Y REPLAY
    # -------------------------------------------------------------------------

    def undo_move(self) -> bool:
        if not self.board_history:
            return False
        self.board = self.board_history.pop()
        last = self.move_history.pop()
        self.captures[last.color] -= last.captured_stones
        self._invalidate_cache()
        return True

    def replay_moves(self, moves: List[Dict]) -> List[MoveInfo]:
        """Reproduce una lista de movimientos en formato SGF."""
        results = []
        for move in moves:
            color = move.get('color', '')
            coords = move.get('coords', '')
            if not coords or move.get('pass', False):
                continue
            position = _sgf_to_coords(coords)
            if position is None:
                continue
            success, msg = self.place_stone(color, position)
            if success:
                self.move_history[-1].comment = move.get('comment', '')
            results.append(
                self.move_history[-1] if success
                else MoveInfo(color, position, is_legal=False, reason=msg)
            )
        return results

    def get_captures(self) -> Dict[str, int]:
        return self.captures.copy()

    def to_numpy(self) -> np.ndarray:
        return self.board.copy()

    def _invalidate_cache(self):
        self._group_cache.clear()
        self._liberty_cache.clear()

    def __str__(self) -> str:
        lines = []
        letters = [c for c in 'ABCDEFGHJKLMNOPQRST'][:self.size]
        header = '   ' + ' '.join(letters)
        lines.append(header)
        for r in range(self.size):
            row_num = str(self.size - r).rjust(2)
            row_str = ' '.join(
                '●' if self.board[r, c] == 'B' else
                '○' if self.board[r, c] == 'W' else '+'
                for c in range(self.size)
            )
            lines.append(f"{row_num} {row_str}")
        return '\n'.join(lines)

    def __repr__(self) -> str:
        return f"GoBoard(size={self.size}, moves={len(self.move_history)})"


# ============================================================================
# PARSER SGF
# ============================================================================

def _sgf_to_coords(sgf_coords: str) -> Optional[Tuple[int, int]]:
    """Convierte coordenadas SGF ('pd', 'aa', ...) a (fila, columna) 0-indexed."""
    if not sgf_coords or len(sgf_coords) != 2:
        return None
    col = ord(sgf_coords[0]) - ord('a')
    row = ord(sgf_coords[1]) - ord('a')
    if col < 0 or row < 0:
        return None
    return (row, col)


class SGFParser:
    """
    Parser minimo para archivos SGF (Smart Game Format).
    Extrae movimientos y metadatos sin dependencias externas.
    """

    @staticmethod
    def parse_file(file_path: str) -> Tuple[List[Dict], GameInfo]:
        """
        Parsea un archivo SGF.

        Returns:
            (moves, GameInfo)
            moves: lista de {'color', 'coords', 'pass', 'comment'}
        """
        with open(file_path, 'r', encoding='utf-8', errors='replace') as f:
            content = f.read()

        props = SGFParser._parse_root_props(content)
        moves = SGFParser._parse_moves(content)

        winner = None
        result = props.get('RE', '')
        if result.startswith('B'):
            winner = 'B'
        elif result.startswith('W'):
            winner = 'W'

        gi = GameInfo(
            black_player=props.get('PB', ''),
            white_player=props.get('PW', ''),
            black_rank=props.get('BR', ''),
            white_rank=props.get('WR', ''),
            date=props.get('DT', ''),
            komi=float(props.get('KM', 6.5) or 6.5),
            board_size=int(props.get('SZ', 19) or 19),
            result=result,
            winner=winner,
        )
        return moves, gi

    @staticmethod
    def _parse_root_props(content: str) -> Dict[str, str]:
        """Extrae propiedades del nodo raiz (antes del primer movimiento B/W)."""
        import re
        props: Dict[str, str] = {}
        # Busca KEY[value] en los primeros 2000 chars
        header = content[:2000]
        for m in re.finditer(r'([A-Z]{1,3})\[([^\]]*)\]', header):
            key, val = m.group(1), m.group(2)
            if key not in ('B', 'W') and key not in props:
                props[key] = val
        return props

    @staticmethod
    def _parse_moves(content: str) -> List[Dict]:
        """Extrae secuencia de movimientos del SGF."""
        import re
        moves = []
        # Busca ;B[..] y ;W[..] con comentario opcional C[..]
        pattern = re.compile(r';([BW])\[([a-z]{0,2})\](?:[^;]*?C\[([^\]]*)\])?', re.DOTALL)
        for m in pattern.finditer(content):
            color = m.group(1)
            coords = m.group(2)
            comment = m.group(3) or ''
            moves.append({
                'color': color,
                'coords': coords,
                'pass': (len(coords) == 0),
                'comment': comment,
            })
        return moves
