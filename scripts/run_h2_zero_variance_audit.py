"""H2 robustness package, Phase 2: exact reproduction of the zero-variance
exclusion issue and the current H2 result, from frozen production inputs
only.

Per verification/h2_robustness_replication_plan.md Section 1.5-1.6. This
script never writes to results/production_confirmatory/,
results/production_corrected_end_to_end/, or results/superseded_pooled/ --
it only *reads* those frozen files and writes new, separate outputs under
results/h2_robustness/original_data_audit/.

Run from the repo root: python scripts/run_h2_zero_variance_audit.py
"""
from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from scipy import stats

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

from qnn_snr.stats.models import H2_H4_FORMULA, build_h2h4_dataset, fit_h2h4_model  # noqa: E402

PROD_DIR = REPO_ROOT / "results" / "production_confirmatory"
CORRECTED_E2E_DIR = REPO_ROOT / "results" / "production_corrected_end_to_end"
OUT_DIR = REPO_ROOT / "results" / "h2_robustness" / "original_data_audit"
CONFIRMATORY_MODE = "finite_shot_end_to_end"
DIAGNOSTIC_MODE = "finite_shot_conditional"

CONFIG_ELR = {
    1: (0, 0, 0), 2: (1, 0, 0), 3: (0, 1, 0), 4: (0, 0, 1),
    5: (1, 1, 0), 6: (1, 0, 1), 7: (0, 1, 1), 8: (1, 1, 1),
}


def sha256_of(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def git_commit() -> str:
    return subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=REPO_ROOT).decode().strip()


def df_to_md(df: pd.DataFrame) -> str:
    """Minimal Markdown table formatter (no `tabulate` dependency)."""
    cols = list(df.columns)
    header = "| " + " | ".join(str(c) for c in cols) + " |"
    sep = "| " + " | ".join("---" for _ in cols) + " |"
    rows = []
    for _, row in df.iterrows():
        rows.append("| " + " | ".join(str(row[c]) for c in cols) + " |")
    return "\n".join([header, sep] + rows)


