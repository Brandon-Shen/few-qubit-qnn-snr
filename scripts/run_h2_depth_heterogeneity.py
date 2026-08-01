"""H2 robustness package: post-run depth-heterogeneity analysis.

Per verification/h2_depth_heterogeneity_plan.md (frozen before any
coefficient in this script was inspected). Explicitly post-run /
exploratory / diagnostic / sensitivity -- no Holm correction, not part of
the original H1-H4 confirmatory family, does not change the prespecified
H2 Wald/Holm rejection.

Reads only from the frozen original and replication pointwise files;
writes only to results/h2_robustness/depth_heterogeneity/ and
results/h2_replication_v1/depth_heterogeneity/.

Usage:
    python scripts/run_h2_depth_heterogeneity.py --dataset original
    python scripts/run_h2_depth_heterogeneity.py --dataset replication
    python scripts/run_h2_depth_heterogeneity.py --dataset both
    python scripts/run_h2_depth_heterogeneity.py --dataset both --resume
"""
from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
from pathlib import Path

import numpy as np
import pandas as pd

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

import qnn_snr.stats.depth_heterogeneity as dh  # noqa: E402
from qnn_snr.stats.models import build_h2h4_dataset  # noqa: E402

ORIGINAL_POINTWISE = REPO_ROOT / "results" / "production_confirmatory" / "pointwise_gradient_statistics.parquet"
REPLICATION_POINTWISE = REPO_ROOT / "results" / "h2_replication_v1" / "_pipeline_output_stage1" / "pointwise_gradient_statistics.parquet"
ORIGINAL_OUT = REPO_ROOT / "results" / "h2_robustness" / "depth_heterogeneity"
REPLICATION_OUT = REPO_ROOT / "results" / "h2_replication_v1" / "depth_heterogeneity"

ADOPTED_BETA_EL = 0.024995843985971582
ADOPTED_BETA_EL_SE = 0.007279011371641417


def sha256_of(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def git_commit() -> str:
    return subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=REPO_ROOT).decode().strip()


def package_versions() -> dict:
    import pandas as pd_, numpy as np_, scipy, statsmodels, patsy as patsy_
    return {"pandas": pd_.__version__, "numpy": np_.__version__, "scipy": scipy.__version__,
            "statsmodels": statsmodels.__version__, "patsy": patsy_.__version__}


def model_summary_row(fit: dh.FitWithWarnings, formula: str) -> dict:
    r = fit.result
    return {
        "formula": formula,
        "converged": r.converged,
        "optimizer_used": r.optimizer_used,
        "attempted_optimizers": json.dumps(r.attempted_optimizers),
        "singular_fit": r.singular_fit,
        "n_obs": r.n_obs,
        "n_groups": r.n_groups,
        "n_vc_levels": r.n_vc_levels,
        "condition_number": r.condition_number,
        "group_intercept_var": r.random_effect_variances.get("group_intercept_var"),
        "nested_param_var": r.random_effect_variances.get("nested_param_var"),
        "resid_mean": r.residual_diagnostics.get("resid_mean"),
        "resid_sd": r.residual_diagnostics.get("resid_sd"),
        "log_likelihood": float(r.raw_result.llf) if r.raw_result is not None else None,
        "n_warnings_captured": len(fit.warnings_captured),
        "warnings_captured": json.dumps(fit.warnings_captured),
        "error": r.error,
    }


