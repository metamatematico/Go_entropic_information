"""
algebra.py
==========
Análisis algebraico y simbólico de Hamiltonianos polinómicos.

Funciones principales
---------------------
analyze(h)  → dict con grado, soporte, puntos críticos, valores críticos,
              clasificación de singularidades (nodo A₁), discriminante.
"""

import warnings
import numpy as np
import sympy as sp
from scipy.optimize import fsolve
from typing import List, Dict, Any

_x, _y = sp.symbols('x y', real=True)

# Pares spin válidos en Go
VALID_PAIRS = [(-1,-1),(-1,0),(-1,1),(1,-1),(1,0),(1,1)]


def _degree(expr: sp.Expr) -> int:
    return sp.total_degree(expr, _x, _y)


def _support(expr: sp.Expr) -> List[str]:
    poly = sp.Poly(expr, _x, _y)
    return [str(sp.Mul(*[v**e for v,e in zip(poly.gens, mon)]))
            for mon, coef in zip(poly.monoms(), poly.coeffs())
            if coef != 0]


def _symmetries(expr: sp.Expr) -> List[str]:
    syms = []
    if sp.simplify(expr.subs([(_x,-_x),(_y,-_y)]) + expr) == 0:
        syms.append("odd: H(-x,-y)=-H(x,y)")
    if sp.simplify(expr.subs([(_x,-_x),(_y,-_y)]) - expr) == 0:
        syms.append("even: H(-x,-y)=H(x,y)")
    if sp.simplify(expr.subs([(_x,_y),(_y,_x)]) - expr) == 0:
        syms.append("symmetric: H(x,y)=H(y,x)")
    return syms


def _critical_points_symbolic(expr: sp.Expr,
                               timeout: float = 5.0) -> List[Dict]:
    """Intenta resolver ∇H=0 simbólicamente con sympy."""
    Hx = sp.diff(expr, _x)
    Hy = sp.diff(expr, _y)
    try:
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            sols = sp.solve([Hx, Hy], [_x, _y], dict=True)
        pts = []
        for sol in sols:
            xv = complex(sol.get(_x, 0))
            yv = complex(sol.get(_y, 0))
            if abs(xv.imag) < 1e-8 and abs(yv.imag) < 1e-8:
                pts.append({"x": float(xv.real), "y": float(yv.real),
                             "source": "symbolic"})
        return pts
    except Exception:
        return []


def _critical_points_numeric(fn_H, fn_Hx, fn_Hy,
                              n_starts: int = 25,
                              box: float = 2.5,
                              tol: float = 1e-9) -> List[Dict]:
    """Busca ∇H=0 numéricamente con múltiples inicios."""
    rng  = np.random.default_rng(0)
    pts  = []
    seen = []

    def system(xy):
        return [fn_Hx(xy[0], xy[1]), fn_Hy(xy[0], xy[1])]

    starts = rng.uniform(-box, box, (n_starts, 2))
    for x0, y0 in starts:
        try:
            sol = fsolve(system, [x0, y0], full_output=True)
            xv, yv = sol[0]
            info = sol[1]
            if np.linalg.norm(system([xv, yv])) < 1e-6:
                # Dedup
                duplicate = any(
                    abs(xv - p["x"]) < 1e-4 and abs(yv - p["y"]) < 1e-4
                    for p in seen
                )
                if not duplicate:
                    seen.append({"x": float(xv), "y": float(yv),
                                 "source": "numeric"})
        except Exception:
            continue
    return seen


def _classify_critical(expr: sp.Expr, xv: float, yv: float) -> str:
    """Clasifica un punto crítico por la Hessiana (nodo A₁ si det<0)."""
    H = sp.Matrix([[sp.diff(expr, _x, _x), sp.diff(expr, _x, _y)],
                   [sp.diff(expr, _x, _y), sp.diff(expr, _y, _y)]])
    Hnum = np.array([[float(H[i,j].subs([(_x,xv),(_y,yv)]).evalf())
                      for j in range(2)] for i in range(2)])
    det  = np.linalg.det(Hnum)
    tr   = np.trace(Hnum)
    if abs(det) < 1e-8:
        return "degenerate"
    elif det < 0:
        return "A1_node"   # silla (nodo A₁ en las fibras)
    elif tr > 0:
        return "min"
    else:
        return "max"


def analyze(h, cfg: dict = None) -> Dict[str, Any]:
    """
    Análisis algebraico completo de un Hamiltoniano.

    Returns
    -------
    dict con claves:
      degree, support, symmetries, critical_points, critical_values,
      n_nodes_A1, milnor_bound, values_on_valid_pairs
    """
    cfg = cfg or {}
    n_starts = cfg.get("n_crit_starts", 25)
    box      = cfg.get("box_L", 2.5) + 0.5

    expr = h.expr
    fn_H  = sp.lambdify((_x,_y), expr, "numpy")
    fn_Hx = sp.lambdify((_x,_y), sp.diff(expr,_x), "numpy")
    fn_Hy = sp.lambdify((_x,_y), sp.diff(expr,_y), "numpy")

    # ── Algebraic ──────────────────────────────────────────────────────────────
    deg     = _degree(expr)
    support = _support(expr)
    syms    = _symmetries(expr)

    # ── Puntos críticos ────────────────────────────────────────────────────────
    cpts_sym = _critical_points_symbolic(expr)
    cpts_num = _critical_points_numeric(fn_H, fn_Hx, fn_Hy, n_starts, box)

    # Combinar y deduplicar
    all_cpts = list(cpts_sym)
    for p in cpts_num:
        dup = any(abs(p["x"]-q["x"]) < 1e-3 and abs(p["y"]-q["y"]) < 1e-3
                  for q in all_cpts)
        if not dup:
            all_cpts.append(p)

    # Clasificar y añadir valor crítico
    crit_vals = []
    for p in all_cpts:
        try:
            p["c_val"] = float(fn_H(p["x"], p["y"]))
            p["type"]  = _classify_critical(expr, p["x"], p["y"])
        except Exception:
            p["c_val"] = None
            p["type"]  = "unknown"
        crit_vals.append(p["c_val"])

    crit_vals_real = sorted([v for v in crit_vals if v is not None])
    n_nodes = sum(1 for p in all_cpts if p["type"] == "A1_node")

    # Separación entre valores críticos consecutivos
    if len(crit_vals_real) > 1:
        diffs = np.diff(crit_vals_real)
        min_sep = float(np.min(np.abs(diffs)))
    else:
        min_sep = float("inf")

    # Número de Milnor estimado (cota superior por Bezout: (d-1)²)
    milnor_bound = (deg - 1)**2 if deg >= 2 else 0

    # ── Valores sobre pares Go válidos ──────────────────────────────────────────
    vals_on_pairs = {str(p): float(fn_H(p[0], p[1])) for p in VALID_PAIRS}

    return {
        "degree":          deg,
        "support":         support,
        "symmetries":      syms,
        "critical_points": all_cpts,
        "critical_values": crit_vals_real,
        "n_nodes_A1":      n_nodes,
        "min_crit_separation": min_sep,
        "milnor_bound":    milnor_bound,
        "values_on_valid_pairs": vals_on_pairs,
    }
