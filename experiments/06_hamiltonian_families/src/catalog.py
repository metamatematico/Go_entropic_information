"""
catalog.py
==========
Gestión del catálogo JSON de Hamiltonianos candidatos.

Esquema de cada entrada
-----------------------
{
  "id":          "H_042",
  "template":    "cubic_mixed",
  "coefficients": {...},
  "expression":  "...",
  "algebraic":   { degree, support, critical_points, ... },
  "tda":         { max_h1_lifetime, n_long_bars, ... },
  "filter":      { passes, criteria_met, tda_score, robustness },
  "validation":  { n_games, improvement, p_value },
  "scores":      { tda_score, robustness, strategy_score, total },
  "metadata":    { created, is_reference }
}
"""

import json
import os
from datetime import date
from typing import Dict, Any, List, Optional
import numpy as np
import pandas as pd


def _safe(obj):
    """Convierte recursivamente tipos no-JSON a tipos Python nativos."""
    import sympy as sp
    if isinstance(obj, (np.integer,)):           return int(obj)
    if isinstance(obj, (np.floating,)):          return float(obj)
    if isinstance(obj, np.ndarray):              return obj.tolist()
    if isinstance(obj, sp.Basic):                return str(obj)
    if isinstance(obj, dict):                    return {k: _safe(v) for k,v in obj.items()}
    if isinstance(obj, (list, tuple)):           return [_safe(v) for v in obj]
    if hasattr(obj, 'item'):                     return obj.item()   # numpy scalar
    return obj


def _total_score(filt: Dict, val: Dict) -> float:
    tda_s  = filt.get("tda_score", 0.0)
    rob_s  = filt.get("robustness", 0.0)
    imp    = val.get("improvement") or 0.0
    strat  = min(max(imp, 0.0), 1.0)
    return round(0.45*tda_s + 0.30*rob_s + 0.25*strat, 4)


class Catalog:
    """Catálogo JSON de Hamiltonianos con métodos de consulta."""

    def __init__(self, path: str):
        self.path = path
        self.entries: List[Dict] = []
        if os.path.exists(path):
            with open(path) as f:
                self.entries = json.load(f)

    def add(self, h, alg: Dict, tda: Dict, filt: Dict,
            val: Dict, is_reference: bool = False) -> str:
        idx = len(self.entries)
        entry_id = f"H_{idx:04d}"

        # Quitar grid_Z del tda (demasiado grande para JSON)
        tda_clean = {k: v for k, v in tda.items() if k != "grid_Z"}
        # Quitar critical_points completos (solo resumen)
        alg_clean = {k: v for k, v in alg.items()
                     if k not in ("critical_points",)}
        alg_clean["n_critical_points"] = len(alg.get("critical_points", []))
        alg_clean["critical_points_summary"] = [
            {"x": round(p["x"],4), "y": round(p["y"],4),
             "c_val": round(p.get("c_val") or 0, 4),
             "type": p.get("type","?")}
            for p in alg.get("critical_points", [])
        ]

        scores = {
            "tda_score":      filt.get("tda_score", 0.0),
            "robustness":     filt.get("robustness", {}).get("robustness", 0.0)
                              if isinstance(filt.get("robustness"), dict)
                              else filt.get("robustness", 0.0),
            "strategy_score": val.get("improvement") or 0.0,
            "total":          _total_score(filt, val),
        }

        entry = {
            "id":           entry_id,
            "template":     h.template,
            "coefficients": dict(h.coefs),
            "expression":   str(h.expr),
            "algebraic":    _safe(alg_clean),
            "tda":          _safe(tda_clean),
            "filter":       _safe(filt),
            "validation":   _safe(val),
            "scores":       _safe(scores),
            "metadata": {
                "created":      str(date.today()),
                "is_reference": is_reference,
            }
        }
        self.entries.append(entry)
        return entry_id

    def save(self):
        os.makedirs(os.path.dirname(self.path), exist_ok=True)
        with open(self.path, "w") as f:
            json.dump(self.entries, f, indent=2, ensure_ascii=False)

    def to_dataframe(self) -> pd.DataFrame:
        rows = []
        for e in self.entries:
            row = {
                "id":           e["id"],
                "template":     e["template"],
                "expression":   e["expression"],
                "degree":       e["algebraic"].get("degree"),
                "n_nodes_A1":   e["algebraic"].get("n_nodes_A1"),
                "n_crit_pts":   e["algebraic"].get("n_critical_points"),
                "passes":       e["filter"].get("passes"),
                "max_h1":       e["tda"].get("max_h1_lifetime"),
                "n_long_bars":  e["tda"].get("n_long_bars"),
                "well_depth":   e["tda"].get("well_depth"),
                "robustness":   e["scores"].get("robustness"),
                "improvement":  e["validation"].get("improvement"),
                "p_value":      e["validation"].get("p_value"),
                "total_score":  e["scores"].get("total"),
                "is_reference": e["metadata"].get("is_reference"),
            }
            rows.append(row)
        return pd.DataFrame(rows)

    def top_n(self, n: int = 10) -> List[Dict]:
        passing = [e for e in self.entries if e["filter"].get("passes")]
        return sorted(passing,
                      key=lambda e: e["scores"].get("total", 0),
                      reverse=True)[:n]