def run_one_dataset(label: str, pointwise_path: Path, out_dir: Path,
                     include_zero: bool, diagnostics: dict) -> dict:
    """Runs models A, B, C, D, E (and F for label=='original') on one
    dataset. Returns a dict of DataFrames keyed by output filename stem,
    for the caller to write out and to build the cross-dataset comparison
    from."""
    out_dir.mkdir(parents=True, exist_ok=True)
    diagnostics[label] = {}

    input_hash = sha256_of(pointwise_path)
    pw = pd.read_parquet(pointwise_path)
    eo = pw[pw["analysis_mode"] == "finite_shot_end_to_end"].copy()
    dh.assert_single_confirmatory_mode(eo)
    dh.assert_depth_levels(eo)

    eligible = build_h2h4_dataset(eo)

    results: dict[str, pd.DataFrame] = {}

    # --- A. Continuous model ---
    fit_a = dh.fit_continuous_model(eo)
    diagnostics[label]["continuous_model"] = model_summary_row(fit_a, dh.CONTINUOUS_FORMULA)
    p = fit_a.result.params
    se = fit_a.result.bse
    zero_var_by_depth = eo.groupby("depth")["zero_variance_flag"].sum().to_dict()
    results["continuous_model"] = pd.DataFrame([{
        "coefficient": "E:L", "estimate": p.get("E:L"), "se": se.get("E:L"),
        "ci95_lo": p.get("E:L", np.nan) - dh.Z975 * se.get("E:L", np.nan),
        "ci95_hi": p.get("E:L", np.nan) + dh.Z975 * se.get("E:L", np.nan),
        "converged": fit_a.result.converged, "n_obs": fit_a.result.n_obs,
        "log_likelihood": float(fit_a.result.raw_result.llf),
        "zero_variance_by_depth": json.dumps({str(k): int(v) for k, v in zero_var_by_depth.items()}),
    }, {
        "coefficient": "E:L:depth_z", "estimate": p.get("E:L:depth_z"), "se": se.get("E:L:depth_z"),
        "ci95_lo": p.get("E:L:depth_z", np.nan) - dh.Z975 * se.get("E:L:depth_z", np.nan),
        "ci95_hi": p.get("E:L:depth_z", np.nan) + dh.Z975 * se.get("E:L:depth_z", np.nan),
        "converged": fit_a.result.converged, "n_obs": fit_a.result.n_obs,
        "log_likelihood": float(fit_a.result.raw_result.llf),
        "zero_variance_by_depth": json.dumps({str(k): int(v) for k, v in zero_var_by_depth.items()}),
    }])

    # --- B. Categorical model (primary, complete-case) ---
    fit_b = dh.fit_categorical_model(eo)
    diagnostics[label]["categorical_model"] = model_summary_row(fit_b, dh.CATEGORICAL_FORMULA)
    results["categorical_model"] = pd.DataFrame([{
        "converged": fit_b.result.converged, "singular_fit": fit_b.result.singular_fit,
        "n_obs": fit_b.result.n_obs, "n_groups": fit_b.result.n_groups,
        "log_likelihood": float(fit_b.result.raw_result.llf),
        "group_intercept_var": fit_b.result.random_effect_variances.get("group_intercept_var"),
        "nested_param_var": fit_b.result.random_effect_variances.get("nested_param_var"),
    }])
    raw_b = fit_b.result.raw_result
    contrasts_b = dh.compute_depth_contrasts(raw_b, eligible, eo)
    results["depth_contrasts"] = contrasts_b

    omnibus_b = dh.compute_omnibus_test(raw_b)
    results["omnibus_tests"] = pd.DataFrame([{"model": "categorical_mixed", **omnibus_b}])

    eq_w = dh.compute_weighted_contrast(raw_b, eligible, dh.equal_depth_weights(), "equal_depth")
    obs_w = dh.compute_weighted_contrast(raw_b, eligible, dh.observation_count_weights(eligible), "observation_count")
    weighted = pd.DataFrame([eq_w, obs_w, {
        "weighting": "adopted_confirmatory_pooled", "estimate": ADOPTED_BETA_EL,
        "se": ADOPTED_BETA_EL_SE,
        "ci95_lo": ADOPTED_BETA_EL - dh.Z975 * ADOPTED_BETA_EL_SE,
        "ci95_hi": ADOPTED_BETA_EL + dh.Z975 * ADOPTED_BETA_EL_SE,
        "p_unadjusted": None, "n_obs_total": fit_b.result.n_obs,
    }])
    results["weighted_contrasts"] = weighted

    # --- E. Cluster-robust categorical sensitivity ---
    cr_result, cr_dataset = dh.fit_cluster_robust_categorical(eo)
    cr_contrasts = dh.compute_depth_contrasts(cr_result, cr_dataset, eo)
    results["cluster_robust_depth_contrasts"] = cr_contrasts
    cr_omnibus = dh.compute_omnibus_test(cr_result)
    diagnostics[label]["cluster_robust_omnibus"] = cr_omnibus
    cr_eq_w = dh.compute_weighted_contrast(cr_result, cr_dataset, dh.equal_depth_weights(), "equal_depth")
    cr_obs_w = dh.compute_weighted_contrast(cr_result, cr_dataset, dh.observation_count_weights(cr_dataset), "observation_count")
    diagnostics[label]["cluster_robust_weighted"] = [cr_eq_w, cr_obs_w]

    # --- F. Include-zero sensitivity (original only) ---
    if include_zero:
        iz_dataset = dh.build_include_zero_dataset(eo)
        fit_f = dh._fit_with_warning_capture(dh.CATEGORICAL_FORMULA, iz_dataset, "y")
        diagnostics[label]["include_zero_model"] = model_summary_row(fit_f, dh.CATEGORICAL_FORMULA)
        raw_f = fit_f.result.raw_result
        contrasts_f = dh.compute_depth_contrasts(raw_f, iz_dataset, eo)
        results["include_zero_depth_contrasts"] = contrasts_f
        omnibus_f = dh.compute_omnibus_test(raw_f)
        diagnostics[label]["include_zero_omnibus"] = omnibus_f
        iz_eq_w = dh.compute_weighted_contrast(raw_f, iz_dataset, dh.equal_depth_weights(), "equal_depth")
        iz_obs_w = dh.compute_weighted_contrast(raw_f, iz_dataset, dh.observation_count_weights(iz_dataset), "observation_count")
        diagnostics[label]["include_zero_weighted"] = [iz_eq_w, iz_obs_w]

    diagnostics[label]["input_sha256"] = input_hash
    diagnostics[label]["eligible_n_obs"] = int(len(eligible))
    diagnostics[label]["total_cells"] = int(len(eo))
    diagnostics[label]["zero_variance_excluded"] = int(eo["zero_variance_flag"].sum())

    for name, frame in results.items():
        frame.to_csv(out_dir / f"{label}_{name}.csv", index=False)

    return results


