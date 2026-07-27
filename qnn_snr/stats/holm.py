"""Confirmatory p-values, Wald tests, and Holm-Bonferroni adjustment
(Section 13). Exactly four confirmatory hypotheses: H1 (eta_EL, exact-signal
model), H2 (beta_EL), H3 (beta_ER), H4 (beta_LRd), all two-sided, corrected
jointly with family-wise alpha=0.05 -- ASSUMPTION A9 documents the p-value
engine (mixed-model Wald z-statistic against a normal reference)."""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd
from scipy import stats

from qnn_snr.stats.models import MixedModelResult

P_VALUE_METHOD = "wald_normal"  # ASSUMPTION A9

HYPOTHESES = [
    {"hypothesis": "H1", "outcome": "asinh(abs(exact_gradient))", "coefficient": "E:L",
     "coef_label": "eta_EL", "model": "exact_signal"},
    {"hypothesis": "H2", "outcome": "asinh(SNR_est)", "coefficient": "E:L",
     "coef_label": "beta_EL", "model": "estimator_snr"},
    {"hypothesis": "H3", "outcome": "asinh(SNR_est)", "coefficient": "E:R",
     "coef_label": "beta_ER", "model": "estimator_snr"},
    {"hypothesis": "H4", "outcome": "asinh(SNR_est)", "coefficient": "L:R:depth_z",
     "coef_label": "beta_LRd", "model": "estimator_snr"},
]


def holm_bonferroni(pvalues: list[float], alpha: float = 0.05) -> tuple[list[float], list[bool]]:
    n = len(pvalues)
    order = np.argsort(pvalues)
    adjusted = [None] * n
    running_max = 0.0
    for rank, idx in enumerate(order):
        adj = min((n - rank) * pvalues[idx], 1.0)
        running_max = max(running_max, adj)
        adjusted[idx] = running_max
    reject = [adjusted[i] <= alpha for i in range(n)]
    return adjusted, reject


def wald_test(estimate: float, se: float) -> tuple[float, float]:
    if not np.isfinite(se) or se <= 0:
        return float("nan"), float("nan")
    z = estimate / se
    p = 2 * (1 - stats.norm.cdf(abs(z)))
    return z, p


def _interpretation(hyp: str, reject: bool, ci_lo: float, ci_hi: float) -> str:
    if not reject:
        return ("Failed to reject H0 after Holm correction; this is not evidence of "
                "additivity, equivalence, or that the interventions have identical effects.")
    if np.isfinite(ci_lo) and np.isfinite(ci_hi):
        if ci_hi < 0:
            return "Rejected H0; coefficient CI entirely below zero (sub-additive on the tested scale)."
        if ci_lo > 0:
            return "Rejected H0; coefficient CI entirely above zero (super-additive on the tested scale)."
    return "Rejected H0 (two-sided); bootstrap CI direction not conclusive."


def build_confirmatory_table(h1_result: MixedModelResult, h2h4_result: MixedModelResult,
                              alpha: float = 0.05,
                              bootstrap_ci: dict[str, tuple[float, float]] | None = None) -> pd.DataFrame:
    bootstrap_ci = bootstrap_ci or {}
    rows = []
    pvals = []
    for h in HYPOTHESES:
        model_result = h1_result if h["model"] == "exact_signal" else h2h4_result
        coef = h["coefficient"]
        if model_result.error is not None or coef not in model_result.params:
            estimate, se, z, p = float("nan"), float("nan"), float("nan"), 1.0
        else:
            estimate = model_result.params[coef]
            se = model_result.bse.get(coef, float("nan"))
            z, p = wald_test(estimate, se)
            if not np.isfinite(p):
                p = 1.0
        pvals.append(p)
        ci_lo, ci_hi = bootstrap_ci.get(h["hypothesis"], (float("nan"), float("nan")))
        rows.append({
            "hypothesis": h["hypothesis"], "coefficient_label": h["coef_label"],
            "coefficient_name": coef, "outcome_scale": h["outcome"], "estimate": estimate,
            "standard_error": se, "wald_statistic": z, "p_unadjusted": p,
            "p_value_method": P_VALUE_METHOD, "bootstrap_ci_lo": ci_lo, "bootstrap_ci_hi": ci_hi,
        })

    adjusted, reject = holm_bonferroni(pvals, alpha)
    for row, p_holm, rej in zip(rows, adjusted, reject):
        row["p_holm"] = p_holm
        row["reject_after_holm"] = rej
        row["family_wise_alpha"] = alpha
        row["interpretation"] = _interpretation(row["hypothesis"], rej, row["bootstrap_ci_lo"], row["bootstrap_ci_hi"])

    return pd.DataFrame(rows)
