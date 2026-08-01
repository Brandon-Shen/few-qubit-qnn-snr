"""Secondary check referenced in verification/h1_finite_difference_check.md Section 4:
does the E x L interaction on the exact-signal (H1) scale vary with depth?

The confirmatory H1_FORMULA has no E:L:depth_z term (qnn_snr/stats/models.py), and the
codebase's existing SENSITIVITY_FORMULA only extends the H2-H4 (finite-shot SNR) model,
not H1 -- there is no ready-made exact-signal sensitivity model to reuse. This script
fits an ad hoc extension of H1_FORMULA with "+ E:L:depth_z" directly, using the same
fit_mixed_model machinery the pipeline uses, on the full confirmatory exact dataset
(results/production_confirmatory/raw/exact.parquet, all 50 inits x 5 depths -- no new simulation, fit-only).

Not part of the pipeline; run standalone from the repo root:
    python verification/h1_el_depth_sensitivity.py

Writes: verification/h1_el_depth_sensitivity_results.json
"""
from __future__ import annotations

import json
from pathlib import Path

from qnn_snr.schema import read_tidy_dataset
from qnn_snr.stats.models import H1_FORMULA, build_h1_dataset, fit_mixed_model

REPO_ROOT = Path(__file__).resolve().parent.parent
EXACT_PARQUET = REPO_ROOT / "results" / "production_confirmatory" / "raw" / "exact.parquet"
FORMULA = H1_FORMULA + " + E:L:depth_z"


def main():
    exact_df = read_tidy_dataset(EXACT_PARQUET)
    exact_df = exact_df[exact_df["analysis_mode"] == "statevector_exact"]
    print(f"loaded {len(exact_df)} exact-signal rows from {EXACT_PARQUET}")

    d = build_h1_dataset(exact_df)
    result = fit_mixed_model(FORMULA, d, "a")

    out = {
        "formula": FORMULA,
        "n_obs": result.n_obs,
        "n_groups": result.n_groups,
        "n_vc_levels": result.n_vc_levels,
        "converged": result.converged,
        "optimizer_used": result.optimizer_used,
        "attempted_optimizers": result.attempted_optimizers,
        "params": result.params,
        "bse": result.bse,
        "z_scores": {k: (result.params[k] / result.bse[k]) if result.bse.get(k) else None
                     for k in result.params if k in result.bse},
        "random_effect_variances": result.random_effect_variances,
        "condition_number": result.condition_number,
        "singular_fit": result.singular_fit,
        "residual_diagnostics": result.residual_diagnostics,
        "error": result.error,
        "reference_H1_formula": H1_FORMULA,
        "reference_confirmatory_eta_EL": 0.004346,
        "note": ("Ad hoc extension of H1_FORMULA, not part of the pipeline's confirmatory "
                 "model set. Fit on the full confirmatory exact dataset (no new simulation). "
                 "Descriptive/diagnostic only -- not a preregistered test, not part of the "
                 "H1-H4 Holm family."),
    }

    out_path = Path(__file__).parent / "h1_el_depth_sensitivity_results.json"
    out_path.write_text(json.dumps(out, indent=2, default=str), encoding="utf-8")

    print(f"converged: {result.converged} ({result.optimizer_used})")
    print(f"E:L         = {result.params.get('E:L'):.6f}  (SE {result.bse.get('E:L'):.6f})")
    print(f"E:L:depth_z = {result.params.get('E:L:depth_z'):.6f}  (SE {result.bse.get('E:L:depth_z'):.6f})")
    print(f"wrote {out_path}")


if __name__ == "__main__":
    main()
