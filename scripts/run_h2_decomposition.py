"""H2 robustness package, Phase 3: decompose SNR_est = |mean| / SD into its
numerator (gradient-mean magnitude) and denominator (repeated-shot
variance/SD) components, to determine which part of the ratio produces the
E x L interaction.

Per verification/h2_robustness_replication_plan.md Section 2.1. Diagnostic
/ mechanism-explaining only -- does not replace the SNR_est estimand or the
adopted H2 result. Reads only from results/production_confirmatory/;
writes only to results/h2_robustness/decomposition/.

Run from the repo root: python scripts/run_h2_decomposition.py
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

from qnn_snr.stats.models import H2_H4_FORMULA, fit_mixed_model  # noqa: E402

PROD_DIR = REPO_ROOT / "results" / "production_confirmatory"
OUT_DIR = REPO_ROOT / "results" / "h2_robustness" / "decomposition"
Z975 = 1.959963984540054
TARGET_COEFS = ("E:L", "E:R", "L:R:depth_z")


def wald_rows(fit_result, model_name: str, response: str, zero_treatment: str, role: str) -> list[dict]:
    rows = []
    for coef in TARGET_COEFS:
        est = fit_result.params[coef]
        se = fit_result.bse[coef]
        rows.append({
            "model": model_name,
            "response_transform": response,
            "coefficient": coef,
            "estimate": est,
            "se": se,
            "ci95_lo": est - Z975 * se,
            "ci95_hi": est + Z975 * se,
            "direction": "positive" if est > 0 else ("negative" if est < 0 else "zero"),
            "n_obs": fit_result.n_obs,
            "converged": fit_result.converged,
            "singular_fit": fit_result.singular_fit,
            "zero_value_treatment": zero_treatment,
            "role": role,
        })
    return rows


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    pw = pd.read_parquet(PROD_DIR / "pointwise_gradient_statistics.parquet")
    eo = pw[pw["analysis_mode"] == "finite_shot_end_to_end"].copy()

    # Same eligible row set as the adopted SNR model (shot_variance > 0),
    # so the three models below are directly comparable on n_obs.
    eligible = eo[~eo["zero_variance_flag"]].copy()
    assert len(eligible) == 101_891, f"unexpected eligible row count: {len(eligible)}"

    all_rows: list[dict] = []

    # --- Reference: the adopted SNR_est model itself (not refit here beyond
    # reuse -- included in this table purely so the summary is self-contained). ---
    snr_df = eligible.copy()
    snr_df["y"] = np.arcsinh(snr_df["SNR_est"])
    snr_fit = fit_mixed_model(H2_H4_FORMULA, snr_df, "y")
    all_rows += wald_rows(
        snr_fit, "SNR_est (reference, not refit)", "arcsinh(SNR_est)",
        "excluded (ratio undefined/infinite when shot_variance==0)", "reference",
    )

    # --- Primary numerator model: asinh(|mu_hat|) ---
    # asinh is defined at 0, so no additional row need be excluded here beyond
    # matching the SNR model's eligible set for direct comparability.
    num_df = eligible.copy()
    num_df["y"] = np.arcsinh(np.abs(num_df["mu_hat"]))
    num_fit = fit_mixed_model(H2_H4_FORMULA, num_df, "y")
    all_rows += wald_rows(
        num_fit, "numerator (gradient-mean magnitude)", "arcsinh(|mu_hat|)",
        "none required (asinh defined at 0; eligible set matched to SNR model for comparability)",
        "primary",
    )

    # --- Primary denominator model: log(shot_sd), shot_sd > 0 by construction
    # of `eligible` (zero_variance_flag excluded), so log is always defined here. ---
    den_df = eligible.copy()
    assert (den_df["shot_sd"] > 0).all()
    den_df["y"] = np.log(den_df["shot_sd"])
    den_fit = fit_mixed_model(H2_H4_FORMULA, den_df, "y")
    all_rows += wald_rows(
        den_fit, "denominator (repeated-shot SD)", "log(shot_sd)",
        "excluded shot_variance==0 (log undefined) -- identical exclusion set as the SNR model",
        "primary",
    )

    summary = pd.DataFrame(all_rows)
    summary.to_csv(OUT_DIR / "h2_decomposition_summary.csv", index=False)

    # --- Descriptive-only outcomes (not modeled with MixedLM; binary/skewed) ---
    desc_rows = []
    for (e, l), g in eligible.groupby(["E", "L"]):
        desc_rows.append({
            "E": e, "L": l,
            "n_cells": len(g),
            "mean_abs_bias": g["absolute_bias"].mean(),
            "median_abs_bias": g["absolute_bias"].median(),
            "sign_agreement_rate": g["sign_agreement"].mean(),
            "mean_SNR_exact": g["SNR_exact"].replace([np.inf, -np.inf], np.nan).mean(),
        })
    desc_df = pd.DataFrame(desc_rows).sort_values(["E", "L"])
    desc_df.to_csv(OUT_DIR / "h2_descriptive_bias_sign_by_EL.csv", index=False)

    # --- Interpretation (fixed rule from the plan, computed mechanically) ---
    el_row_num = summary[(summary["model"].str.startswith("numerator")) & (summary["coefficient"] == "E:L")].iloc[0]
    el_row_den = summary[(summary["model"].str.startswith("denominator")) & (summary["coefficient"] == "E:L")].iloc[0]
    num_distinguishable = not (el_row_num["ci95_lo"] <= 0 <= el_row_num["ci95_hi"])
    den_distinguishable = not (el_row_den["ci95_lo"] <= 0 <= el_row_den["ci95_hi"])
    if num_distinguishable and den_distinguishable:
        driver = "both numerator and denominator show an E:L effect distinguishable from zero at alpha=0.05 (unadjusted, diagnostic)"
    elif num_distinguishable:
        driver = "numerator (gradient-mean magnitude) shows an E:L effect distinguishable from zero; denominator does not, at this sample size"
    elif den_distinguishable:
        driver = "denominator (repeated-shot SD) shows an E:L effect distinguishable from zero; numerator does not, at this sample size"
    else:
        driver = "neither component individually shows an E:L effect distinguishable from zero at alpha=0.05, despite the SNR ratio itself doing so -- consistent with the interaction arising from the numerator/denominator relationship rather than either marginal component alone"

    md = [
        "# H2 decomposition: numerator vs. denominator (Phase 3, diagnostic only)",
        "",
        "Diagnostic / mechanism-explaining only. Does not replace the SNR_est",
        "estimand or the adopted H2 result.",
        "",
        f"Eligible rows (matched to the adopted SNR model): **{len(eligible)}**",
        "",
        "## E:L coefficient by model",
        "",
        "| model | response | estimate | 95% CI | n_obs |",
        "|---|---|---:|---|---:|",
    ]
    for _, r in summary[summary["coefficient"] == "E:L"].iterrows():
        md.append(f"| {r['model']} | {r['response_transform']} | {r['estimate']:.6f} | "
                   f"[{r['ci95_lo']:.6f}, {r['ci95_hi']:.6f}] | {r['n_obs']} |")
    md += [
        "",
        f"**Interpretation (fixed rule, computed mechanically, not selected post hoc):** {driver}",
        "",
        "## Descriptive bias / sign-agreement by (E, L) [not a fitted model]",
        "",
        "| E | L | n_cells | mean abs bias | median abs bias | sign agreement rate | mean SNR_exact |",
        "|---|---|---:|---:|---:|---:|---:|",
    ]
    for _, r in desc_df.iterrows():
        md.append(f"| {int(r['E'])} | {int(r['L'])} | {int(r['n_cells'])} | {r['mean_abs_bias']:.6f} | "
                   f"{r['median_abs_bias']:.6f} | {r['sign_agreement_rate']:.4f} | {r['mean_SNR_exact']:.4f} |")
    (OUT_DIR / "h2_decomposition_summary.md").write_text("\n".join(md), encoding="utf-8")

    print(f"wrote {OUT_DIR}")
    print(driver)


if __name__ == "__main__":
    main()
