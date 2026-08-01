"""H2 robustness package, Phase 4 (E): leave-one-initialization-out
influence, extended to the numerator and denominator decomposition models
(Phase 3) so influence can be attributed to gradient-mean magnitude,
repeated-shot SD, or both -- not just to the SNR ratio.

Reuses verification/run_loo_initialization.py's existing SNR-model output
directly (does not recompute it) and adds two new leave-one-out sweeps for
the numerator (asinh|mu_hat|) and denominator (log shot_sd) models defined
in scripts/run_h2_decomposition.py. No initialization is removed from any
primary analysis; this only quantifies influence.

Run from the repo root: python scripts/run_h2_loo_extended.py
Resumable: checkpoints every iteration.
"""
from __future__ import annotations

import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd
from scipy import stats

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

from qnn_snr.stats.models import H2_H4_FORMULA, fit_mixed_model  # noqa: E402

PROD_DIR = REPO_ROOT / "results" / "production_confirmatory"
EXISTING_SNR_LOO = REPO_ROOT / "results" / "sensitivity_analyses" / "leave_one_initialization_out_coefficients.csv"
OUT_DIR = REPO_ROOT / "results" / "h2_robustness" / "robust_inference"
CHECKPOINT_DIR = OUT_DIR / "_loo_extended_checkpoints"
TARGET_COEF = "E:L"

# Original full-data reference values (from scripts/run_h2_decomposition.py),
# used to express LOO movement in original-SE units.
ORIGINAL = {
    "numerator": {"estimate": 0.004314692534638696, "se": 0.0006321487918104937},
    "denominator": {"estimate": -0.14986553030400301, "se": 0.012077763762833829},
}


def load_checkpoint(name: str) -> list[dict]:
    p = CHECKPOINT_DIR / f"{name}.parquet"
    if p.exists():
        return pd.read_parquet(p).to_dict("records")
    return []


def save_checkpoint(name: str, rows: list[dict]) -> None:
    CHECKPOINT_DIR.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(rows).to_parquet(CHECKPOINT_DIR / f"{name}.parquet", index=False)


def run_loo(df: pd.DataFrame, response_col_source: str, name: str) -> pd.DataFrame:
    init_ids = sorted(df["initialization_id"].unique())
    rows = load_checkpoint(name)
    done = {r["excluded_initialization_id"] for r in rows}
    print(f"[{name}] resuming: {len(done)}/{len(init_ids)} already completed", flush=True)

    for init_id in init_ids:
        if init_id in done:
            continue
        t0 = time.time()
        subset = df[df["initialization_id"] != init_id].copy()
        subset["y"] = subset[response_col_source]
        try:
            res = fit_mixed_model(H2_H4_FORMULA, subset, "y")
            dt = time.time() - t0
            est, se = res.params[TARGET_COEF], res.bse[TARGET_COEF]
            z = est / se
            p = 2 * (1 - stats.norm.cdf(abs(z)))
            row = {"excluded_initialization_id": int(init_id), "converged": res.converged,
                   "n_obs": res.n_obs, "wallclock_s": dt, "estimate": est, "se": se, "p": p}
        except Exception as exc:  # noqa: BLE001
            dt = time.time() - t0
            row = {"excluded_initialization_id": int(init_id), "converged": False,
                   "n_obs": len(subset), "wallclock_s": dt, "error": str(exc)}
        print(f"[{name}][init {init_id}] {row}", flush=True)
        rows.append(row)
        save_checkpoint(name, rows)

    return pd.DataFrame(rows).sort_values("excluded_initialization_id")


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    pw = pd.read_parquet(PROD_DIR / "pointwise_gradient_statistics.parquet")
    eo = pw[pw["analysis_mode"] == "finite_shot_end_to_end"].copy()
    eligible = eo[~eo["zero_variance_flag"]].copy()
    eligible["_num"] = np.arcsinh(np.abs(eligible["mu_hat"]))
    eligible["_den"] = np.log(eligible["shot_sd"])

    num_loo = run_loo(eligible, "_num", "numerator")
    num_loo.to_csv(OUT_DIR / "h2_loo_numerator.csv", index=False)

    den_loo = run_loo(eligible, "_den", "denominator")
    den_loo.to_csv(OUT_DIR / "h2_loo_denominator.csv", index=False)

    # --- Combine with the existing SNR-model LOO (not recomputed) into one influence table ---
    if EXISTING_SNR_LOO.exists():
        snr_loo = pd.read_csv(EXISTING_SNR_LOO)
        combined = []
        for init_id in sorted(eligible["initialization_id"].unique()):
            snr_row = snr_loo[snr_loo["excluded_initialization_id"] == init_id]
            num_row = num_loo[num_loo["excluded_initialization_id"] == init_id]
            den_row = den_loo[den_loo["excluded_initialization_id"] == init_id]
            rec = {"excluded_initialization_id": init_id}
            if len(snr_row):
                rec["snr_E_L_estimate"] = snr_row["E:L_estimate"].iloc[0]
            if len(num_row):
                num_est = num_row["estimate"].iloc[0]
                rec["numerator_E_L_estimate"] = num_est
                rec["numerator_delta_original_se_units"] = (
                    (num_est - ORIGINAL["numerator"]["estimate"]) / ORIGINAL["numerator"]["se"]
                )
            if len(den_row):
                den_est = den_row["estimate"].iloc[0]
                rec["denominator_E_L_estimate"] = den_est
                rec["denominator_delta_original_se_units"] = (
                    (den_est - ORIGINAL["denominator"]["estimate"]) / ORIGINAL["denominator"]["se"]
                )
            combined.append(rec)
        combined_df = pd.DataFrame(combined)
        combined_df.to_csv(OUT_DIR / "h2_loo_combined_influence.csv", index=False)
        print(f"\nwrote combined influence table: {OUT_DIR / 'h2_loo_combined_influence.csv'}")
        print("Most influential initialization per component:")
        for col in ("numerator_delta_original_se_units", "denominator_delta_original_se_units"):
            if col in combined_df.columns:
                idx = combined_df[col].abs().idxmax()
                print(f"  {col}: init {combined_df.loc[idx, 'excluded_initialization_id']}, "
                      f"delta={combined_df.loc[idx, col]:.4f} original-SE units")
    else:
        print(f"WARNING: {EXISTING_SNR_LOO} not found -- combined table not written, "
              f"numerator/denominator LOO still written separately.")


if __name__ == "__main__":
    main()
