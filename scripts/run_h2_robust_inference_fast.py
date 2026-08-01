"""H2 robustness package, Phase 4 (C) and (D): the fast robustness checks
that do not require repeated resampling refits --

  (C) a cluster-robust (initialization-level) OLS refit of the identical
      H2-H4 fixed-effect formula, as a heteroscedasticity- and
      within-initialization-correlation-robust alternative to the mixed
      model's Wald SEs;
  (D) depth- and budget-stratified diagnostics (exploratory, not
      confirmatory -- no Holm correction, no "best stratum" selected).

Per verification/h2_robustness_replication_plan.md Section 2.2 (C), (D).
Reads only from results/production_confirmatory/; writes only to
results/h2_robustness/robust_inference/.

Run from the repo root: python scripts/run_h2_robust_inference_fast.py
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd
import statsmodels.formula.api as smf

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

from qnn_snr.stats.models import H2_H4_FORMULA, build_h2h4_dataset, fit_mixed_model  # noqa: E402

PROD_DIR = REPO_ROOT / "results" / "production_confirmatory"
OUT_DIR = REPO_ROOT / "results" / "h2_robustness" / "robust_inference"
TARGET_COEFS = ("E:L", "E:R", "L:R:depth_z")
Z975 = 1.959963984540054

# Depth is constant within a per-depth stratum, so depth_z and its
# interactions must be dropped there (fixed before running, not chosen
# post hoc -- collinearity would otherwise make the design matrix singular).
STRATIFIED_BY_DEPTH_FORMULA = "y ~ E*L*R + log2_budget"


def load_eligible() -> pd.DataFrame:
    pw = pd.read_parquet(PROD_DIR / "pointwise_gradient_statistics.parquet")
    eo = pw[pw["analysis_mode"] == "finite_shot_end_to_end"].copy()
    return build_h2h4_dataset(eo)  # applies the identical zero-variance filter, adds y=asinh(SNR_est)


def run_cluster_robust(df: pd.DataFrame) -> pd.DataFrame:
    model = smf.ols(H2_H4_FORMULA, data=df)
    result = model.fit(cov_type="cluster", cov_kwds={"groups": df["initialization_id"]})
    rows = []
    for coef in TARGET_COEFS:
        est = result.params[coef]
        se = result.bse[coef]
        rows.append({
            "method": "cluster_robust_ols_initialization_level",
            "coefficient": coef,
            "estimate": est,
            "se_cluster_robust": se,
            "ci95_lo": est - Z975 * se,
            "ci95_hi": est + Z975 * se,
            "p_unadjusted": result.pvalues[coef],
            "n_obs": int(result.nobs),
            "n_clusters": df["initialization_id"].nunique(),
        })
    return pd.DataFrame(rows)


def run_depth_stratified(df: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for depth, g in df.groupby("depth"):
        try:
            fit = fit_mixed_model(STRATIFIED_BY_DEPTH_FORMULA, g, "y")
        except Exception as exc:  # noqa: BLE001 -- report failure explicitly, do not drop the stratum
            rows.append({"depth": depth, "coefficient": "E:L", "estimate": float("nan"),
                         "se": float("nan"), "n_obs": len(g), "converged": False, "error": str(exc)})
            continue
        for coef in ("E:L", "E:R"):  # L:R:depth_z has no meaning within a fixed depth
            if coef not in fit.params:
                continue
            est, se = fit.params[coef], fit.bse[coef]
            rows.append({
                "depth": depth, "coefficient": coef, "estimate": est, "se": se,
                "ci95_lo": est - Z975 * se, "ci95_hi": est + Z975 * se,
                "n_obs": fit.n_obs, "converged": fit.converged, "singular_fit": fit.singular_fit,
                "error": None,
            })
    return pd.DataFrame(rows)


def run_budget_stratified(df: pd.DataFrame) -> pd.DataFrame:
    # Fixed split, decided before running: B<=500 vs B>500 (the only split
    # tested -- a finer split would leave too few cells per stratum for the
    # nested random-effects structure with only 50 groups).
    rows = []
    for label, mask in (("B<=500", df["budget"] <= 500), ("B>500", df["budget"] > 500)):
        g = df[mask]
        try:
            fit = fit_mixed_model(H2_H4_FORMULA, g, "y")
        except Exception as exc:  # noqa: BLE001
            rows.append({"budget_stratum": label, "coefficient": "E:L", "estimate": float("nan"),
                         "se": float("nan"), "n_obs": len(g), "converged": False, "error": str(exc)})
            continue
        for coef in TARGET_COEFS:
            est, se = fit.params[coef], fit.bse[coef]
            rows.append({
                "budget_stratum": label, "coefficient": coef, "estimate": est, "se": se,
                "ci95_lo": est - Z975 * se, "ci95_hi": est + Z975 * se,
                "n_obs": fit.n_obs, "converged": fit.converged, "singular_fit": fit.singular_fit,
                "error": None,
            })
    return pd.DataFrame(rows)


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    df = load_eligible()

    cluster_df = run_cluster_robust(df)
    cluster_df.to_csv(OUT_DIR / "h2_cluster_robust_ols.csv", index=False)
    print("cluster-robust OLS:")
    print(cluster_df.to_string(index=False))

    depth_df = run_depth_stratified(df)
    depth_df.to_csv(OUT_DIR / "h2_depth_stratified.csv", index=False)
    print("\ndepth-stratified (exploratory):")
    print(depth_df.to_string(index=False))

    budget_df = run_budget_stratified(df)
    budget_df.to_csv(OUT_DIR / "h2_budget_stratified.csv", index=False)
    print("\nbudget-stratified (exploratory):")
    print(budget_df.to_string(index=False))

    print(f"\nwrote {OUT_DIR}")


if __name__ == "__main__":
    main()
