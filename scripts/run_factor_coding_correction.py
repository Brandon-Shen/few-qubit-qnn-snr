"""Run the frozen factor-coding reparameterization and primary-family audit."""
from __future__ import annotations

import hashlib
import json
import shutil
import subprocess
import warnings
from pathlib import Path

import numpy as np
import pandas as pd
from scipy import stats

from qnn_snr.stats.factor_coding import (
    H1_CENTERED_FORMULA,
    H2_H4_CENTERED_FORMULA,
    add_centered_factors,
    design_coefficient_map,
    transform_bootstrap_draws,
    transform_fixed_effects,
)
from qnn_snr.stats.holm import holm_bonferroni
from qnn_snr.stats.models import (
    H1_FORMULA,
    H2_H4_FORMULA,
    build_h1_dataset,
    build_h2h4_dataset,
    fit_mixed_model,
)

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "results" / "primary_corrected" / "effect_coded"
SUPERSEDED = ROOT / "results" / "superseded" / "direct_01_factor_coding"
PLAN_COMMIT = "ec35570569cb0078bbf3f49a4b1b421ccad8c1c4"
TARGETS = {
    "H1": ("h1", "E:L", "E_c:L_c"),
    "H2": ("h2h4", "E:L", "E_c:L_c"),
    "H3": ("h2h4", "E:R", "E_c:R_c"),
    "H4": ("h2h4", "L:R:depth_z", "L_c:R_c:depth_z"),
}


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def fit_pair(direct_formula, centered_formula, data, response):
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        direct = fit_mixed_model(direct_formula, data, response)
        centered = fit_mixed_model(centered_formula, add_centered_factors(data), response)
    if direct.error or centered.error or not direct.converged or not centered.converged:
        raise RuntimeError(f"Nonconverged correction fit: direct={direct.error}, centered={centered.error}")
    mapping, design = design_coefficient_map(direct.raw_result, centered.raw_result)
    if design["max_column_space_projection_error"] > 1e-10:
        raise RuntimeError(f"Model spaces differ: {design}")
    tb, tv = transform_fixed_effects(direct.raw_result, mapping)
    cfe = centered.raw_result.fe_params
    ccov = centered.raw_result.cov_params().loc[cfe.index, cfe.index]
    comparisons = {
        "max_abs_coefficient_difference": float(np.max(np.abs(tb - cfe))),
        "max_abs_covariance_difference": float(np.max(np.abs(tv - ccov))),
        "max_abs_fitted_difference": float(np.max(np.abs(direct.raw_result.fittedvalues - centered.raw_result.fittedvalues))),
        "max_abs_residual_difference": float(np.max(np.abs(direct.raw_result.resid - centered.raw_result.resid))),
        "log_likelihood_difference": float(centered.raw_result.llf - direct.raw_result.llf),
        "scale_difference": float(centered.raw_result.scale - direct.raw_result.scale),
        "random_effect_variance_differences": {
            key: centered.random_effect_variances[key] - direct.random_effect_variances[key]
            for key in direct.random_effect_variances
        },
    }
    if comparisons["max_abs_coefficient_difference"] > 1e-7 or comparisons["max_abs_fitted_difference"] > 1e-7:
        raise RuntimeError(f"Centered refit does not match algebraic transform: {comparisons}")
    return direct, centered, mapping, tb, tv, {**design, **comparisons}, [str(w.message) for w in caught]


