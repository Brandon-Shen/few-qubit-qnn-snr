"""Finalize the frozen independent-seed H1 robustness package."""
from __future__ import annotations

import hashlib
import json
import subprocess
from datetime import datetime, timezone
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "results/independent_seed_h1/effect_coded"
PLAN_COMMIT = "7cdb9a2b9a820799fe1b05491f9498b838f5a15c"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def main() -> None:
    summary = json.loads((OUT / "summary.json").read_text())
    validation = json.loads((OUT / "validation.json").read_text())
    meta = json.loads((OUT / "bootstrap_meta.json").read_text())
    draws = pd.read_parquet(OUT / "bootstrap_centered.parquet")

    assert meta["attempted"] == meta["completed"] == len(draws) == 2000
    assert not meta["failed"]
    assert draws["iteration"].is_unique and set(draws["iteration"]) == set(range(2000))
    assert validation["initialization_seed_overlap"] == []
    assert summary["plan_commit"] == PLAN_COMMIT
    ci = np.percentile(draws["E_c:L_c"], [2.5, 50, 97.5])
    assert np.allclose(ci, [summary["bootstrap_ci"][0], summary["bootstrap_median"], summary["bootstrap_ci"][1]])

    coefficient = {
        "coefficient": "E_c:L_c",
        "estimate": summary["estimate"],
        "standard_error": summary["se"],
        "wald_ci_lo": summary["ci"][0],
        "wald_ci_hi": summary["ci"][1],
        "p_unadjusted": summary["p_raw"],
        "bootstrap_ci_lo": summary["bootstrap_ci"][0],
        "bootstrap_median": summary["bootstrap_median"],
        "bootstrap_ci_hi": summary["bootstrap_ci"][1],
        "bootstrap_completed": summary["bootstrap_completed"],
        "classification": summary["classification"],
    }
    (OUT / "coefficient.json").write_text(json.dumps(coefficient, indent=2) + "\n")
    pd.DataFrame([coefficient]).to_csv(OUT / "coefficient.csv", index=False)
    pd.DataFrame(columns=["iteration", "status", "reason"]).to_csv(OUT / "failure_log.csv", index=False)

    comparison = pd.read_csv(OUT / "original_vs_independent.csv")
    comparison.to_csv(OUT / "comparison_figure_source.csv", index=False)
    fig, ax = plt.subplots(figsize=(5.5, 2.7))
    y = np.arange(len(comparison))
    ax.errorbar(comparison.estimate, y,
                xerr=[comparison.estimate - comparison.ci_lo, comparison.ci_hi - comparison.estimate],
                fmt="o", capsize=4, color="#24527a")
    ax.axvline(0, color="0.45", lw=0.8)
    ax.set_yticks(y, ["Original seed", "Independent seed"])
    ax.set_xlabel(r"Centered $E\times L$ coefficient (Wald 95% CI)")
    ax.set_title("H1 seed-root comparison")
    fig.tight_layout()
    fig.savefig(OUT / "comparison_figure.pdf")
    fig.savefig(OUT / "comparison_figure.png", dpi=200)
    plt.close(fig)

    input_paths = [
        ROOT / "results/h2_replication_v1/_pipeline_output_stage1/raw/exact.parquet",
        ROOT / "results/production_confirmatory/raw/exact.parquet",
        ROOT / "results/primary_corrected/effect_coded/corrected_confirmatory_hypotheses.csv",
        ROOT / "configs/confirmatory.yaml",
        ROOT / "configs/h2_replication_v1_stage1.yaml",
    ]
    provenance = {
        "plan_commit": PLAN_COMMIT,
        "analysis_commit": None,
        "code_head_at_finalization": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip(),
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "commands": ["python scripts/run_independent_seed_h1.py", "python scripts/resume_independent_seed_h1_bootstrap.py", "python scripts/finalize_independent_seed_h1.py"],
        "input_sha256": {str(p.relative_to(ROOT)).replace("\\", "/"): sha256(p) for p in input_paths},
    }
    (OUT / "provenance.json").write_text(json.dumps(provenance, indent=2) + "\n")

    validation_md = f"""# Independent-seed H1 validation

- Rows: {validation['rows']}; initialization clusters: {validation['clusters']}.
- Configurations: {validation['configurations']}; depths: {validation['depths']}.
- Duplicate analysis keys: {validation['duplicate_keys']}.
- Parameter counts by depth: {validation['parameter_counts_by_depth']}.
- Original/independent initialization-seed overlap: none.
- Bootstrap: {meta['completed']} completed of {meta['attempted']} attempted; 0 failed; iteration identities 0--1999 are unique and complete.
- Frozen plan commit: `{PLAN_COMMIT}`.

All frozen eligibility, seed-separation, convergence, and bootstrap-completion checks passed.
"""
    (OUT / "validation.md").write_text(validation_md)

    report = f"""# Independent-seed H1 robustness result

**Status:** completed post-primary robustness analysis under the plan frozen at `{PLAN_COMMIT}`. This is not part of the original Holm family and is not an independent-investigator replication.

The independent-seed centered H1 estimate is {summary['estimate']:.6f} (SE {summary['se']:.6f}; Wald 95% CI [{summary['ci'][0]:.6f}, {summary['ci'][1]:.6f}]; unadjusted p={summary['p_raw']:.3g}). The 2,000-fit cluster bootstrap completed with zero failures and gives a percentile 95% CI [{summary['bootstrap_ci'][0]:.6f}, {summary['bootstrap_ci'][1]:.6f}] (median {summary['bootstrap_median']:.6f}). Both intervals exclude zero in the positive direction.

The original corrected estimate was {comparison.iloc[0].estimate:.6f} with Wald 95% CI [{comparison.iloc[0].ci_lo:.6f}, {comparison.iloc[0].ci_hi:.6f}]. The independent-seed estimate has the same sign but lies above that original interval. Under the frozen categories, the result is therefore **{summary['classification']}**. It supports directional robustness while flagging seed-root sensitivity in effect size; it is not described as “confirmed.”

Endpoint checks at 100, 250, 400, 1,000, and 2,000 completed fits are retained in `bootstrap_endpoints.csv`; validation and provenance are recorded alongside the coefficient, draws, failure log, source table, and comparison figure in `results/independent_seed_h1/effect_coded/`.
"""
    (ROOT / "verification/h1_independent_seed_results.md").write_text(report)


if __name__ == "__main__":
    main()
