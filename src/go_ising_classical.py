"""
go_ising_classical.py
=====================
Modelo de Ising CLASICO para el juego de Go.

Mapeo de spins:
    Negro (B)  -> s = -1
    Blanco (W) -> s = +1
    Vacio (.)  -> s =  0

Hamiltoniano clasico:
    H(s0, s1) = h0*s0 + h1*s1 + K*s0*s1^2 + L*s0^2*s1

Interaccion por distancia Manhattan con coeficientes 1/d^2.
"""

import numpy as np
from typing import Dict, Tuple, Optional


# ============================================================================
# CONFIGURACION
# ============================================================================

class IsingGoConfig:
    """Parametros fisicos del modelo de Ising para Go."""

    STONE_TO_SPIN: Dict[str, float] = {'B': -1.0, 'W': +1.0, '.': 0.0}
    SPIN_TO_STONE: Dict[float, str] = {-1: 'B', +1: 'W', 0: '.'}

    # Coeficientes de interaccion: peso segun distancia Manhattan (ley 1/d^2)
    INTERACTION_COEFFS: Dict[int, float] = {
        1: 1.0,
        2: 0.25,
        3: 0.111,
        4: 0.0625,
        5: 0.04,
        6: 0.0278,
        7: 0.0204,
        8: 0.0156,
        9: 0.0123,
    }

    @staticmethod
    def get_kernel_positions(manhattan_distance: int = 1) -> Dict[int, Tuple[int, int]]:
        """
        Posiciones del kernel en coordenadas relativas (dx, dy).
        Indice 0 = centro (0, 0).
        """
        positions: Dict[int, Tuple[int, int]] = {0: (0, 0)}
        idx = 1
        for d in range(1, manhattan_distance + 1):
            for dx in range(-d, d + 1):
                for dy in range(-d, d + 1):
                    if abs(dx) + abs(dy) == d:
                        positions[idx] = (dx, dy)
                        idx += 1
        return positions

    @staticmethod
    def manhattan_distance(pos1: Tuple[int, int], pos2: Tuple[int, int]) -> int:
        return abs(pos1[0] - pos2[0]) + abs(pos1[1] - pos2[1])

    @classmethod
    def get_kernel_info(cls, manhattan_distance: int) -> Dict:
        positions = cls.get_kernel_positions(manhattan_distance)
        n_sites = len(positions)
        coefficients: Dict[int, float] = {}
        for idx, pos in positions.items():
            if idx == 0:
                coefficients[idx] = 0.0
            else:
                dist = cls.manhattan_distance((0, 0), pos)
                coefficients[idx] = cls.INTERACTION_COEFFS.get(dist, 0.0)
        return {
            'positions': positions,
            'n_sites': n_sites,
            'coefficients': coefficients,
            'manhattan_distance': manhattan_distance,
        }


# ============================================================================
# MODELO CLASICO
# ============================================================================

class ClassicalIsingModel:
    """
    Modelo de Ising clasico para tableros de Go.

    Hamiltoniano de dos spins:
        H(s0, s1) = h0*s0 + h1*s1 + K*s0*s1^2 + L*s0^2*s1

    donde s_i in {-1, 0, +1} representan Negro, Vacio, Blanco.
    """

    def __init__(self, manhattan_distance: int = 1, config: Optional[IsingGoConfig] = None):
        self.config = config or IsingGoConfig()
        self.manhattan_distance = int(manhattan_distance)

        # Parametros del Hamiltoniano
        self.params: Dict[str, float] = {
            'h0': 1.0,
            'h1': 2.0,
            'K': -1.0,
            'L': -1.0,
        }

    @staticmethod
    def _hamiltonian(s0: float, s1: float, params: Dict[str, float]) -> float:
        """Hamiltoniano de interaccion entre dos spins."""
        h0, h1 = params['h0'], params['h1']
        K, L = params['K'], params['L']
        return h0 * s0 + h1 * s1 + K * s0 * (s1 ** 2) + L * (s0 ** 2) * s1

    def compute_energy(self, board: np.ndarray, x: int, y: int,
                       manhattan_distance: Optional[int] = None) -> float:
        """
        Energia clasica total en la posicion (x, y) del tablero.

        Suma las interacciones del centro con todos sus vecinos dentro
        del kernel Manhattan, ponderadas por 1/d^2.
        """
        dist = int(manhattan_distance) if manhattan_distance is not None else self.manhattan_distance
        positions = self.config.get_kernel_positions(dist)
        center_spin = self.config.STONE_TO_SPIN[board[x, y]]
        total = 0.0

        for idx, (dx, dy) in positions.items():
            if idx == 0:
                continue
            nx, ny = x + dx, y + dy
            if 0 <= nx < board.shape[0] and 0 <= ny < board.shape[1]:
                neighbor_spin = self.config.STONE_TO_SPIN[board[nx, ny]]
            else:
                neighbor_spin = 0.0  # fuera del tablero = vacio

            d = self.config.manhattan_distance((0, 0), (dx, dy))
            coeff = self.config.INTERACTION_COEFFS.get(d, 0.0)
            energy = self._hamiltonian(center_spin, neighbor_spin, self.params)
            total += coeff * energy

        return total


# ============================================================================
# GENERADOR DE MAPAS DE ENERGIA
# ============================================================================

class EnergyMapGenerator:
    """Genera mapas de energia para tableros de Go completos."""

    def __init__(self, model: ClassicalIsingModel):
        self.model = model

    def generate_energy_map(self, board: np.ndarray) -> np.ndarray:
        """
        Calcula la energia de Ising en cada interseccion del tablero.

        Returns:
            Array 2D de floats con la energia local en cada celda.
        """
        energy_map = np.zeros(board.shape, dtype=float)
        for i in range(board.shape[0]):
            for j in range(board.shape[1]):
                energy_map[i, j] = self.model.compute_energy(board, i, j)
        return energy_map

    def compute_statistics(self, board: np.ndarray, energy_map: np.ndarray) -> Dict:
        """Estadisticas de energia por color."""
        stats = {
            'black_energy': 0.0,
            'white_energy': 0.0,
            'empty_positive': 0.0,
            'empty_negative': 0.0,
            'total_energy': float(energy_map.sum()),
        }
        for i in range(board.shape[0]):
            for j in range(board.shape[1]):
                e = energy_map[i, j]
                stone = board[i, j]
                if stone == 'B':
                    stats['black_energy'] += e
                elif stone == 'W':
                    stats['white_energy'] += e
                else:
                    if e > 0:
                        stats['empty_positive'] += e
                    else:
                        stats['empty_negative'] += e
        return stats