def build_comparison_table(original_results: dict, replication_results: dict) -> pd.DataFrame:
    orig = original_results["depth_contrasts"].set_index("depth")
    repl = replication_results["depth_contrasts"].set_index("depth")
    rows = []
    for d in dh.DEPTHS:
        o, r = orig.loc[d], repl.loc[d]
        diff = r["estimate"] - o["estimate"]
        se_diff = float(np.sqrt(o["se"] ** 2 + r["se"] ** 2))
        ci_lo, ci_hi = diff - dh.Z975 * se_diff, diff + dh.Z975 * se_diff
        same_sign = (o["estimate"] > 0) == (r["estimate"] > 0)
        overlap = not (r["ci95_hi"] < o["ci95_lo"] or r["ci95_lo"] > o["ci95_hi"])
        rows.append({
            "depth": d,
            "original_estimate": o["estimate"], "original_ci95_lo": o["ci95_lo"], "original_ci95_hi": o["ci95_hi"],
            "replication_estimate": r["estimate"], "replication_ci95_lo": r["ci95_lo"], "replication_ci95_hi": r["ci95_hi"],
            "difference": diff, "se_difference_independent_approx": se_diff,
            "difference_ci95_lo": ci_lo, "difference_ci95_hi": ci_hi,
            "same_sign": bool(same_sign), "interval_overlap": bool(overlap),
            "original_n_zero_variance": int(o["n_zero_variance"]), "replication_n_zero_variance": int(r["n_zero_variance"]),
            "label": "post-run approximate comparison, not a confirmatory test",
        })
    return pd.DataFrame(rows)


