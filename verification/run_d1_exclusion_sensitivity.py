"""QMI/QIP robustness package, Task 1: D=1-exclusion sensitivity fit.

Refits H2_H4_FORMULA on the adopted end-to-end-only data after excluding
*all* block-count-1 observations (D in {2,3,4,6}), distinct from the
existing D>=3 sensitivity fit (D in {3,4,6}) in
verification/d_ge_3_sensitivity_refit.md, which is left untouched.

Per verification/qmi_qip_analysis_inputs.md Section 4, depth_z is a
precomputed column standardized once against the full five-level design
({1,2,3,4,6}) and is never recentered per-subset by fit_h2h4_model -- so
simply filtering rows and calling fit_h2h4_model() already satisfies the
"preserve full-sweep centering/scaling" requirement with no extra code.
This script verifies that explicitly (prints the depth_z levels present in
each subset) rather than assuming it.

Run from the repo root: python verification/run_d1_exclusion_sensitivity.py
"""
from __future__ import annotations

import json
import time
from pathlib import Path

import numpy as np
import pandas as pd
from scipy import stats

from qnn_snr.stats.models import fit_h2h4_model

REPO_ROOT = Path(__file__).resolve().parent.parent
TARGET_COEFS = ["E:L", "E:R", "L:R:depth_z"]
HYP_LABELS = {"E:L": "H2 (beta_EL)", "E:R": "H3 (beta_ER)", "L:R:depth_z": "H4 (beta_LRd)"}


def summarize(res, label: str) -> dict:
    exog_cols = list(res.raw_result.model.exog_names) if res.raw_result is not None else []
    warnings_seen = getattr(res, "_warnings", None)
    return {
        "label": label,
        "converged": res.converged,
        "optimizer_used": res.optimizer_used,
        "n_obs": res.n_obs,
        "n_groups": res.n_groups,
        "n_vc_levels": res.n_vc_levels,
        "condition_number": res.condition_number,
        "singular_fit": res.singular_fit,
        "group_intercept_var": res.random_effect_variances.get("group_intercept_var"),
        "nested_param_var": res.random_effect_variances.get("nested_param_var"),
    }


def main():
    pw = pd.read_parquet(REPO_ROOT / "results" / "production_confirmatory" / "pointwise_gradient_statistics.parquet")
    eo_full = pw[pw["analysis_mode"] == "finite_shot_end_to_end"].copy()
    eo_d1excl = eo_full[eo_full["depth"] != 1].copy()

    print(f"full-sweep end-to-end rows: {len(eo_full)}; depth_z levels present: "
          f"{sorted(eo_full[['depth', 'depth_z']].drop_duplicates()['depth_z'].tolist())}")
    print(f"D!=1 end-to-end rows: {len(eo_d1excl)}; depth_z levels present: "
          f"{sorted(eo_d1excl[['depth', 'depth_z']].drop_duplicates()['depth_z'].tolist())}")
    assert set(eo_d1excl["depth_z"].unique()) < set(eo_full["depth_z"].unique()), (
        "D!=1 subset's depth_z values must be a strict subset of the full-sweep values "
        "(i.e. no re-centering happened) -- aborting, this is the critical comparability check."
    )
    print("CONFIRMED: D!=1 subset reuses the full-sweep depth_z levels verbatim (no re-centering).\n")

    t0 = time.time()
    res_full = fit_h2h4_model(eo_full)
    t_full = time.time() - t0
    print(f"full-sweep fit: {t_full:.1f}s, converged={res_full.converged}, "
          f"optimizer={res_full.optimizer_used}, singular_fit={res_full.singular_fit}")

    t0 = time.time()
    res_d1excl = fit_h2h4_model(eo_d1excl)
    t_d1 = time.time() - t0
    print(f"D!=1 fit: {t_d1:.1f}s, converged={res_d1excl.converged}, "
          f"optimizer={res_d1excl.optimizer_used}, singular_fit={res_d1excl.singular_fit}")

    rows = []
    for coef in TARGET_COEFS:
        full_est, full_se = res_full.params[coef], res_full.bse[coef]
        d1_est, d1_se = res_d1excl.params[coef], res_d1excl.bse[coef]
        full_z = full_est / full_se
        d1_z = d1_est / d1_se
        full_p = 2 * (1 - stats.norm.cdf(abs(full_z)))
        d1_p = 2 * (1 - stats.norm.cdf(abs(d1_z)))
        full_ci = (full_est - 1.96 * full_se, full_est + 1.96 * full_se)
        d1_ci = (d1_est - 1.96 * d1_se, d1_est + 1.96 * d1_se)
        abs_change = d1_est - full_est
        change_in_se_units = abs_change / full_se
        sign_agree = bool(np.sign(full_est) == np.sign(d1_est))
        ci_overlap = not (d1_ci[1] < full_ci[0] or d1_ci[0] > full_ci[1])

        for model_label, est, se, z, p, ci, n_obs in (
            ("full_sweep_adopted", full_est, full_se, full_z, full_p, full_ci, res_full.n_obs),
            ("d_neq_1_sensitivity", d1_est, d1_se, d1_z, d1_p, d1_ci, res_d1excl.n_obs),
        ):
            rows.append({
                "hypothesis": HYP_LABELS[coef], "coefficient": coef, "model": model_label,
                "estimate": est, "se": se, "wald_z": z, "p_unadjusted": p,
                "ci_lo": ci[0], "ci_hi": ci[1], "n_obs": n_obs,
            })
        rows.append({
            "hypothesis": HYP_LABELS[coef], "coefficient": coef, "model": "comparison",
            "estimate": abs_change, "se": float("nan"), "wald_z": change_in_se_units,
            "p_unadjusted": float("nan"), "ci_lo": float(sign_agree), "ci_hi": float(ci_overlap),
            "n_obs": res_d1excl.n_obs,
        })
        print(f"\n{HYP_LABELS[coef]} [{coef}]:")
        print(f"  full sweep   : {full_est:+.6f} (SE {full_se:.6f}, z={full_z:+.3f}, p={full_p:.4g}) "
              f"CI [{full_ci[0]:+.6f}, {full_ci[1]:+.6f}]")
        print(f"  D!=1 subset  : {d1_est:+.6f} (SE {d1_se:.6f}, z={d1_z:+.3f}, p={d1_p:.4g}) "
              f"CI [{d1_ci[0]:+.6f}, {d1_ci[1]:+.6f}]")
        print(f"  abs change   : {abs_change:+.6f}  ({change_in_se_units:+.3f} original-SE units)")
        print(f"  sign agree   : {sign_agree}   CI overlap: {ci_overlap}")

    out_df = pd.DataFrame(rows)
    out_path = REPO_ROOT / "results" / "sensitivity_analyses" / "d1_exclusion_sensitivity_coefficients.csv"
    out_df.to_csv(out_path, index=False)
    print(f"\nwrote {out_path}")

    diag = {
        "full_sweep": summarize(res_full, "full_sweep_adopted"),
        "d_neq_1": summarize(res_d1excl, "d_neq_1_sensitivity"),
        "full_sweep_wallclock_s": t_full,
        "d_neq_1_wallclock_s": t_d1,
    }
    diag_path = REPO_ROOT / "verification" / "_d1_exclusion_sensitivity_diagnostics.json"
    diag_path.write_text(json.dumps(diag, indent=2, default=str), encoding="utf-8")
    print(f"wrote {diag_path}")


if __name__ == "__main__":
    main()
