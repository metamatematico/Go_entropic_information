"""
klein.py
=========
Descomposición de un Hamiltoniano H(x,y) en las cuatro piezas del grupo
de Klein V4 = Z2 x Z2 generado por las dos simetrías del problema:

    sigma : (x,y) -> (y,x)      (posición: cuál punto del par es "el primero")
    tau   : (x,y) -> (-x,-y)    (color: qué número representa a cada color)

Ambas son involuciones y conmutan, así que generan el grupo de Klein
(no el cíclico Z4) — todos sus elementos no triviales tienen orden 2, y
por eso todos sus caracteres son reales, con valores en {+1,-1}.

El operador de Reynolds asociado a cada carácter chi,

    P_chi(H) = (1/|G|) * sum_{g in G} chi(g) * (g . H)

proyecta H sobre la pieza que transforma como chi. Es idempotente y
completo: la suma de las cuatro proyecciones reconstruye H exactamente
(verificable con `verify_decomposition`), así que la descomposición
REORGANIZA el polinomio, nunca lo trunca.

Por qué importa aquí
--------------------
`relaxation_field` (experimento 07) nunca evalúa H en un solo orden de
argumentos: siempre usa la suma simétrica H(s,q) + H(q,s). Esa suma es
el doble de la proyección sigma-invariante, así que el campo solo puede
ver P_++ (+) P_+- — 4 de las 7 dimensiones de `cubic_mixed`. Las tres
restantes (Delta_a, Delta_b, Delta_c) se cancelan exactamente, sin
importar su magnitud.

De las dos piezas visibles, P_++ es PAR en color y P_+- es IMPAR. El
sesgo de color de H se define como esa componente impar visible:

    sesgo(H) := P_+-(H)     no nulo  <=>  (Sigma_a, Sigma_c) != (0,0)

Es una propiedad del polinomio, calculable antes de tocar un tablero.

ADVERTENCIA DE ALCANCE: esta reducción vale ÚNICAMENTE para el campo de
relajación. El análisis topológico de Gamma(H) evalúa H(x,y) directo,
sin simetrizar — ahí los 7 coeficientes sí importan por separado.
"""

from typing import Dict, Tuple

import sympy as sp

# Variables simbólicas canónicas — las mismas de families.py (exp. 06)
x, y = sp.symbols('x y', real=True)

# Los cuatro caracteres de V4: (signo bajo sigma, signo bajo tau)
CHARACTERS = {
    "P++": (+1, +1),   # par en color,   simétrico en posición  -> VISIBLE
    "P+-": (+1, -1),   # impar en color, simétrico en posición  -> VISIBLE (= SESGO)
    "P-+": (-1, +1),   # par en color,   anti en posición       -> invisible
    "P--": (-1, -1),   # impar en color, anti en posición       -> invisible
}

VISIBLE_PIECES = ("P++", "P+-")
INVISIBLE_PIECES = ("P-+", "P--")

# Nombres de coeficientes de la plantilla cubic_mixed, en el orden de families.py
CUBIC_MIXED_NAMES = ["a1", "a2", "b11", "b12", "b22", "c112", "c122"]


# ── Acción del grupo ──────────────────────────────────────────────────────────

def apply_sigma(expr: sp.Expr) -> sp.Expr:
    """(sigma . H)(x,y) = H(y,x) — intercambia el orden del par."""
    return sp.expand(expr.subs({x: y, y: x}, simultaneous=True))


def apply_tau(expr: sp.Expr) -> sp.Expr:
    """(tau . H)(x,y) = H(-x,-y) — invierte los colores del tablero."""
    return sp.expand(expr.subs({x: -x, y: -y}, simultaneous=True))


def group_action(expr: sp.Expr) -> Dict[str, sp.Expr]:
    """Los cuatro elementos del grupo aplicados a H: e, sigma, tau, sigma*tau."""
    e = sp.expand(expr)
    s = apply_sigma(e)
    t = apply_tau(e)
    st = apply_tau(s)          # == apply_sigma(t), porque conmutan
    return {"e": e, "sigma": s, "tau": t, "sigma_tau": st}


def commutes(expr: sp.Expr) -> bool:
    """Verifica sigma(tau(H)) == tau(sigma(H)) término a término."""
    return sp.simplify(apply_sigma(apply_tau(expr)) - apply_tau(apply_sigma(expr))) == 0


# ── Proyección de Reynolds ────────────────────────────────────────────────────

def reynolds(expr: sp.Expr, chi: Tuple[int, int]) -> sp.Expr:
    """P_chi(H) = (1/4) * sum_g chi(g) (g . H), para chi = (sig_sigma, sig_tau).

    El carácter de sigma*tau es el producto de los otros dos, porque los
    caracteres de un grupo abeliano son homomorfismos."""
    chi_sigma, chi_tau = chi
    g = group_action(expr)
    total = (g["e"]
             + chi_sigma * g["sigma"]
             + chi_tau * g["tau"]
             + (chi_sigma * chi_tau) * g["sigma_tau"])
    return sp.expand(total / 4)


def klein_decomposition(expr: sp.Expr) -> Dict[str, sp.Expr]:
    """Las cuatro piezas de Klein de H, indexadas por nombre de carácter."""
    return {name: reynolds(expr, chi) for name, chi in CHARACTERS.items()}


def verify_decomposition(expr: sp.Expr) -> bool:
    """Completitud: sum_chi P_chi(H) == H exactamente (sin residuo)."""
    pieces = klein_decomposition(expr)
    return sp.simplify(sum(pieces.values()) - sp.expand(expr)) == 0


