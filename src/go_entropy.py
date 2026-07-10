"""
go_entropy.py
=============
Calculo de entropia y temperatura efectiva para posiciones de Go
a partir del mapa de energia del modelo de Ising clasico.

Relaciones fisicas utilizadas:
    - Energia local: H_i = Hamiltoniano de Ising en la celda i
    - Temperatura efectiva: T_eff = sigma^2(E) / |mean(E)|
      (analogia con fluctuacion-disipacion: C_v = beta^2 * <(deltaH)^2>)
    - Entropia de Shannon: S = -sum( p_i * ln(p_i) )
      donde p_i = |E_i| / sum|E_j| (energia normalizada como probabilidad)
    - Entropia de Boltzmann: S_B = -sum( p_i * ln(p_i) )
      donde p_i = exp(-E_i/T) / Z  (distribucion de Gibbs)
"""

import numpy as np
from typing import Dict, Optional
from .go_ising_classical import ClassicalIsingModel, EnergyMapGenerator, IsingGoConfig


class GoEntropyAnalyzer:
    """
    Analiza entropia y temperatura efectiva de configuraciones de Go
    usando el mapa de energia del modelo de Ising clasico.

    Interpretacion fisica:
    - T_eff alto  -> energias dispersas -> posicion desordenada (apertura, tablero vacio)
    - T_eff bajo  -> energias concentradas -> posicion ordenada (grupos compactos)
    - S alto      -> distribucion de energia uniforme (patron sin estructura dominante)
    - S bajo      -> energia concentrada en pocas celdas (patron localizado)
    """

    def __init__(self, manhattan_distance: int = 1):
        self.manhattan_distance = manhattan_distance
        self.config = IsingGoConfig()
        self.model = ClassicalIsingModel(manhattan_distance=manhattan_distance)
        self.generator = EnergyMapGenerator(self.model)

    def energy_map(self, board: np.ndarray) -> np.ndarray:
        """Calcula el mapa de energia de Ising para el tablero dado."""
        return self.generator.generate_energy_map(board)

    def effective_temperature(self, emap: np.ndarray) -> float:
        """
        Temperatura efectiva de la configuracion.

        T_eff = sigma^2(E) / |mean(E)|

        Derivacion: en el ensamble canonico de Ising, la capacidad calorifica
        satisface C_v = beta^2 * <(deltaH)^2>, que implica
        T ~ sigma^2(E) / |<E>|  cuando C_v ~ constante.

        Resultado:
            0     -> tablero completamente ordenado o vacio
            inf   -> mean(E) ~ 0 (simetria perfecta entre pos/neg)
            valor tipico en juego ~ [0.5, 3.0]
        """
        flat = emap.flatten()
        nonzero = flat[np.abs(flat) > 1e-10]
        if len(nonzero) == 0:
            return 0.0
        mean_e = np.mean(nonzero)
        var_e = np.var(nonzero)
        if np.abs(mean_e) < 1e-10:
            return float('inf')
        return float(var_e / np.abs(mean_e))

    def shannon_entropy(self, emap: np.ndarray) -> float:
        """
        Entropia de Shannon de la distribucion de energia.

        p_i = |E_i| / sum_j |E_j|
        S   = -sum_i p_i * ln(p_i)   [en nats]

        Maximo: ln(N) cuando la energia esta distribuida uniformemente.
        Minimo: 0 cuando toda la energia esta en una sola celda.
        """
        flat = np.abs(emap.flatten())
        total = flat.sum()
        if total < 1e-12:
            return 0.0
        probs = flat / total
        probs = probs[probs > 1e-12]
        return float(-np.sum(probs * np.log(probs)))

    def boltzmann_entropy(self, emap: np.ndarray, T: float = 1.0) -> float:
        """
        Entropia de la distribucion de Gibbs a temperatura T.

        p_i = exp(-E_i / T) / Z   donde Z = sum_j exp(-E_j / T)
        S_B = -sum_i p_i * ln(p_i)

        Parametro T controla el balance entre estados:
        - T -> 0:  solo el estado de minima energia contribuye -> S_B ~ 0
        - T -> inf: todos los estados equiprobables -> S_B -> ln(N)
        """
        flat = emap.flatten()
        flat_shifted = flat - flat.min()   # estabilidad numerica
        T_safe = max(T, 1e-10)
        weights = np.exp(-flat_shifted / T_safe)
        Z = weights.sum()
        if Z < 1e-12:
            return 0.0
        probs = weights / Z
        probs = probs[probs > 1e-12]
        return float(-np.sum(probs * np.log(probs)))

    def analyze(self, board: np.ndarray, T: float = 1.0) -> Dict:
        """
        Analisis completo de un tablero.

        Args:
            board: Array 2D con 'B', 'W', '.'
            T: Temperatura para la entropia de Boltzmann (default 1.0)

        Returns:
            dict con:
                energy_map    - mapa de energia 2D
                total_energy  - suma de todas las energias
                mean_energy   - energia promedio por celda
                std_energy    - desviacion estandar de la energia
                T_eff         - temperatura efectiva
                S_shannon     - entropia de Shannon (nats)
                S_boltzmann   - entropia de Boltzmann a temperatura T (nats)
                stone_count   - conteo de piedras {'B', 'W', 'empty'}
        """
        emap = self.energy_map(board)
        return {
            'energy_map': emap,
            'total_energy': float(emap.sum()),
            'mean_energy': float(emap.mean()),
            'std_energy': float(emap.std()),
            'T_eff': self.effective_temperature(emap),
            'S_shannon': self.shannon_entropy(emap),
            'S_boltzmann': self.boltzmann_entropy(emap, T=T),
            'stone_count': {
                'B': int(np.sum(board == 'B')),
                'W': int(np.sum(board == 'W')),
                'empty': int(np.sum(board == '.')),
            },
        }


def board_from_stones(size: int, stones: list) -> np.ndarray:
    """
    Crea un tablero numpy a partir de una lista de piedras.

    Args:
        size: Tamanio del tablero (ej. 9, 19)
        stones: Lista de tuplas ('B'|'W', row, col)

    Returns:
        Array 2D de strings con 'B', 'W', '.'
    """
    board = np.full((size, size), '.', dtype='<U1')
    for color, r, c in stones:
        if 0 <= r < size and 0 <= c < size:
            board[r, c] = color
    return board
