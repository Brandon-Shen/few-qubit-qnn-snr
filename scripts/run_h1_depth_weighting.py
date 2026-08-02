"""Run the frozen post-primary H1 depth heterogeneity/weighting analysis."""
from __future__ import annotations

import json
import platform
import subprocess
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import scipy
import statsmodels

from qnn_snr.stats.h1_depth_weighting import (
    CATEGORICAL_FORMULA, DEPTHS, Z975, build_validated_h1, cluster_robust_analysis,
    equal_weights, fit_categorical_mixed, moderation_test, observation_weights,
    parameter_weights, sha256, summarize_contrasts, weighted_summary,
)

ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / "results/h1_depth_weighting"
PLAN_COMMIT = "d528566acb2488380b5efd42d91b9e81fc739aaf"
INPUTS = {
    "original": ROOT / "results/production_confirmatory/raw/exact.parquet",
    "independent_seed": ROOT / "results/h2_replication_v1/_pipeline_output_stage1/raw/exact.parquet",
}


def dump(path: Path, value) -> None:
    path.write_text(json.dumps(value, indent=2, default=float) + "\n", encoding="utf-8", newline="\n")


def model_meta(bundle, raw) -> dict:
    r = bundle.result
    return {"formula": CATEGORICAL_FORMULA, "n_obs": r.n_obs, "n_groups": r.n_groups,
            "n_vc_levels": r.n_vc_levels, "design_columns": list(raw.model.exog_names),
            "design_rank": int(np.linalg.matrix_rank(raw.model.exog)),
            "design_n_columns": int(raw.model.exog.shape[1]), "condition_number": r.condition_number,
            "optimizer_attempts": r.attempted_optimizers, "adopted_optimizer": r.optimizer_used,
            "converged": r.converged, "singular": r.singular_fit,
            "random_effect_variances": r.random_effect_variances, "residual_variance": float(raw.scale),
            "reml_log_likelihood": float(raw.llf), "warnings": bundle.warnings,
            "software": {"python": platform.python_version(), "numpy": np.__version__, "pandas": pd.__version__,
                         "scipy": scipy.__version__, "statsmodels": statsmodels.__version__}}


def run_one(label: str, path: Path) -> dict:
    out = BASE / label
    out.mkdir(parents=True, exist_ok=False)
    exact = pd.read_parquet(path)
    data, validation = build_validated_h1(exact, label)
    validation["input_path"] = str(path.relative_to(ROOT)).replace("\\", "/")
    validation["input_sha256"] = sha256(path)
    data.to_parquet(out / "validated_h1_table.parquet", index=False)
    dump(out / "validation.json", validation)
    bundle = fit_categorical_mixed(data)
    if bundle.result.error or not bundle.result.converged:
        raise RuntimeError(f"{label} mixed fit failed: {bundle.result.error}")
    raw = bundle.result.raw_result
    meta = model_meta(bundle, raw)
    if meta["design_rank"] != meta["design_n_columns"]:
        raise RuntimeError(f"{label} categorical design is rank deficient: {meta}")
    dump(out / "model_metadata.json", meta)
    pd.DataFrame({"coefficient": raw.fe_params.index, "estimate": raw.fe_params.values,
                  "se": raw.bse_fe.values}).to_csv(out / "model_coefficients.csv", index=False)
    depth, matrix, cov = summarize_contrasts(raw, data)
    depth.to_csv(out / "depth_contrasts.csv", index=False)
    matrix.to_csv(out / "contrast_matrix.csv")
    cov.to_csv(out / "contrast_covariance.csv")
    schemes = {"equal_depth": equal_weights(), "observation_weighted": observation_weights(data),
               "parameter_weighted": parameter_weights(data)}
    dump(out / "weighting_definitions.json", {k: {str(d): v for d, v in w.items()} for k, w in schemes.items()})
    weighted = pd.DataFrame([weighted_summary(depth, cov, w, k) for k, w in schemes.items()])
    weighted.to_csv(out / "weighted_summaries.csv", index=False)
    robust_depth, robust_joint, robust_meta = cluster_robust_analysis(data)
    robust_depth.to_csv(out / "cluster_robust_depth_contrasts.csv", index=False)
    dump(out / "moderation_tests.json", {"mixed_model": moderation_test(raw),
                                         "cluster_robust_ols": robust_joint,
                                         "cluster_robust_metadata": robust_meta,
                                         "max_abs_mixed_ols_contrast_difference": float(np.max(np.abs(depth.estimate-robust_depth.estimate)))})
    return {"data": data, "depth": depth, "cov": cov, "weighted": weighted,
            "model_meta": meta, "validation": validation,
            "moderation": json.loads((out / "moderation_tests.json").read_text())}


def difference_rows(a: pd.DataFrame, b: pd.DataFrame, key: str) -> pd.DataFrame:
    x = a.merge(b, on=key, suffixes=("_original", "_seed"))
    x["difference_seed_minus_original"] = x.estimate_seed - x.estimate_original
    x["difference_se"] = np.sqrt(x.se_seed**2 + x.se_original**2)
    x["difference_ci_lo"] = x.difference_seed_minus_original - Z975*x.difference_se
    x["difference_ci_hi"] = x.difference_seed_minus_original + Z975*x.difference_se
    x["difference_p_raw"] = 2*scipy.stats.norm.sf(abs(x.difference_seed_minus_original/x.difference_se))
    return x


