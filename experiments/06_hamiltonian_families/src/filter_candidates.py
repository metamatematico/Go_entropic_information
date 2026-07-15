"""
filter_candidates.py
====================
Filtrado de candidatos por criterios cuantitativos + test de robustez.

Criterios por defecto (configurables)
--------------------------------------
1. τ1      : vida máxima H1 normalizada > τ1 (default 0.20)
2. ΔE      : profundidad de pozo > ΔE  (default 0.50)
3. δ_crit  : separación mínima entre valores críticos > δ (default 0.30)

Un candidato pasa si cumple al menos min_criteria (default 2 de 3).

Robustez
--------
Se perturban los coeficientes ±5% y se verifica que el score TDA
se mantenga por encima de τ1 en al menos el 80% de las perturbaciones.
"""

import numpy as np
from typing import Dict, Any, List, Tuple
from .families import Hamiltonian
from .topology import compute_persistence


def _tda_score(tda: Dict) -> float:
    """Score combinado TDA: mezcla vida máxima H1, barras largas, profundidad."""
    return (0.50 * tda["max_h1_lifetime"] +
            0.30 * min(tda["n_long_bars"] / 5.0, 1.0) +
            0.20 * min(tda["well_depth"] / 4.0, 1.0))


def filter_candidate(alg: Dict, tda: Dict, cfg: Dict) -> Dict[str, Any]:
    """
    Aplica los tres criterios y devuelve un dict de filtrado.

    Returns
    -------
    dict con: passes, criteria_met, criteria_results, tda_score
    """
    tau1       = cfg.get("tau1",       0.20)
    delta_E    = cfg.get("delta_E",    0.50)
    delta_crit = cfg.get("delta_crit", 0.30)
    min_crit   = cfg.get("min_criteria", 2)

    criteria = {
        "tau1":       tda["max_h1_lifetime"] > tau1,
        "delta_E":    tda["well_depth"]       > delta_E,
        "delta_crit": alg["min_crit_separation"] > delta_crit,
    }
    met    = [k for k, v in criteria.items() if v]
    passes = len(met) >= min_crit

    return {
        "passes":           passes,
        "criteria_met":     met,
        "criteria_results": criteria,
        "tda_score":        _tda_score(tda),
    }


def robustness_test(h: Hamiltonian, tda_score_ref: float,
                    cfg: Dict) -> Dict[str, float]:
    """
    Perturba los coeficientes ±5% n_robustness veces y
    mide la fracción de runs donde tda_score > tau1.
    """
    n_rob  = cfg.get("n_robustness", 12)
    tau1   = cfg.get("tau1", 0.20)
    L      = cfg.get("box_L", 2.0)
    N      = cfg.get("grid_size", 100)   # resolución reducida para velocidad
    tau_t  = cfg.get("tau", 0.15)

    rng    = np.random.default_rng(42)
    scores = []

    coef_arr = h.coef_vector
    for _ in range(n_rob):
        noise   = rng.uniform(-0.05, 0.05, len(coef_arr))
        new_arr = coef_arr * (1 + noise)
        new_coefs = {k: float(v) for k, v in
                     zip(h.coefs.keys(), new_arr)}
        try:
            h_pert = Hamiltonian(h.template, new_coefs)
            tda_p  = compute_persistence(h_pert, L=L, N=N, tau=tau_t)
            scores.append(_tda_score(tda_p))
        except Exception:
            scores.append(0.0)

    frac_ok = float(np.mean([s > tau1 for s in scores]))
    return {
        "robustness":       frac_ok,
        "mean_score_pert":  float(np.mean(scores)),
        "std_score_pert":   float(np.std(scores)),
        "n_perturbations":  n_rob,
    }