def classify_depth_pattern(comparison: pd.DataFrame) -> str:
    n_agree = int((comparison["same_sign"] & comparison["interval_overlap"]).sum())
    if n_agree >= 4:
        return f"original and replication depth patterns agree ({n_agree}/5 depths same-sign and overlapping)"
    elif n_agree >= 1:
        return f"original and replication depth patterns partially agree ({n_agree}/5 depths same-sign and overlapping)"
    else:
        return "original and replication depth patterns disagree (0/5 depths same-sign and overlapping)"


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dataset", choices=["original", "replication", "both"], default="both")
    parser.add_argument("--resume", action="store_true")
    parser.add_argument("--output-root", default=None)
    args = parser.parse_args()

    diagnostics_path = ORIGINAL_OUT / "model_diagnostics.json"
    if diagnostics_path.exists():
        diagnostics: dict = json.loads(diagnostics_path.read_text())
    else:
        diagnostics = {}
    diagnostics["git_commit"] = git_commit()
    diagnostics["package_versions"] = package_versions()

    original_out = Path(args.output_root) / "original" if args.output_root else ORIGINAL_OUT
    replication_out = Path(args.output_root) / "replication" if args.output_root else REPLICATION_OUT

    original_results = None
    replication_results = None

    def load_from_disk(label: str, out_dir: Path) -> dict:
        return {
            "depth_contrasts": pd.read_csv(out_dir / f"{label}_depth_contrasts.csv"),
            "omnibus_tests": pd.read_csv(out_dir / f"{label}_omnibus_tests.csv"),
            "weighted_contrasts": pd.read_csv(out_dir / f"{label}_weighted_contrasts.csv"),
        }

    if args.dataset in ("original", "both"):
        marker = original_out / "original_omnibus_tests.csv"
        if args.resume and marker.exists():
            print(f"[original] already complete (resume), loading from disk")
            original_results = load_from_disk("original", original_out)
        else:
            print("[original] running...")
            original_results = run_one_dataset("original", ORIGINAL_POINTWISE, original_out,
                                                include_zero=True, diagnostics=diagnostics)
            print("[original] done")

    if args.dataset in ("replication", "both"):
        marker = replication_out / "replication_omnibus_tests.csv"
        if args.resume and marker.exists():
            print(f"[replication] already complete (resume), loading from disk")
            replication_results = load_from_disk("replication", replication_out)
        else:
            print("[replication] running...")
            replication_results = run_one_dataset("replication", REPLICATION_POINTWISE, replication_out,
                                                   include_zero=False, diagnostics=diagnostics)
            print("[replication] done")

    if args.dataset == "both" and original_results is not None and replication_results is not None:
        comparison = build_comparison_table(original_results, replication_results)
        comparison.to_csv(ORIGINAL_OUT / "original_vs_replication_depth.csv", index=False)
        pattern_classification = classify_depth_pattern(comparison)
        print(f"\nDepth pattern classification: {pattern_classification}")

        # --- master summary CSV + JSON ---
        summary_rows = []
        for d in dh.DEPTHS:
            o = comparison[comparison["depth"] == d].iloc[0]
            summary_rows.append({
                "depth": d, "original_estimate": o["original_estimate"],
                "original_ci_excludes_zero": bool(o["original_ci95_lo"] > 0 or o["original_ci95_hi"] < 0),
                "replication_estimate": o["replication_estimate"],
                "replication_ci_excludes_zero": bool(o["replication_ci95_lo"] > 0 or o["replication_ci95_hi"] < 0),
                "same_sign": o["same_sign"], "interval_overlap": o["interval_overlap"],
            })
        summary_df = pd.DataFrame(summary_rows)
        summary_df.to_csv(ORIGINAL_OUT / "h2_depth_heterogeneity_summary.csv", index=False)

        omnibus_orig = original_results["omnibus_tests"].iloc[0].to_dict()
        omnibus_repl = replication_results["omnibus_tests"].iloc[0].to_dict()
        summary_json = {
            "depth_pattern_classification": pattern_classification,
            "n_depths_agreeing": int((comparison["same_sign"] & comparison["interval_overlap"]).sum()),
            "original_omnibus": omnibus_orig,
            "replication_omnibus": omnibus_repl,
            "original_weighted_contrasts": original_results["weighted_contrasts"].to_dict("records"),
            "replication_weighted_contrasts": replication_results["weighted_contrasts"].to_dict("records"),
            "d2_reversal": {
                "original_depth2_estimate": float(comparison[comparison["depth"] == 2]["original_estimate"].iloc[0]),
                "original_depth2_ci_excludes_zero_negative": bool(
                    original_results["depth_contrasts"].set_index("depth").loc[2, "ci95_hi"] < 0
                ),
            },
        }
        (ORIGINAL_OUT / "h2_depth_heterogeneity_summary.json").write_text(
            json.dumps(summary_json, indent=2, default=str), encoding="utf-8"
        )

    (ORIGINAL_OUT / "model_diagnostics.json").write_text(
        json.dumps(diagnostics, indent=2, default=str), encoding="utf-8"
    )
    print(f"\nwrote diagnostics to {ORIGINAL_OUT / 'model_diagnostics.json'}")


if __name__ == "__main__":
    main()
