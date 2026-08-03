"""Finalize exactly 1,000 valid H2--H4 draws and generated manuscript rows."""
from __future__ import annotations

import json
import subprocess
from pathlib import Path

import numpy as np
import pandas as pd

from qnn_snr.stats.factor_coding import transform_bootstrap_draws

ROOT = Path(__file__).resolve().parents[1]
DIRECT = ROOT / "results/production_corrected_end_to_end/bootstrap_end_to_end_h2_h4_iterations.parquet"
OUT = ROOT / "results/primary_corrected/effect_coded"


def evidence(wald_reject: bool, wald_lo: float, wald_hi: float, boot_lo: float, boot_hi: float) -> str:
    wald_excludes = not (wald_lo <= 0 <= wald_hi)
    boot_excludes = not (boot_lo <= 0 <= boot_hi)
    if wald_reject and wald_excludes and boot_excludes:
        return "Both"
    if wald_reject and boot_lo <= 0 <= boot_hi:
        return "Wald only"
    if not wald_reject and boot_lo <= 0 <= boot_hi:
        return "Neither"
    return "Bootstrap only" if boot_excludes else "Discordant"


def main() -> None:
    subprocess.run(["python", "verification/summarize_bootstrap_checkpoints.py"], cwd=ROOT, check=True)
    direct = pd.read_parquet(DIRECT)
    if len(direct) != 1000 or direct["global_iteration_id"].nunique() != 1000:
        raise AssertionError("final H2--H4 input is not exactly 1,000 unique successful fits")
    centered = transform_bootstrap_draws(direct, "h2h4")
    centered.to_parquet(OUT / "h2h4_centered_bootstrap_1000_transformed.parquet", index=False)

    h1_meta = json.loads((OUT / "h1_centered_bootstrap_2000.meta.json").read_text())
    h1 = {"hypothesis": "H1", "coefficient": "E_c:L_c",
          "completed_bootstrap_iterations": h1_meta["completed_bootstrap_fits"],
          "percentile_ci_lo": h1_meta["percentile_interval"][0],
          "bootstrap_median": h1_meta["median"],
          "percentile_ci_hi": h1_meta["percentile_interval"][1]}
    rows = [h1]
    for hyp, coef in (("H2", "E_c:L_c"), ("H3", "E_c:R_c"), ("H4", "L_c:R_c:depth_z")):
        lo, med, hi = np.percentile(centered[coef], [2.5, 50, 97.5])
        rows.append({"hypothesis": hyp, "coefficient": coef, "completed_bootstrap_iterations": 1000,
                     "percentile_ci_lo": lo, "bootstrap_median": med, "percentile_ci_hi": hi})
    boot = pd.DataFrame(rows)
    boot.to_csv(OUT / "corrected_bootstrap_intervals_current_draws.csv", index=False)

    primary = pd.read_csv(OUT / "corrected_confirmatory_hypotheses.csv").set_index("hypothesis")
    labels = {"H1": (r"$E_cL_c$, exact"), "H2": (r"$E_cL_c$, end-to-end"),
              "H3": (r"$E_cR_c$, end-to-end"), "H4": (r"$L_cR_c\times$depth")}
    tex = []
    classifications = {}
    for b in boot.itertuples(index=False):
        p = primary.loc[b.hypothesis]
        label = evidence(bool(p.corrected_reject_after_holm), p.corrected_ci_lo, p.corrected_ci_hi,
                         b.percentile_ci_lo, b.percentile_ci_hi)
        classifications[b.hypothesis] = label
        tex += [f"{b.hypothesis} & {labels[b.hypothesis]}", f"   & {p.corrected_estimate:.6f}",
                f"   & \\mbox{{$[{p.corrected_ci_lo:.6f},\\,{p.corrected_ci_hi:.6f}]$}}",
                f"   & {p.corrected_p_holm:.6f}",
                f"   & \\mbox{{$[{b.percentile_ci_lo:.6f},\\,{b.percentile_ci_hi:.6f}]$}}",
                f"   & {label} \\\\"]
    (OUT / "primary_h1_h4_rows.tex").write_text("\n".join(tex) + "\n", encoding="utf-8")
    (OUT / "h2h4_bootstrap_1000_finalization.json").write_text(json.dumps({
        "successful_fits": 1000, "unique_global_iteration_ids": 1000,
        "classifications": classifications, "intervals": rows[1:],
    }, indent=2), encoding="utf-8")
    summary = pd.read_csv(ROOT / "results/production_corrected_end_to_end/bootstrap_end_to_end_h2_h4_summary.csv")
    audit = {
        "status": "final_revised_target_1000", "included_successful": 1000,
        "completed_successful_total": int(summary.n_attempted.iloc[0]),
        "successful_excluded_after_target_revision": int(summary.n_successful_excluded_after_target_revision.iloc[0]),
        "failed": int(summary.n_failed.iloc[0]), "rejected": int(summary.n_rejected.iloc[0]),
        "historical_prefix": 443, "intervals_and_mc_endpoint_uncertainty": summary.to_dict("records"),
        "scientific_design_changes": [],
        "command": "python scripts/finalize_h2h4_bootstrap_1000.py",
    }
    (ROOT / "verification/h2h4_bootstrap_1000_final.json").write_text(json.dumps(audit, indent=2), encoding="utf-8")
    md = ["# Final H2--H4 nested bootstrap", "", "**Status:** exactly 1,000 unique valid fits included under the revised stopping instruction.", "",
          f"Completed successfully before stop: {audit['completed_successful_total']}; included: 1,000; excluded post-target successes: {audit['successful_excluded_after_target_revision']}; failed: {audit['failed']}; rejected: {audit['rejected']}.", "",
          "The original 443 draws are unchanged and form the historical prefix. Excluded valid draws are retained under `results/superseded/h2h4_bootstrap_post_1000_excluded/`.", "",
          "Endpoint Monte Carlo intervals below are binomial/order-statistic rank intervals and are not scientific confidence intervals.", "", "```csv", summary.to_csv(index=False).strip(), "```", ""]
    (ROOT / "verification/h2h4_bootstrap_1000_final.md").write_text("\n".join(md), encoding="utf-8")
    print(boot.to_string(index=False)); print(classifications)


if __name__ == "__main__":
    main()
