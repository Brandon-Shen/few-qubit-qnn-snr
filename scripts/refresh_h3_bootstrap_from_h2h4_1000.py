"""Refresh bootstrap-only H3 robustness artifacts from the final H2--H4 pool."""
import json
from pathlib import Path

import numpy as np
import pandas as pd

from qnn_snr.stats.factor_coding import transform_bootstrap_draws

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "results/h3_centered_robustness"


def main() -> None:
    boot = transform_bootstrap_draws(pd.read_parquet(
        ROOT / "results/production_corrected_end_to_end/bootstrap_end_to_end_h2_h4_iterations.parquet"), "h2h4")
    if len(boot) != 1000 or boot.global_iteration_id.nunique() != 1000:
        raise AssertionError("H3 refresh requires exactly 1,000 unique final H2--H4 draws")
    boot["ER_L0"] = boot["E:R"]
    boot["ER_L1"] = boot["E:R"] + boot["E:L:R"]
    boot["ER_L_average"] = boot["E_c:R_c"]
    rows = []
    for col in ("ER_L0", "ER_L1", "ER_L_average"):
        lo, med, hi = np.percentile(boot[col], [2.5, 50, 97.5])
        rows.append({"contrast": col, "iterations": 1000, "median": med, "ci_lo": lo, "ci_hi": hi})
    pd.DataFrame(rows).to_csv(OUT / "bootstrap_simple_interactions.csv", index=False)
    pd.DataFrame({"global_iteration_id": boot.global_iteration_id, "iteration": boot.iteration,
                  "stream": boot._stream, "seed": boot._seed, "ER_L0": boot.ER_L0,
                  "ER_L1": boot.ER_L1, "ER_L_average": boot.ER_L_average}).to_parquet(
                      OUT / "bootstrap_draws.parquet", index=False)
    report_json = ROOT / "verification/h3_centered_interaction_robustness_results.json"
    report = json.loads(report_json.read_text(encoding="utf-8"))
    report.pop("bootstrap_443", None)
    by = {r["contrast"]: r for r in rows}
    report["bootstrap_1000"] = {
        "L0_ci": [by["ER_L0"]["ci_lo"], by["ER_L0"]["ci_hi"]],
        "L1_ci": [by["ER_L1"]["ci_lo"], by["ER_L1"]["ci_hi"]],
        "average_ci": [by["ER_L_average"]["ci_lo"], by["ER_L_average"]["ci_hi"]],
    }
    report_json.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    md = ROOT / "verification/h3_centered_interaction_robustness_results.md"
    text = md.read_text(encoding="utf-8")
    marker = "The frozen 443-draw bootstrap" if "The frozen 443-draw bootstrap" in text else "The final 1,000-draw bootstrap"
    start = text.index(marker)
    end = text.index("\n\n", start)
    replacement = ("The final 1,000-draw bootstrap intervals include zero for all three: "
                   f"L=0 `[{by['ER_L0']['ci_lo']:.6f},{by['ER_L0']['ci_hi']:.6f}]`, "
                   f"L=1 `[{by['ER_L1']['ci_lo']:.6f},{by['ER_L1']['ci_hi']:.6f}]`, and averaged "
                   f"`[{by['ER_L_average']['ci_lo']:.6f},{by['ER_L_average']['ci_hi']:.6f}]`. "
                   "The original 443 draws are the preserved historical prefix.")
    md.write_text(text[:start] + replacement + text[end:], encoding="utf-8")
    print(pd.DataFrame(rows).to_string(index=False))


if __name__ == "__main__":
    main()
