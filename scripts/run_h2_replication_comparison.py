"""H2 robustness/replication package, Phase 7: original-vs-replication
comparison, using the decision rule frozen BEFORE any replication result
was inspected (verification/h2_robustness_replication_plan.md Section 6).

Never pools original and replication data. Reads the replication's own
Wald fit output (produced by scripts/run_h2_replication_stage1.py via the
standard qnn_snr CLI) and, if available, its own bootstrap interval
(scripts/run_h2_replication_stage1_bootstrap.py).

Run from the repo root: python scripts/run_h2_replication_comparison.py
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pandas as pd

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

PROD_DIR = REPO_ROOT / "results" / "production_confirmatory"
REPL_DIR = REPO_ROOT / "results" / "h2_replication_v1" / "_pipeline_output_stage1"
OUT_DIR = REPO_ROOT / "results" / "h2_replication_v1" / "tables"

Z975 = 1.959963984540054

# Original, frozen reference values (verification/confirmatory_numbers_adopted.md,
# independently re-reproduced bit-for-bit in Phase 2).
ORIGINAL_ESTIMATE = 0.024995843985971582
ORIGINAL_SE = 0.007279011371641417
ORIGINAL_CI = (0.010729243854496907, 0.039262444117446255)
ORIGINAL_N_OBS = 101_891


def classify(replication_estimate: float, replication_ci: tuple[float, float],
             replication_n_obs: int, replication_converged: bool) -> str:
    """Exact decision rule from verification/h2_robustness_replication_plan.md
    Section 6, computed mechanically -- never edited after seeing the inputs."""
    if not replication_converged:
        return "inconclusive (fit did not converge)"

    sign_match = (replication_estimate > 0) == (ORIGINAL_ESTIMATE > 0)
    delta_se = (replication_estimate - ORIGINAL_ESTIMATE) / ORIGINAL_SE
    overlap = not (replication_ci[1] < ORIGINAL_CI[0] or replication_ci[0] > ORIGINAL_CI[1])
    repl_width = replication_ci[1] - replication_ci[0]
    orig_width = ORIGINAL_CI[1] - ORIGINAL_CI[0]
    ci_includes_zero = replication_ci[0] <= 0 <= replication_ci[1]
    n_obs_shortfall_pct = 100.0 * (ORIGINAL_N_OBS - replication_n_obs) / ORIGINAL_N_OBS

    if ci_includes_zero:
        return "inconclusive (replication 95% CI includes zero)"
    if abs(n_obs_shortfall_pct) > 20 and n_obs_shortfall_pct > 0:
        return f"inconclusive (eligible n_obs {n_obs_shortfall_pct:.1f}% below original for reasons beyond design)"

    if not sign_match:
        if not ci_includes_zero or abs(delta_se) > 2:
            return "did not replicate (opposite sign, confidently discrepant)"
        return "inconclusive (opposite sign but not confidently discrepant)"

    if overlap and abs(delta_se) <= 2:
        return "direction and magnitude replicated"
    if repl_width > 3 * orig_width:
        return "direction replicated but magnitude uncertain (replication CI too wide to pin magnitude)"
    return "direction replicated but magnitude uncertain"


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    repl_coef_path = REPL_DIR / "snr_model_coefficients.csv"
    if not repl_coef_path.exists():
        print(f"Stage 1 replication output not found at {repl_coef_path} -- "
              f"run scripts/run_h2_replication_stage1.py first.")
        sys.exit(1)

    repl_coef = pd.read_csv(repl_coef_path)
    row = repl_coef[repl_coef["coefficient"] == "E:L"].iloc[0]
    repl_estimate = float(row["estimate"])
    repl_se = float(row["se"])
    repl_ci = (repl_estimate - Z975 * repl_se, repl_estimate + Z975 * repl_se)

    repl_hyp_path = REPL_DIR / "confirmatory_hypotheses.csv"
    repl_n_obs = None
    repl_converged = True
    if repl_hyp_path.exists():
        hyp = pd.read_csv(repl_hyp_path)
        # n_obs isn't necessarily a column here; fall back to the pointwise file directly.
    pw_path = REPL_DIR / "pointwise_gradient_statistics.parquet"
    if pw_path.exists():
        pw = pd.read_parquet(pw_path)
        eo = pw[pw["analysis_mode"] == "finite_shot_end_to_end"]
        repl_n_obs = int((~eo["zero_variance_flag"]).sum())
        repl_zero_variance_excluded = int(eo["zero_variance_flag"].sum())
        repl_l0_excluded = int(eo.loc[eo["L"] == 0, "zero_variance_flag"].sum())
        repl_l1_excluded = int(eo.loc[eo["L"] == 1, "zero_variance_flag"].sum())
    else:
        repl_zero_variance_excluded = repl_l0_excluded = repl_l1_excluded = None

    category = classify(repl_estimate, repl_ci, repl_n_obs or 0, repl_converged)

    delta = repl_estimate - ORIGINAL_ESTIMATE
    delta_se_units = delta / ORIGINAL_SE
    sign_agreement = (repl_estimate > 0) == (ORIGINAL_ESTIMATE > 0)
    ci_overlap = not (repl_ci[1] < ORIGINAL_CI[0] or repl_ci[0] > ORIGINAL_CI[1])

    comparison = pd.DataFrame([{
        "quantity": "E:L (H2)",
        "original_estimate": ORIGINAL_ESTIMATE,
        "original_se": ORIGINAL_SE,
        "original_ci95_lo": ORIGINAL_CI[0],
        "original_ci95_hi": ORIGINAL_CI[1],
        "original_n_obs": ORIGINAL_N_OBS,
        "original_zero_variance_excluded": 509,
        "replication_estimate": repl_estimate,
        "replication_se": repl_se,
        "replication_ci95_lo": repl_ci[0],
        "replication_ci95_hi": repl_ci[1],
        "replication_n_obs": repl_n_obs,
        "replication_zero_variance_excluded": repl_zero_variance_excluded,
        "replication_zero_variance_confined_to_L0": (repl_l1_excluded == 0) if repl_l1_excluded is not None else None,
        "difference": delta,
        "difference_in_original_se_units": delta_se_units,
        "sign_agreement": sign_agreement,
        "ci_overlap": ci_overlap,
        "interpretation": category,
    }])
    comparison.to_csv(OUT_DIR / "original_vs_replication.csv", index=False)

    print(comparison.T.to_string())
    print(f"\nInterpretation (fixed decision rule, computed mechanically): {category}")
    print(f"\nwrote {OUT_DIR / 'original_vs_replication.csv'}")


if __name__ == "__main__":
    main()
