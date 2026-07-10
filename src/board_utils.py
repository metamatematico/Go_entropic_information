"""
board_utils.py
==============
Helpers para crear e intercambiar tableros numpy con el motor de Go.
"""

import numpy as np
from typing import Iterable, TYPE_CHECKING

if TYPE_CHECKING:
    from .go_game_engine import GoBoard


def empty_board(size: int) -> np.ndarray:
    """Crea un tablero numpy vacio del tamanio dado."""
    return np.full((size, size), '.', dtype='<U1')


def board_from_matrix(matrix: Iterable[Iterable[str]]) -> np.ndarray:
    """
    Construye un array numpy desde una matriz de 'B'/'W'/'.'.
    La matriz debe ser cuadrada.
    """
    arr = np.array(matrix, dtype='<U1')
    if arr.ndim != 2 or arr.shape[0] != arr.shape[1]:
        raise ValueError("La matriz debe ser cuadrada")
    valid = {'.', 'B', 'W'}
    if not np.isin(arr, list(valid)).all():
        raise ValueError("La matriz debe contener solo '.', 'B', 'W'")
    return arr


def board_to_numpy(board: 'GoBoard') -> np.ndarray:
    """Devuelve una copia numpy del tablero interno de un GoBoard."""
    return np.array(board.board, dtype='<U1')


def board_from_stones(size: int, stones: list) -> np.ndarray:
    """
    Crea un tablero numpy a partir de una lista de piedras.

    Args:
        size: Tamanio del tablero (ej. 9, 19)
        stones: Lista de tuplas ('B'|'W', row, col)
    """
    board = empty_board(size)
    for color, r, c in stones:
        if 0 <= r < size and 0 <= c < size:
            board[r, c] = color
    return board