def main() -> None:
    if OUT.exists() or SUPERSEDED.exists():
        raise FileExistsError("Correction output directory already exists; refusing to overwrite")
    exact_path = ROOT / "results/production_confirmatory/raw/exact.parquet"
    pointwise_path = ROOT / "results/production_confirmatory/pointwise_gradient_statistics.parquet"
    exact = pd.read_parquet(exact_path)
    key = ["initialization_id", "configuration_id", "depth", "parameter_id"]
    if exact.duplicated(key).any() or set(exact.analysis_mode) != {"statevector_exact"}:
        raise ValueError("H1 uniqueness or mode validation failed")
    pointwise = pd.read_parquet(pointwise_path)
    pointwise = pointwise[pointwise.analysis_mode == "finite_shot_end_to_end"].copy()
    h1_data = build_h1_dataset(exact)
    h2_data = build_h2h4_dataset(pointwise)

    h1 = fit_pair(H1_FORMULA, H1_CENTERED_FORMULA, h1_data, "a")
    h2 = fit_pair(H2_H4_FORMULA, H2_H4_CENTERED_FORMULA, h2_data, "y")
    pairs = {"h1": h1, "h2h4": h2}

    rows = []
    pvals = []
    for hypothesis, (family, direct_name, centered_name) in TARGETS.items():
        direct, centered, mapping, tb, tv, audit, fit_warnings = pairs[family]
        old_est = direct.params[direct_name]
        old_se = direct.bse[direct_name]
        est = float(centered.params[centered_name])
        se = float(centered.bse[centered_name])
        z = est / se
        p = float(2 * stats.norm.sf(abs(z)))
        pvals.append(p)
        rows.append({
            "hypothesis": hypothesis,
            "historical_coefficient": direct_name,
            "historical_estimate": old_est,
            "historical_standard_error": old_se,
            "historical_p_unadjusted": float(2 * stats.norm.sf(abs(old_est / old_se))),
            "corrected_coefficient": centered_name,
            "corrected_estimate": est,
            "corrected_standard_error": se,
            "corrected_ci_lo": est - stats.norm.ppf(0.975) * se,
            "corrected_ci_hi": est + stats.norm.ppf(0.975) * se,
            "corrected_wald_z": z,
            "corrected_p_unadjusted": p,
            "n_observations": centered.n_obs,
            "n_initialization_clusters": centered.n_groups,
            "optimizer": centered.optimizer_used,
            "converged": centered.converged,
            "singular_fit": centered.singular_fit,
        })
    corrected_holm, corrected_reject = holm_bonferroni(pvals)
    historical_holm = pd.read_csv(ROOT / "results/production_confirmatory/confirmatory_hypotheses.csv").set_index("hypothesis")
    for row, hp, reject in zip(rows, corrected_holm, corrected_reject):
        old = historical_holm.loc[row["hypothesis"]]
        row["historical_p_holm"] = float(old.p_holm)
        row["historical_reject_after_holm"] = bool(old.reject_after_holm)
        row["corrected_p_holm"] = hp
        row["corrected_reject_after_holm"] = reject
        row["family_decision_changed"] = bool(old.reject_after_holm) != reject

    h1_draw_path = ROOT / "verification/_bootstrap_checkpoints/h1_boot.parquet"
    h2_draw_path = ROOT / "results/production_corrected_end_to_end/bootstrap_end_to_end_h2_h4_iterations.parquet"
    h1_draws = transform_bootstrap_draws(pd.read_parquet(h1_draw_path), "h1")
    h2_draws = transform_bootstrap_draws(pd.read_parquet(h2_draw_path), "h2h4")
    boot_rows = []
    for hypothesis, draws, column in (
        ("H1", h1_draws, "E_c:L_c"), ("H2", h2_draws, "E_c:L_c"),
        ("H3", h2_draws, "E_c:R_c"), ("H4", h2_draws, "L_c:R_c:depth_z"),
    ):
        lo, median, hi = np.percentile(draws[column], [2.5, 50, 97.5])
        boot_rows.append({"hypothesis": hypothesis, "coefficient": column,
                          "completed_bootstrap_iterations": len(draws),
                          "median": median, "percentile_ci_lo": lo, "percentile_ci_hi": hi})

    OUT.mkdir(parents=True)
    SUPERSEDED.mkdir(parents=True)
    pd.DataFrame(rows).to_csv(OUT / "corrected_confirmatory_hypotheses.csv", index=False)
    pd.DataFrame(boot_rows).to_csv(OUT / "corrected_bootstrap_intervals_current_draws.csv", index=False)
    h1_draws.to_parquet(OUT / "h1_centered_bootstrap_400_transformed.parquet", index=False)
    h2_draws.to_parquet(OUT / "h2h4_centered_bootstrap_443_transformed.parquet", index=False)
    h1[2].to_csv(OUT / "h1_design_coefficient_map.csv")
    h2[2].to_csv(OUT / "h2h4_design_coefficient_map.csv")

    archive_files = [
        ROOT / "results/production_confirmatory/confirmatory_hypotheses.csv",
        h1_draw_path,
        ROOT / "verification/_bootstrap_checkpoints/h1_boot.meta.json",
        h2_draw_path,
        ROOT / "results/production_corrected_end_to_end/bootstrap_end_to_end_h2_h4_summary.csv",
        ROOT / "results/production_corrected_end_to_end/bootstrap_end_to_end_h2_h4_seed_manifest.csv",
    ]
    for source in archive_files:
        shutil.copy2(source, SUPERSEDED / source.name)
    (SUPERSEDED / "README.md").write_text(
        "# Superseded direct-0/1 factor-coding audit artifacts\n\n"
        "These are preserved copies. Pairwise coefficients are reference-level simple interactions, "
        "not centered factorial averages. Original source files remain untouched.\n", encoding="utf-8")

    metadata = {
        "schema_version": 1,
        "status": "coding_correction_current_draws",
        "plan_commit": PLAN_COMMIT,
        "analysis_commit": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip(),
        "inputs": {str(p.relative_to(ROOT)).replace('\\','/'): sha256(p) for p in (exact_path, pointwise_path, h1_draw_path, h2_draw_path)},
        "h1_audit": h1[5], "h2h4_audit": h2[5],
        "h1_warnings": h1[6], "h2h4_warnings": h2[6],
        "simple_effect_identities": {
            "EL_R0": "E:L", "EL_R1": "E:L + E:L:R", "EL_average_R": "E:L + 0.5*E:L:R",
            "ER_L0": "E:R", "ER_L1": "E:R + E:L:R", "ER_average_L": "E:R + 0.5*E:L:R"
        },
        "bootstrap_validation_status": "draw transformation complete; explicit resample-refit subset validation pending",
    }
    (OUT / "correction_audit.json").write_text(json.dumps(metadata, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
