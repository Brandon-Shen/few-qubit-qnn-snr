"""H2 robustness package, Phase 4 (F.2) and (F.3): zero-variance
sensitivity beyond complete-case exclusion.

(F.1) is satisfied by scripts/run_h2_decomposition.py (numerator/denominator
modeled separately, SNR never formed for zero-variance cells).

(F.2) treats "landing on exactly zero empirical variance" as a modeled
finite-replicate outcome: a logistic model of P(zero_variance_flag) on the
same factorial structure.

(F.3) is a PREDEFINED variance-floor sensitivity grid (fixed in
verification/h2_robustness_replication_plan.md Section 2.2(F.3) before this
script was run): for each floor f, cells with shot_variance==0 are
refloored to f and SNR_est recomputed, ONLY in this labeled sensitivity
path. The full coefficient trajectory across the grid is reported; no
single floor is selected as "the" answer.

Run from the repo root: python scripts/run_h2_zero_variance_sensitivity.py
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd
import statsmodels.formula.api as smf

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

from qnn_snr.stats.models import H2_H4_FORMULA, fit_mixed_model  # noqa: E402

PROD_DIR = REPO_ROOT / "results" / "production_confirmatory"
OUT_DIR = REPO_ROOT / "results" / "h2_robustness" / "robust_inference"
Z975 = 1.959963984540054

# Fixed BEFORE running (verification/h2_robustness_replication_plan.md Sec. 2.2 F.3):
# 0 (baseline/no floor), then anchored to machine precision, the minimum
# nonzero observed shot_variance, and empirical percentiles of the nonzero
# distribution, up to the empirical median.
FLOOR_GRID = [0.0, 1e-12, 6.227451072756091e-11, 1e-9,
              8.246974048968847e-07, 1.0579851428657802e-05, 1e-3]


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    pw = pd.read_parquet(PROD_DIR / "pointwise_gradient_statistics.parquet")
    eo = pw[pw["analysis_mode"] == "finite_shot_end_to_end"].copy()

    # --- F.2: logistic model of P(zero_variance_flag) ---
    logit_df = eo.copy()
    logit_df["zv"] = logit_df["zero_variance_flag"].astype(int)
    logit_formula = "zv ~ E*L*R + depth_z + log2_budget + E:depth_z + L:depth_z + R:depth_z + L:R:depth_z"
    logit_result = smf.logit(logit_formula, data=logit_df).fit(disp=False)
    logit_rows = []
    for coef in ("E:L", "E:R", "L:R:depth_z", "L"):
        if coef not in logit_result.params:
            continue
        est = logit_result.params[coef]
        se = logit_result.bse[coef]
        logit_rows.append({
            "coefficient": coef, "estimate_logodds": est, "se": se,
            "ci95_lo": est - Z975 * se, "ci95_hi": est + Z975 * se,
            "p_unadjusted": logit_result.pvalues[coef],
            "odds_ratio": float(np.exp(est)),
        })
    logit_summary = pd.DataFrame(logit_rows)
    logit_summary.to_csv(OUT_DIR / "h2_zero_variance_logistic_model.csv", index=False)
    print("logistic model of P(zero_variance_flag):")
    print(logit_summary.to_string(index=False))
    print(f"note: this is a fixed-effects-only logistic fit (no per-initialization "
          f"random intercept -- statsmodels has no stable REML mixed-logit fit available "
          f"in this environment; stated as a limitation, not hidden).")

    # --- F.3: variance-floor sensitivity grid ---
    floor_rows = []
    for floor in FLOOR_GRID:
        d = eo.copy()
        if floor == 0.0:
            d = d[~d["zero_variance_flag"]].copy()  # baseline: complete-case exclusion (identical to production)
            treatment = "complete_case_exclusion (production baseline)"
        else:
            zv_mask = d["zero_variance_flag"]
            d.loc[zv_mask, "shot_variance"] = floor
            d.loc[zv_mask, "shot_sd"] = np.sqrt(floor)
            d.loc[zv_mask, "SNR_est"] = np.abs(d.loc[zv_mask, "mu_hat"]) / np.sqrt(floor)
            treatment = f"variance_floor={floor:.3e}"
        d["y"] = np.arcsinh(d["SNR_est"])
        try:
            fit = fit_mixed_model(H2_H4_FORMULA, d, "y")
            est, se = fit.params["E:L"], fit.bse["E:L"]
            floor_rows.append({
                "floor": floor, "treatment": treatment, "n_obs": fit.n_obs,
                "converged": fit.converged, "singular_fit": fit.singular_fit,
                "E:L_estimate": est, "E:L_se": se,
                "E:L_ci95_lo": est - Z975 * se, "E:L_ci95_hi": est + Z975 * se,
                "error": None,
            })
        except Exception as exc:  # noqa: BLE001 -- report failure explicitly, do not skip the grid point
            floor_rows.append({
                "floor": floor, "treatment": treatment, "n_obs": len(d),
                "converged": False, "singular_fit": None,
                "E:L_estimate": float("nan"), "E:L_se": float("nan"),
                "E:L_ci95_lo": float("nan"), "E:L_ci95_hi": float("nan"),
                "error": str(exc),
            })
        print(f"floor={floor!r}: E:L={floor_rows[-1]['E:L_estimate']}")

    floor_df = pd.DataFrame(floor_rows)
    floor_df.to_csv(OUT_DIR / "h2_variance_floor_sensitivity_grid.csv", index=False)
    print(f"\nwrote {OUT_DIR}")
    print("Full E:L trajectory across the predefined floor grid (no floor selected as primary):")
    print(floor_df[["floor", "treatment", "n_obs", "E:L_estimate", "E:L_ci95_lo", "E:L_ci95_hi"]].to_string(index=False))


if __name__ == "__main__":
    main()
