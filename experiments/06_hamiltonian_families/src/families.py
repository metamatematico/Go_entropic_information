"""
families.py
===========
Generación de familias paramétricas de Hamiltonianos polinómicos para Go.

Plantillas soportadas
---------------------
cubic_mixed  : a1*x + a2*y + b11*x² + b12*xy + b22*y² + c112*x²y + c122*xy²
quadratic    : a1*x + a2*y + b11*x² + b12*xy + b22*y²
sparse_cubic : subconjunto aleatorio de monomios cúbicos
odd_cubic    : H(-x,-y)=-H(x,y)  →  a1*x + a2*y + c112*x²y + c122*xy²
h_m1         : H_M1 = x + 2y - xy² - x²y  (referencia Mercado & Jiménez)
"""

import numpy as np
import sympy as sp
from typing import Dict, List, Tuple

# Variables simbólicas canónicas
_x, _y = sp.symbols('x y', real=True)

# ── Templates ──────────────────────────────────────────────────────────────────
TEMPLATES = {
    "cubic_mixed": [_x, _y, _x**2, _x*_y, _y**2, _x**2*_y, _x*_y**2],
    "quadratic":   [_x, _y, _x**2, _x*_y, _y**2],
    "sparse_cubic":[_x, _y, _x**2*_y, _x*_y**2],
    "odd_cubic":   [_x, _y, _x**2*_y, _x*_y**2],   # paridad forzada
    "h_m1":        [_x, _y, _x**2*_y, _x*_y**2],   # coeficientes fijos
}

COEF_NAMES = {
    "cubic_mixed": ["a1","a2","b11","b12","b22","c112","c122"],
    "quadratic":   ["a1","a2","b11","b12","b22"],
    "sparse_cubic":["a1","a2","c112","c122"],
    "odd_cubic":   ["a1","a2","c112","c122"],
    "h_m1":        ["a1","a2","c112","c122"],
}

COEF_RANGES = {
    "cubic_mixed": [(-3,3),(-3,3),(-3,3),(-3,3),(-3,3),(-1,1),(-1,1)],
    "quadratic":   [(-3,3),(-3,3),(-3,3),(-3,3),(-3,3)],
    "sparse_cubic":[(-3,3),(-3,3),(-1,1),(-1,1)],
    "odd_cubic":   [(-3,3),(-3,3),(-1,1),(-1,1)],
    "h_m1":        None,
}

H_M1_COEFS = {"a1": 1.0, "a2": 2.0, "c112": -1.0, "c122": -1.0}


class Hamiltonian:
    """Un Hamiltoniano polinómico evaluable en ℝ² con metadatos."""

    def __init__(self, template: str, coefs: Dict[str, float]):
        self.template = template
        self.coefs    = coefs
        monomials     = TEMPLATES[template]
        names         = COEF_NAMES[template]
        # Expresión simbólica
        self.expr = sum(coefs[n] * m for n, m in zip(names, monomials))
        self.expr = sp.expand(self.expr)
        # Función numérica
        self._fn = sp.lambdify((_x, _y), self.expr, "numpy")

    def __call__(self, x, y):
        return self._fn(x, y)

    def __repr__(self):
        return f"H({self.template}) = {self.expr}"

    @property
    def coef_vector(self) -> np.ndarray:
        return np.array(list(self.coefs.values()), dtype=float)

    def to_dict(self) -> dict:
        return {"template": self.template, "coefficients": dict(self.coefs),
                "expression": str(self.expr)}


# ── Sampling ───────────────────────────────────────────────────────────────────

def _sample_coefs(template: str, rng: np.random.Generator,
                  cfg: dict) -> Dict[str, float]:
    """Muestrea coeficientes para una plantilla dada."""
    if template == "h_m1":
        return dict(H_M1_COEFS)

    names  = COEF_NAMES[template]
    ranges = COEF_RANGES[template]
    coefs  = {}
    for name, (lo, hi) in zip(names, ranges):
        coefs[name] = float(rng.uniform(lo, hi))

    # Paridad forzada en odd_cubic: los cuadráticos ya no están
    # (la plantilla solo tiene monomios impares, no hay que hacer nada extra)
    return coefs


def generate_random(template: str, n: int, cfg: dict,
                    seed: int = 42) -> List[Hamiltonian]:
    """Genera n Hamiltonianos aleatorios de la plantilla dada."""
    rng  = np.random.default_rng(seed)
    hams = []
    for _ in range(n):
        coefs = _sample_coefs(template, rng, cfg)
        try:
            h = Hamiltonian(template, coefs)
            hams.append(h)
        except Exception:
            continue
    return hams


def generate_grid(template: str, steps: int, cfg: dict) -> List[Hamiltonian]:
    """Genera una cuadrícula de Hamiltonianos variando los primeros dos coeficientes."""
    names  = COEF_NAMES[template]
    ranges = COEF_RANGES[template]
    if template == "h_m1":
        return [Hamiltonian("h_m1", H_M1_COEFS)]

    base_coefs = {n: (lo+hi)/2 for n, (lo, hi) in zip(names, ranges)}
    hams = []
    lo0, hi0 = ranges[0]
    lo1, hi1 = ranges[1]
    for v0 in np.linspace(lo0, hi0, steps):
        for v1 in np.linspace(lo1, hi1, steps):
            c = dict(base_coefs)
            c[names[0]] = float(v0)
            c[names[1]] = float(v1)
            hams.append(Hamiltonian(template, c))
    return hams


def reference_hamiltonians() -> List[Hamiltonian]:
    """Devuelve los Hamiltonianos de referencia del proyecto."""
    h_m1 = Hamiltonian("h_m1", H_M1_COEFS)
    # Alvarado: H = xy  (grado 2, genus 0)
    h_al = Hamiltonian("quadratic", {"a1":0,"a2":0,"b11":0,"b12":1,"b22":0})
    return [h_m1, h_al]
