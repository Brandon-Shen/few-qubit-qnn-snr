"""Secondary normalized interaction indices (Section 15).

I_AB = (M_AB * M_0) / (M_A * M_B),  M = RMS pointwise SNR_est
J_AB = (G_AB * G_0) / (G_A * G_B),  G = RMS exact-gradient magnitude

computed per configuration by aggregating over every depth/budget/
initialization/parameter cell within that configuration. Secondary/
descriptive only -- never part of the H1-H4 confirmatory family. Zero
denominators return an explicit `undefined` marker with a reason instead of
a substituted epsilon (Section 15 forbids epsilon substitution).
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from qnn_snr.config import CONFIGURATION_TABLE

# (label, config_0, config_A, config_B, config_AB)
PAIR_SPECS = [
    ("E_L", 1, 2, 3, 5),
    ("E_R", 1, 2, 4, 6),
    ("L_R", 1, 3, 4, 7),
]


def _rms(values: np.ndarray) -> float:
    finite = values[np.isfinite(values)]
    if len(finite) == 0:
        return float("nan")
    return float(np.sqrt(np.mean(finite ** 2)))


def _rms_snr_by_config(pointwise_df: pd.DataFrame) -> dict[int, float]:
    return {
        cid: _rms(g["SNR_est"].to_numpy())
        for cid, g in pointwise_df.groupby("configuration_id")
    }


def _rms_exact_gradient_by_config(exact_df: pd.DataFrame) -> dict[int, float]:
    return {
        cid: _rms(np.abs(g["exact_gradient"].to_numpy()))
        for cid, g in exact_df.groupby("configuration_id")
    }


def _safe_ratio(num: float, denom_a: float, denom_b: float) -> tuple[float | None, str | None]:
    if not (np.isfinite(denom_a) and np.isfinite(denom_b)):
        return None, "one or both single-intervention RMS values are undefined (no finite pointwise SNR observed)"
    if denom_a == 0.0 or denom_b == 0.0:
        return None, "zero-denominator: a single-intervention RMS value is exactly zero"
    if not np.isfinite(num):
        return None, "numerator (combined-intervention or baseline RMS) is undefined"
    return num / (denom_a * denom_b), None


def compute_interaction_indices(pointwise_df: pd.DataFrame, exact_df: pd.DataFrame) -> pd.DataFrame:
    M = _rms_snr_by_config(pointwise_df)
    G = _rms_exact_gradient_by_config(exact_df)
    rows = []
    for label, c0, cA, cB, cAB in PAIR_SPECS:
        M0, MA, MB, MAB = M.get(c0, np.nan), M.get(cA, np.nan), M.get(cB, np.nan), M.get(cAB, np.nan)
        G0, GA, GB, GAB = G.get(c0, np.nan), G.get(cA, np.nan), G.get(cB, np.nan), G.get(cAB, np.nan)

        I_val, I_reason = _safe_ratio(MAB * M0 if np.isfinite(MAB) and np.isfinite(M0) else float("nan"), MA, MB)
        J_val, J_reason = _safe_ratio(GAB * G0 if np.isfinite(GAB) and np.isfinite(G0) else float("nan"), GA, GB)

        rows.append({
            "pair": label,
            "M_0": M0, "M_A": MA, "M_B": MB, "M_AB": MAB,
            "I_AB": I_val, "I_AB_undefined_reason": I_reason,
            "G_0": G0, "G_A": GA, "G_B": GB, "G_AB": GAB,
            "J_AB": J_val, "J_AB_undefined_reason": J_reason,
            "interpretation": (
                "undefined" if I_val is None else
                ("sub-additive fold change" if I_val < 1 else
                 "super-additive fold change" if I_val > 1 else "multiplicative independence")
            ),
        })
    return pd.DataFrame(rows)
