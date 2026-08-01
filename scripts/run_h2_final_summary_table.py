"""H2 robustness/replication package, Phase 9: consolidated
machine-readable results table across every method run in this package.

Run from the repo root: python scripts/run_h2_final_summary_table.py
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pandas as pd

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

ROBUST_DIR = REPO_ROOT / "results" / "h2_robustness" / "robust_inference"
DECOMP_DIR = REPO_ROOT / "results" / "h2_robustness" / "decomposition"
REPL_DIR = REPO_ROOT / "results" / "h2_replication_v1" / "_pipeline_output_stage1"
OUT_PATH = REPO_ROOT / "results" / "h2_robustness" / "h2_final_summary_table.csv"


def main() -> None:
    rows = []

    # 1. Original prespecified Wald/Holm
    rows.append({
        "method": "prespecified Wald/Holm (mixed model)", "dataset": "original",
        "coefficient": "E:L", "estimate": 0.024995843985971582,
        "ci_lo": 0.010729243854496907, "ci_hi": 0.039262444117446255,
        "ci_excludes_zero": True, "n_obs": 101891, "category": "confirmatory (prespecified)",
    })

    # 2. Original nested bootstrap (n=443, existing production record)
    rows.append({
        "method": "nested percentile bootstrap (n=443)", "dataset": "original",
        "coefficient": "E:L", "estimate": 0.023685464808045162,
        "ci_lo": -0.018024348208322244, "ci_hi": 0.06568788799503045,
        "ci_excludes_zero": False, "n_obs": 101891, "category": "robustness",
    })

    # 3. Cluster-robust OLS
    cr = pd.read_csv(ROBUST_DIR / "h2_cluster_robust_ols.csv")
    r = cr[cr["coefficient"] == "E:L"].iloc[0]
    rows.append({
        "method": "cluster-robust OLS (initialization-level)", "dataset": "original",
        "coefficient": "E:L", "estimate": r["estimate"],
        "ci_lo": r["ci95_lo"], "ci_hi": r["ci95_hi"],
        "ci_excludes_zero": bool(r["ci95_lo"] > 0 or r["ci95_hi"] < 0),
        "n_obs": int(r["n_obs"]), "category": "robustness",
    })

    # 4. Initialization-level resampling (Phase 4B)
    init_summary = json.loads((ROBUST_DIR / "init_resample_summary.json").read_text())
    ci = init_summary["percentile_ci"]["E:L"]
    rows.append({
        "method": "initialization-level resampling (n=50, w/ zero-variance logging)", "dataset": "original",
        "coefficient": "E:L", "estimate": init_summary["median_E_L"],
        "ci_lo": ci[0], "ci_hi": ci[1],
        "ci_excludes_zero": bool(ci[0] > 0 or ci[1] < 0),
        "n_obs": None, "category": "robustness",
    })

    # 5. Depth-stratified (exploratory)
    depth = pd.read_csv(ROBUST_DIR / "h2_depth_stratified.csv")
    for _, dr in depth[depth["coefficient"] == "E:L"].iterrows():
        rows.append({
            "method": f"depth-stratified (D={int(dr['depth'])})", "dataset": "original",
            "coefficient": "E:L", "estimate": dr["estimate"],
            "ci_lo": dr["ci95_lo"], "ci_hi": dr["ci95_hi"],
            "ci_excludes_zero": bool(dr["ci95_lo"] > 0 or dr["ci95_hi"] < 0),
            "n_obs": int(dr["n_obs"]), "category": "exploratory",
        })

    # 6. Numerator/denominator decomposition (diagnostic)
    decomp = pd.read_csv(DECOMP_DIR / "h2_decomposition_summary.csv")
    for _, dr in decomp[decomp["coefficient"] == "E:L"].iterrows():
        rows.append({
            "method": f"decomposition: {dr['model']}", "dataset": "original",
            "coefficient": "E:L", "estimate": dr["estimate"],
            "ci_lo": dr["ci95_lo"], "ci_hi": dr["ci95_hi"],
            "ci_excludes_zero": bool(dr["ci95_lo"] > 0 or dr["ci95_hi"] < 0),
            "n_obs": int(dr["n_obs"]), "category": "diagnostic",
        })

    # 7. Zero-variance sensitivity (F.3), baseline + one representative nonzero floor
    floor = pd.read_csv(ROBUST_DIR / "h2_variance_floor_sensitivity_grid.csv")
    for _, fr in floor.iterrows():
        rows.append({
            "method": f"zero-variance sensitivity ({fr['treatment']})", "dataset": "original",
            "coefficient": "E:L", "estimate": fr["E:L_estimate"],
            "ci_lo": fr["E:L_ci95_lo"], "ci_hi": fr["E:L_ci95_hi"],
            "ci_excludes_zero": bool(fr["E:L_ci95_lo"] > 0 or fr["E:L_ci95_hi"] < 0)
            if pd.notna(fr["E:L_ci95_lo"]) else None,
            "n_obs": int(fr["n_obs"]), "category": "sensitivity",
        })

    # 8. Replication Wald
    repl_coef = pd.read_csv(REPL_DIR / "snr_model_coefficients.csv")
    rr = repl_coef[repl_coef["coefficient"] == "E:L"].iloc[0]
    Z975 = 1.959963984540054
    rows.append({
        "method": "prespecified Wald (mixed model)", "dataset": "replication (Stage 1, R_rep=30)",
        "coefficient": "E:L", "estimate": rr["estimate"],
        "ci_lo": rr["estimate"] - Z975 * rr["se"], "ci_hi": rr["estimate"] + Z975 * rr["se"],
        "ci_excludes_zero": bool(rr["estimate"] - Z975 * rr["se"] > 0),
        "n_obs": None, "category": "replication",
    })

    # 9. Replication bootstrap
    repl_boot = json.loads((REPL_DIR / "bootstrap_summary_tight_checkpoints.json").read_text())
    rb_ci = repl_boot["percentile_ci"]["H2"]
    rows.append({
        "method": "nested percentile bootstrap (n=30)", "dataset": "replication (Stage 1, R_rep=30)",
        "coefficient": "E:L", "estimate": None,
        "ci_lo": rb_ci[0], "ci_hi": rb_ci[1],
        "ci_excludes_zero": bool(rb_ci[0] > 0 or rb_ci[1] < 0),
        "n_obs": None, "category": "replication",
    })

    df = pd.DataFrame(rows)
    df.to_csv(OUT_PATH, index=False)
    print(df.to_string(index=False))
    print(f"\nwrote {OUT_PATH} ({len(df)} rows)")


if __name__ == "__main__":
    main()