def marginal_table(df: pd.DataFrame, group_cols: list[str]) -> pd.DataFrame:
    g = df.groupby(group_cols, dropna=False)["zero_variance_flag"].agg(
        total="count", excluded="sum").reset_index()
    g["pct_excluded"] = 100.0 * g["excluded"] / g["total"]
    return g


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    # --- Provenance: hash every input this script reads, before reading it as data ---
    input_files = {
        "pointwise": PROD_DIR / "pointwise_gradient_statistics.parquet",
        "raw_exact": PROD_DIR / "raw" / "exact.parquet",
        "raw_end_to_end": PROD_DIR / "raw" / "finite_shot_end_to_end.parquet",
        "raw_conditional": PROD_DIR / "raw" / "finite_shot_conditional.parquet",
    }
    input_hashes = {name: sha256_of(p) for name, p in input_files.items()}

    pw = pd.read_parquet(input_files["pointwise"])

    # --- 1. Total pointwise cells by estimator mode ---
    by_mode = pw.groupby("analysis_mode").size().rename("n_cells").reset_index()
    by_mode_zv = pw.groupby("analysis_mode")["zero_variance_flag"].agg(
        total="count", excluded="sum").reset_index()
    by_mode_zv["pct_excluded"] = 100.0 * by_mode_zv["excluded"] / by_mode_zv["total"]

    eo = pw[pw["analysis_mode"] == CONFIRMATORY_MODE].copy()
    cond = pw[pw["analysis_mode"] == DIAGNOSTIC_MODE].copy()

    # --- 2. Zero-variance counts/percentages by every requested factor, end-to-end mode ---
    marg_E = marginal_table(eo, ["E"])
    marg_L = marginal_table(eo, ["L"])
    marg_R = marginal_table(eo, ["R"])
    marg_D = marginal_table(eo, ["depth"])
    marg_B = marginal_table(eo, ["budget"])
    marg_init = marginal_table(eo, ["initialization_id"])
    marg_param = marginal_table(eo, ["parameter_id"])
    marg_full = marginal_table(eo, ["configuration_id", "E", "L", "R", "depth", "budget"])

    marg_E.to_csv(OUT_DIR / "zero_variance_by_E.csv", index=False)
    marg_L.to_csv(OUT_DIR / "zero_variance_by_L.csv", index=False)
    marg_R.to_csv(OUT_DIR / "zero_variance_by_R.csv", index=False)
    marg_D.to_csv(OUT_DIR / "zero_variance_by_depth.csv", index=False)
    marg_B.to_csv(OUT_DIR / "zero_variance_by_budget.csv", index=False)
    marg_init.to_csv(OUT_DIR / "zero_variance_by_initialization.csv", index=False)
    marg_param.to_csv(OUT_DIR / "zero_variance_by_parameter_id.csv", index=False)
    marg_full.to_csv(OUT_DIR / "zero_variance_by_full_factorial_cell.csv", index=False)

    # --- 3. Confirm exclusions are (or are not) confined to L=0 ---
    l0_excluded = int(eo.loc[eo["L"] == 0, "zero_variance_flag"].sum())
    l1_excluded = int(eo.loc[eo["L"] == 1, "zero_variance_flag"].sum())
    total_excluded = int(eo["zero_variance_flag"].sum())
    confined_to_L0 = bool(l1_excluded == 0 and l0_excluded == total_excluded)

    # --- 4. Non-finite SNR_est not explained by zero_variance_flag (must be 0) ---
    non_finite_unexplained = pw[(~np.isfinite(pw["SNR_est"])) & (~pw["zero_variance_flag"])]

    # --- 5. Reproduce the current H2 (and full H2-H4) coefficient/SE/p/CI exactly ---
    h2h4_dataset = build_h2h4_dataset(eo)  # single-mode, no pooling
    fit_result = fit_h2h4_model(eo)

    coef_rows = []
    for coef in ("E:L", "E:R", "L:R:depth_z"):
        est = fit_result.params[coef]
        se = fit_result.bse[coef]
        z = est / se
        p = 2 * (1 - stats.norm.cdf(abs(z)))
        ci_lo, ci_hi = est - 1.959963984540054 * se, est + 1.959963984540054 * se
        coef_rows.append({
            "coefficient": coef, "estimate": est, "se": se, "wald_z": z,
            "p_unadjusted": p, "ci95_lo": ci_lo, "ci95_hi": ci_hi,
        })
    coef_df = pd.DataFrame(coef_rows)
    coef_df.to_csv(OUT_DIR / "h2h4_wald_reproduction.csv", index=False)

    reproduced_beta_EL = fit_result.params["E:L"]
    ADOPTED_BETA_EL = 0.024995843985971582
    beta_EL_matches_adopted = bool(np.isclose(reproduced_beta_EL, ADOPTED_BETA_EL, atol=1e-9))

    # --- 6. Current bootstrap interval (read, not recomputed) ---
    boot_summary_path = CORRECTED_E2E_DIR / "bootstrap_end_to_end_h2_h4_summary.csv"
    boot_summary = pd.read_csv(boot_summary_path)

    # --- 7. Residual-scale diagnostics from the reproduced fit ---
    resid = np.asarray(fit_result.raw_result.resid)
    d_for_resid = eo.copy()
    d_for_resid = d_for_resid[np.isfinite(d_for_resid["SNR_est"])]
    d_for_resid["_resid"] = resid
    resid_by_depth = d_for_resid.groupby("depth")["_resid"].std(ddof=1).rename("resid_sd").reset_index()
    resid_by_budget = d_for_resid.groupby("budget")["_resid"].std(ddof=1).rename("resid_sd").reset_index()
    resid_by_depth.to_csv(OUT_DIR / "residual_sd_by_depth.csv", index=False)
    resid_by_budget.to_csv(OUT_DIR / "residual_sd_by_budget.csv", index=False)

    # --- Write consolidated machine-readable summary ---
    summary = {
        "generated_at_git_commit": git_commit(),
        "input_file_sha256": input_hashes,
        "total_cells_by_mode": by_mode.to_dict("records"),
        "zero_variance_by_mode": by_mode_zv.to_dict("records"),
        "end_to_end_total_cells": int(len(eo)),
        "end_to_end_zero_variance_excluded": total_excluded,
        "end_to_end_zero_variance_pct": 100.0 * total_excluded / len(eo),
        "confined_to_L0": confined_to_L0,
        "l0_excluded": l0_excluded,
        "l1_excluded": l1_excluded,
        "non_finite_snr_not_explained_by_zero_variance_flag": int(len(non_finite_unexplained)),
        "h2h4_model": {
            "formula": H2_H4_FORMULA,
            "n_obs": fit_result.n_obs,
            "n_groups": fit_result.n_groups,
            "converged": fit_result.converged,
            "optimizer_used": fit_result.optimizer_used,
            "singular_fit": fit_result.singular_fit,
            "reproduced_beta_EL": reproduced_beta_EL,
            "adopted_beta_EL": ADOPTED_BETA_EL,
            "beta_EL_matches_adopted_bit_for_bit": beta_EL_matches_adopted,
        },
        "wald_coefficients": coef_df.to_dict("records"),
        "bootstrap_summary_source": str(boot_summary_path.relative_to(REPO_ROOT)),
        "bootstrap_summary": boot_summary.to_dict("records"),
        "residual_sd_by_depth": resid_by_depth.to_dict("records"),
        "residual_sd_by_budget": resid_by_budget.to_dict("records"),
    }
    (OUT_DIR / "h2_audit_summary.json").write_text(json.dumps(summary, indent=2, default=str), encoding="utf-8")

    # --- Concise markdown record ---
    md_lines = [
        "# H2 zero-variance and current-result audit (Phase 2, original data only)",
        "",
        f"Reproduced at commit `{summary['generated_at_git_commit']}` from frozen inputs in "
        f"`results/production_confirmatory/` (hashes below). No original file was modified.",
        "",
        "## Input hashes",
        "",
    ]
    for name, h in input_hashes.items():
        md_lines.append(f"- `{name}`: `{h}`")
    md_lines += [
        "",
        "## Cell counts and zero-variance exclusion",
        "",
        f"- End-to-end total cells: **{len(eo)}**; excluded (zero variance): "
        f"**{total_excluded}** ({100.0*total_excluded/len(eo):.3f}%).",
        f"- Conditional total cells: **{len(cond)}**; excluded: "
        f"**{int(cond['zero_variance_flag'].sum())}** "
        f"({100.0*cond['zero_variance_flag'].sum()/len(cond):.3f}%).",
        f"- **Confined to L=0: {confined_to_L0}** (L=0 excluded={l0_excluded}, "
        f"L=1 excluded={l1_excluded}).",
        f"- Non-finite `SNR_est` rows not explained by `zero_variance_flag` "
        f"(should be 0): **{len(non_finite_unexplained)}**.",
        "",
        "## Reproduced H2-H4 Wald fit",
        "",
        f"- `n_obs`={fit_result.n_obs}, converged={fit_result.converged}, "
        f"optimizer={fit_result.optimizer_used}, singular_fit={fit_result.singular_fit}",
        f"- Reproduced `E:L` (H2): **{reproduced_beta_EL:.15f}** "
        f"(adopted: {ADOPTED_BETA_EL:.15f}, bit-for-bit match: {beta_EL_matches_adopted})",
        "",
        df_to_md(coef_df),
        "",
        "## Current bootstrap interval (read from "
        "`results/production_corrected_end_to_end/bootstrap_end_to_end_h2_h4_summary.csv`)",
        "",
        df_to_md(boot_summary),
        "",
        "## Residual SD by depth (reproduced fit)",
        "",
        df_to_md(resid_by_depth),
        "",
        "## Residual SD by budget (reproduced fit)",
        "",
        df_to_md(resid_by_budget),
        "",
    ]
    (OUT_DIR / "h2_audit_summary.md").write_text("\n".join(md_lines), encoding="utf-8")

    print(f"wrote {OUT_DIR}")
    print(f"confined_to_L0={confined_to_L0}, total_excluded={total_excluded}, "
          f"beta_EL_matches_adopted={beta_EL_matches_adopted}")


if __name__ == "__main__":
    main()