def figures(depth_diff: pd.DataFrame, weighting_source: pd.DataFrame, out: Path) -> None:
    depth_diff.to_csv(out / "figure_a_depth_source.csv", index=False)
    fig, ax = plt.subplots(figsize=(5.5, 3.2))
    for suffix, marker, ls, offset, label in [("original","o","-",-0.06,"Original"),("seed","s","--",0.06,"Independent seed")]:
        x=np.arange(5)+offset; est=depth_diff[f"estimate_{suffix}"]; lo=depth_diff[f"ci_lo_{suffix}"]; hi=depth_diff[f"ci_hi_{suffix}"]
        ax.errorbar(x,est,yerr=[est-lo,hi-est],fmt=marker,linestyle=ls,capsize=3,label=label)
    ax.axhline(0,color="0.45",lw=.8); ax.set_xticks(range(5),DEPTHS); ax.set_xlabel("Block count D")
    ax.set_ylabel(r"Centered $E\times L$ contrast in $\mathrm{asinh}(|g_{exact}|)$")
    ax.legend(frameon=False); fig.tight_layout(); fig.savefig(out/"figure_a_depth.pdf"); fig.savefig(out/"figure_a_depth.png",dpi=200); plt.close(fig)
    weighting_source.to_csv(out / "figure_b_weighting_source.csv", index=False)
    fig, ax = plt.subplots(figsize=(6.0, 3.3)); labels=list(weighting_source.estimand.unique()); y=np.arange(len(labels)); off={"original":-.1,"independent_seed":.1}
    for dataset,marker,ls in [("original","o","-"),("independent_seed","s","--")]:
        z=weighting_source[weighting_source.dataset==dataset].set_index("estimand").loc[labels]
        ax.errorbar(z.estimate,y+off[dataset],xerr=[z.estimate-z.ci_lo,z.ci_hi-z.estimate],fmt=marker,linestyle=ls,capsize=3,label=dataset.replace('_',' '))
    ax.axvline(0,color="0.45",lw=.8); ax.set_yticks(y,labels); ax.set_xlabel(r"Centered $E\times L$ estimate in $\mathrm{asinh}(|g_{exact}|)$")
    ax.legend(frameon=False); fig.tight_layout(); fig.savefig(out/"figure_b_weighting.pdf"); fig.savefig(out/"figure_b_weighting.png",dpi=200); plt.close(fig)


def main() -> None:
    if BASE.exists():
        raise FileExistsError(f"refusing to overwrite {BASE}")
    results = {label: run_one(label, path) for label, path in INPUTS.items()}
    if set(results["original"]["data"].initialization_seed) & set(results["independent_seed"]["data"].initialization_seed):
        raise RuntimeError("initialization seed overlap")
    comp = BASE / "comparison"; comp.mkdir()
    depth_diff = difference_rows(results["original"]["depth"], results["independent_seed"]["depth"], "depth")
    obs_w = results["original"]["weighted"].set_index("estimand").loc["observation_weighted", [f"weight_D{d}" for d in DEPTHS]].to_numpy()
    delta = depth_diff.difference_seed_minus_original.to_numpy()
    contributions = obs_w*delta
    depth_diff["observation_weighted_difference_contribution"] = contributions
    depth_diff["absolute_contribution_fraction"] = np.abs(contributions)/np.abs(contributions).sum()
    depth_diff.to_csv(comp / "depth_comparisons.csv", index=False)
    weighted_diff = difference_rows(results["original"]["weighted"], results["independent_seed"]["weighted"], "estimand")
    weighted_diff.to_csv(comp / "weighted_comparisons.csv", index=False)
    orig_primary = pd.read_csv(ROOT/"results/primary_corrected/effect_coded/corrected_confirmatory_hypotheses.csv").query("hypothesis == 'H1'").iloc[0]
    seed_primary = json.loads((ROOT/"results/independent_seed_h1/effect_coded/coefficient.json").read_text())
    pooled = pd.DataFrame([
        {"dataset":"original","estimand":"adopted_pooled","estimate":orig_primary.corrected_estimate,"se":orig_primary.corrected_standard_error,"ci_lo":orig_primary.corrected_ci_lo,"ci_hi":orig_primary.corrected_ci_hi},
        {"dataset":"independent_seed","estimand":"adopted_pooled","estimate":seed_primary["estimate"],"se":seed_primary["standard_error"],"ci_lo":seed_primary["wald_ci_lo"],"ci_hi":seed_primary["wald_ci_hi"]},
    ])
    pooled.to_csv(comp/"adopted_pooled.csv",index=False)
    pooled_diff=difference_rows(pooled.iloc[[0]].drop(columns="dataset"),pooled.iloc[[1]].drop(columns="dataset"),"estimand"); pooled_diff.to_csv(comp/"adopted_pooled_difference.csv",index=False)
    source=pd.concat([results[k]["weighted"].assign(dataset=k) for k in results],ignore_index=True)
    source=pd.concat([source,pooled],ignore_index=True)
    figures(depth_diff,source,comp)
    dump(comp/"figure_metadata.json",{"commands":["python scripts/run_h1_depth_weighting.py"],"formats":["PDF","PNG"],"source_csvs":["figure_a_depth_source.csv","figure_b_weighting_source.csv"],"relies_on_color_alone":False})
    manifest={"plan_commit":PLAN_COMMIT,"analysis_commit":None,"input_sha256":{k:sha256(v) for k,v in INPUTS.items()},"dataset_pooling":False,"initialization_seed_overlap":[],"command":"python scripts/run_h1_depth_weighting.py","protected_fig0_sha256_expected":"f89ccd263f2ea2e3fb92aed4677d0e32292851eda316244d014ccd49342a9a11","code_head":subprocess.check_output(["git","rev-parse","HEAD"],cwd=ROOT,text=True).strip()}
    dump(comp/"provenance.json",manifest)


if __name__ == "__main__": main()
