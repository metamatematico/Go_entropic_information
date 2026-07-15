"""
topology.py
===========
Análisis topológico de la fibración de Milnor H: ℝ² → ℝ.

Usa gudhi.CubicalComplex para calcular diagramas de persistencia H0/H1
sobre los conjuntos de subnivel {H ≤ c} en una malla discreta.

Métricas extraídas
------------------
- max_h1_lifetime   : vida máxima de una barra H1 (normalizada a [0,1])
- n_long_bars       : barras H1 con vida > τ
- mean_h1_lifetime  : vida media de todas las barras H1
- h0_components     : número de componentes conexas en la fibración
- well_depth        : |max(c*) - min(c*)| (profundidad del pozo energético)
- diagram           : diagrama de persistencia completo (birth, death) por dim
"""

import numpy as np
from typing import Dict, Any, List, Tuple

try:
    import gudhi
    _HAS_GUDHI = True
except ImportError:
    _HAS_GUDHI = False
    import warnings
    warnings.warn("gudhi no disponible; usando fallback simplificado.")


def _make_grid(h_fn, L: float, N: int) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Evalúa H en una malla N×N sobre [-L,L]²."""
    xs = np.linspace(-L, L, N)
    ys = np.linspace(-L, L, N)
    X, Y = np.meshgrid(xs, ys)
    Z = np.array(h_fn(X, Y), dtype=float)
    return X, Y, Z


def _persistence_gudhi(Z: np.ndarray, tau: float) -> Dict[str, Any]:
    """Calcula persistencia con gudhi.CubicalComplex (subnivel sets)."""
    # gudhi usa convención: filtration = Z aplanado en orden C (row-major)
    cc = gudhi.CubicalComplex(
        dimensions=list(Z.shape),
        top_dimensional_cells=Z.flatten().tolist()
    )
    cc.compute_persistence()
    pairs = cc.persistence()          # list of (dim, (birth, death))

    diag = {0: [], 1: []}
    for dim, (b, d) in pairs:
        if dim in diag and d != float('inf'):
            diag[dim].append((float(b), float(d)))

    return diag


def _fallback_persistence(Z: np.ndarray, n_thresh: int = 80,
                           tau: float = 0.15) -> Dict[str, Any]:
    """
    Persistencia aproximada sin gudhi.
    Usa scipy.ndimage para rastrear componentes conexas de {Z ≤ c}.
    H1 se estima por agujeros en el complemento.
    """
    from scipy.ndimage import label

    zmin, zmax = Z.min(), Z.max()
    thresholds = np.linspace(zmin, zmax, n_thresh)
    prev_cc = 0
    diag0 = []
    for c in thresholds:
        mask = (Z <= c)
        lbl, n = label(mask)
        if n > prev_cc:
            for _ in range(n - prev_cc):
                diag0.append((c, zmax))
        prev_cc = n
    diag1 = []   # fallback: no H1 sin gudhi completo
    return {0: diag0, 1: diag1}


def compute_persistence(h_fn, L: float = 2.0, N: int = 150,
                         tau: float = 0.15,
                         n_thresh: int = 80) -> Dict[str, Any]:
    """
    Punto de entrada principal para el análisis TDA.

    Returns
    -------
    dict con:
      diagram, max_h1_lifetime, n_long_bars, mean_h1_lifetime,
      h0_bars, well_depth, grid_Z
    """
    _, _, Z = _make_grid(h_fn, L, N)
    zmin, zmax = float(Z.min()), float(Z.max())
    zrange = zmax - zmin if zmax > zmin else 1.0

    if _HAS_GUDHI:
        diag = _persistence_gudhi(Z, tau)
    else:
        diag = _fallback_persistence(Z, n_thresh, tau)

    h1_lifetimes = [d - b for b, d in diag.get(1, [])]
    h1_lifetimes_norm = [l / zrange for l in h1_lifetimes]

    max_h1  = float(max(h1_lifetimes_norm)) if h1_lifetimes_norm else 0.0
    n_long  = int(sum(1 for l in h1_lifetimes_norm if l > tau))
    mean_h1 = float(np.mean(h1_lifetimes_norm)) if h1_lifetimes_norm else 0.0
    h0_bars = len(diag.get(0, []))

    return {
        "diagram":           diag,
        "max_h1_lifetime":   max_h1,
        "n_long_bars":       n_long,
        "mean_h1_lifetime":  mean_h1,
        "h0_bars":           h0_bars,
        "well_depth":        zrange,
        "grid_Z":            Z,
        "zmin":              zmin,
        "zmax":              zmax,
    }


def plot_persistence_diagram(tda_result: Dict[str, Any],
                              title: str = "",
                              ax=None):
    """Dibuja el diagrama de persistencia (birth vs death)."""
    import matplotlib.pyplot as plt

    if ax is None:
        fig, ax = plt.subplots(figsize=(5, 5))
    diag = tda_result["diagram"]
    zmin, zmax = tda_result["zmin"], tda_result["zmax"]

    ax.plot([zmin, zmax], [zmin, zmax], 'k--', lw=0.8, alpha=0.4)
    colors = {0: "#4488FF", 1: "#FF4444"}
    labels = {0: "H₀", 1: "H₁"}
    for dim, pts in diag.items():
        if pts:
            bs, ds = zip(*pts)
            ax.scatter(bs, ds, s=28, alpha=0.75, label=labels[dim],
                       color=colors.get(dim, "gray"), zorder=3)
    ax.set_xlabel("Nacimiento (birth)")
    ax.set_ylabel("Muerte (death)")
    ax.set_title(title or "Diagrama de persistencia")
    ax.legend(fontsize=8)
    ax.set_aspect("equal")
    return ax