def verify_idempotent(expr: sp.Expr, piece: str = "P+-") -> bool:
    """Idempotencia: P_chi(P_chi(H)) == P_chi(H)."""
    chi = CHARACTERS[piece]
    once = reynolds(expr, chi)
    return sp.simplify(reynolds(once, chi) - once) == 0


# ── Lo que el campo de relajación ve ──────────────────────────────────────────

def symmetrized(expr: sp.Expr) -> sp.Expr:
    """H~(x,y) = H(x,y) + H(y,x) — exactamente lo que evalúa
    `relaxation_field` en cada actualización de punto. Vive en
    P_++ (+) P_+-; las piezas anti-invariantes se cancelan."""
    return sp.expand(expr + apply_sigma(expr))


def visible_part(expr: sp.Expr) -> sp.Expr:
    """La parte que el campo puede ver: P_++ + P_+- = H~/2."""
    pieces = klein_decomposition(expr)
    return sp.expand(pieces["P++"] + pieces["P+-"])


def color_bias(expr: sp.Expr) -> sp.Expr:
    """El sesgo de color de H: su proyección P_+- (componente impar en
    color de la parte visible). Cero si y solo si (Sigma_a, Sigma_c) = (0,0)."""
    return reynolds(expr, CHARACTERS["P+-"])


def is_equivariant(expr: sp.Expr) -> bool:
    """True si P_+-(H) == 0 — condición necesaria y suficiente para que el
    campo relajado cumpla F(-B) = -F(B) en todo tablero (teorema de
    equivariancia). Equivale a que H no tenga sesgo de color."""
    return sp.simplify(color_bias(expr)) == 0


# ── Coordenadas efectivas de cubic_mixed ──────────────────────────────────────

def effective_coefficients(coefs: Dict[str, float]) -> Dict[str, float]:
    """Las 4 combinaciones que el campo ve y las 3 que ignora, a partir de
    los 7 coeficientes crudos de `cubic_mixed` (los que falten se toman 0,
    lo que cubre las plantillas quadratic / sparse_cubic / h_m1)."""
    c = {name: float(coefs.get(name, 0.0)) for name in CUBIC_MIXED_NAMES}
    return {
        # visibles
        "Sigma_a": c["a1"] + c["a2"],
        "Sigma_b": c["b11"] + c["b22"],
        "b12": c["b12"],
        "Sigma_c": c["c112"] + c["c122"],
        # invisibles para relaxation_field (pero parte real del polinomio)
        "Delta_a": c["a1"] - c["a2"],
        "Delta_b": c["b11"] - c["b22"],
        "Delta_c": c["c112"] - c["c122"],
    }


def raw_from_effective(sigma_a: float, sigma_b: float, b12: float,
                       sigma_c: float) -> Dict[str, float]:
    """Reparto simétrico de las 4 dimensiones efectivas a los 7 coeficientes
    crudos (a1=a2=Sigma_a/2, etc.). Por la identidad de Klein cualquier otro
    reparto de las mismas sumas da EL MISMO campo, así que esta elección no
    pierde generalidad para el objetivo de Delta R^2 — es la misma que usa
    `optimize_coefficients.make_objective_4d`."""
    return {"a1": sigma_a / 2, "a2": sigma_a / 2,
            "b11": sigma_b / 2, "b12": b12, "b22": sigma_b / 2,
            "c112": sigma_c / 2, "c122": sigma_c / 2}


def has_color_bias(coefs: Dict[str, float], tol: float = 1e-12) -> bool:
    """Versión numérica de `is_equivariant`, sobre coeficientes crudos:
    hay sesgo de color si (Sigma_a, Sigma_c) != (0,0)."""
    eff = effective_coefficients(coefs)
    return abs(eff["Sigma_a"]) > tol or abs(eff["Sigma_c"]) > tol


def piece_norms(expr: sp.Expr) -> Dict[str, float]:
    """Norma L2 de los coeficientes de cada pieza de Klein — la medida que
    usa la Figura 4 del informe para comparar cuánto pesa cada componente."""
    out = {}
    for name, piece in klein_decomposition(expr).items():
        poly = sp.Poly(piece, x, y) if piece != 0 else None
        coeffs = [float(c) for c in poly.coeffs()] if poly is not None else []
        out[name] = float(sum(c * c for c in coeffs) ** 0.5)
    return out


if __name__ == "__main__":
    # Autoverificación sobre cubic_mixed genérico y sobre H_M1.
    a1, a2, b11, b12, b22, c112, c122 = sp.symbols(
        "a1 a2 b11 b12 b22 c112 c122", real=True)
    H = (a1 * x + a2 * y + b11 * x**2 + b12 * x * y + b22 * y**2
         + c112 * x**2 * y + c122 * x * y**2)

    print("sigma y tau conmutan sobre cubic_mixed generico:", commutes(H))
    print("Descomposicion completa (suma == H):", verify_decomposition(H))
    print("P+- idempotente:", verify_idempotent(H))
    print()
    for name, piece in klein_decomposition(H).items():
        marca = "VISIBLE" if name in VISIBLE_PIECES else "invisible"
        print(f"  {name} ({marca}): {sp.simplify(piece)}")

    print("\nH_M1 = x + 2y - x^2*y - x*y^2")
    H_M1 = x + 2 * y - x**2 * y - x * y**2
    print("  sesgo de color P+-:", sp.simplify(color_bias(H_M1)))
    print("  es equivariante (sin sesgo):", is_equivariant(H_M1))
    print("  coeficientes efectivos:",
          effective_coefficients({"a1": 1, "a2": 2, "c112": -1, "c122": -1}))
    print("  normas por pieza:", piece_norms(H_M1))
