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
sym_cubic    : f(x,y)=f(y,x)  →  d*(x³+y³) + c*xy + e*(x²y+xy²)
               Base armónica: Δf=0 ∀(x,y); referencia: d=1, c=-3, e=-3
"""

import numpy as np
import sympy as sp
from typing import Dict, List, Tuple

# Variables simbólicas canónicas
_x, _y = sp.symbols('x y', real=True)

# ── Templates ──────────────────────────────────────────────────────────────────
# sym_cubic usa combinaciones simétricas como monomios base:
#   (x³+y³), xy, (x²y+xy²) → fuerza f(x,y)=f(y,x)
#   La referencia d=1,c=-3,e=-3 además es armónica: Δf=0
TEMPLATES = {
    "cubic_mixed": [_x, _y, _x**2, _x*_y, _y**2, _x**2*_y, _x*_y**2],
    "quadratic":   [_x, _y, _x**2, _x*_y, _y**2],
    "sparse_cubic":[_x, _y, _x**2*_y, _x*_y**2],
    "odd_cubic":   [_x, _y, _x**2*_y, _x*_y**2],   # paridad forzada
    "h_m1":        [_x, _y, _x**2*_y, _x*_y**2],   # coeficientes fijos
    "sym_cubic":   [_x**3 + _y**3, _x*_y, _x**2*_y + _x*_y**2],  # simétrico
}

COEF_NAMES = {
    "cubic_mixed": ["a1","a2","b11","b12","b22","c112","c122"],
    "quadratic":   ["a1","a2","b11","b12","b22"],
    "sparse_cubic":["a1","a2","c112","c122"],
    "odd_cubic":   ["a1","a2","c112","c122"],
    "h_m1":        ["a1","a2","c112","c122"],
    "sym_cubic":   ["d","c","e"],
}

COEF_RANGES = {
    "cubic_mixed": [(-3,3),(-3,3),(-3,3),(-3,3),(-3,3),(-1,1),(-1,1)],
    "quadratic":   [(-3,3),(-3,3),(-3,3),(-3,3),(-3,3)],
    "sparse_cubic":[(-3,3),(-3,3),(-1,1),(-1,1)],
    "odd_cubic":   [(-3,3),(-3,3),(-1,1),(-1,1)],
    "h_m1":        None,
    "sym_cubic":   [(-2,2),(-4,4),(-4,4)],
}

H_M1_COEFS         = {"a1": 1.0, "a2": 2.0, "c112": -1.0, "c122": -1.0}
# Referencia armónica: Δf=0, f(x,y)=f(y,x), 2 nodos A₁ en (0,0) y (-½,-½)
HARMONIC_CUBIC_COEFS = {"d": 1.0, "c": -3.0, "e": -3.0}


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
    if template == "sym_cubic":
        # Referencia fija si se pide explícitamente, aleatorio en otro caso
        pass  # cae al código general abajo

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
    # Alvarado: H = xy  (grado 2, 1 nodo A₁ en origen)
    h_al = Hamiltonian("quadratic", {"a1":0,"a2":0,"b11":0,"b12":1,"b22":0})
    # Armónico simétrico: x³+y³-3xy-3x²y-3xy²  (Δf=0, 2 nodos A₁, simétrico)
    h_harm = Hamiltonian("sym_cubic", HARMONIC_CUBIC_COEFS)
    return [h_m1, h_al, h_harm]
