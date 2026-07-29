"""Task G: real per-initialization error bars for the entanglement-by-depth
diagnostic, replacing the across-4-configs "sd" in the original
verification/depth_entanglement_by_depth_check.md (which was ~0 wherever R
hadn't activated and only reflected R's small effect afterward, not genuine
init-to-init sampling noise).

`qnn_snr.stats.descriptive.physics_summary_rows(cfg)` recomputes the exact
same deterministic (theta_seed, classical_seed)-driven physics diagnostics
that were averaged into results/configuration_summaries.csv -- calling it
directly gives the underlying 50-per-(config,depth) values instead of just
their mean. This is a cheap, deterministic recomputation (no shot sampling,
no re-simulation of the confirmatory run's stored results), not new science.

Run from the repo root:
    python verification/entanglement_per_init_check.py

Writes: verification/_entanglement_per_init.parquet (raw per-init rows),
        verification/entanglement_per_init_check_results.json (summary + regression)
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd
import statsmodels.formula.api as smf

from qnn_snr.config import load_config
from qnn_snr.stats.descriptive import physics_summary_rows

REPO_ROOT = Path(__file__).resolve().parent.parent
DEPTHS = [1, 2, 3, 4, 6]
DEPTH_MEAN = float(np.mean(DEPTHS))
DEPTH_STD = float(np.std(DEPTHS, ddof=0))
# one representative config per (E, R) -- L is verified below to have exactly
# zero effect on entanglement diagnostics, so including both L=0/L=1 configs
# would be pseudo-replication (bit-identical duplicate rows), not real n.
REP_CONFIG = {(0, 0): 1, (1, 0): 2, (0, 1): 4, (1, 1): 6}


def main():
    cfg = load_config(REPO_ROOT / "configs" / "confirmatory.yaml")
    rows = physics_summary_rows(cfg)
    df = pd.DataFrame(rows)
    df.to_parquet(Path(__file__).parent / "_entanglement_per_init.parquet", index=False)
    print(f"computed {len(df)} per-(config,depth,init) physics rows "
          f"({df['configuration_id'].nunique()} configs x {df['depth'].nunique()} depths x "
          f"{df['initialization_id'].nunique()} inits)")

    # --- verify L has zero effect (justifies collapsing L before computing SEM) ---
    l_pairs = [(1, 3), (2, 5), (4, 7), (6, 8)]
    max_l_diff = 0.0
    for a, b in l_pairs:
        da = df[df.configuration_id == a].sort_values(["depth", "initialization_id"]).reset_index(drop=True)
        db = df[df.configuration_id == b].sort_values(["depth", "initialization_id"]).reset_index(drop=True)
        d = float((da["mean_entanglement_entropy"] - db["mean_entanglement_entropy"]).abs().max())
        max_l_diff = max(max_l_diff, d)
    print(f"max |entropy diff| across L=0/L=1 config pairs (same E,R): {max_l_diff:.3e}")

    rep_ids = set(REP_CONFIG.values())
    d = df[df["configuration_id"].isin(rep_ids)].copy()
    d["depth_z"] = (d["depth"] - DEPTH_MEAN) / DEPTH_STD

    # --- per (E, R, depth): real n=50 mean +/- SEM ---
    per_erd = (d.groupby(["E", "R", "depth"])
                 .agg(entropy_mean=("mean_entanglement_entropy", "mean"),
                      entropy_sd=("mean_entanglement_entropy", lambda s: s.std(ddof=1)),
                      purity_mean=("mean_purity", "mean"),
                      purity_sd=("mean_purity", lambda s: s.std(ddof=1)),
                      n=("initialization_id", "size"))
                 .reset_index())
    per_erd["entropy_sem"] = per_erd["entropy_sd"] / np.sqrt(per_erd["n"])
    per_erd["purity_sem"] = per_erd["purity_sd"] / np.sqrt(per_erd["n"])

    # --- per (E, depth) marginal: pooled over R (2*50=100), decomposing
    #     within-cell (init) variance from the systematic R shift explicitly ---
    per_ed = (d.groupby(["E", "depth"])
                .agg(entropy_mean=("mean_entanglement_entropy", "mean"),
                     entropy_sd_pooled=("mean_entanglement_entropy", lambda s: s.std(ddof=1)),
                     purity_mean=("mean_purity", "mean"),
                     purity_sd_pooled=("mean_purity", lambda s: s.std(ddof=1)),
                     n=("initialization_id", "size"))
                .reset_index())
    per_ed["entropy_sem_pooled"] = per_ed["entropy_sd_pooled"] / np.sqrt(per_ed["n"])
    # within-R-group average SEM (proper sampling SEM, not inflated by the R systematic shift)
    within = per_erd.groupby(["E", "depth"])["entropy_sem"].mean().rename("entropy_sem_within_R").reset_index()
    per_ed = per_ed.merge(within, on=["E", "depth"])

    # --- regression: entropy ~ depth_z (+R, +R:depth_z) with init random intercept, per E ---
    regression_results = {}
    for e_val in (0, 1):
        sub = d[d["E"] == e_val].copy()
        try:
            md = smf.mixedlm("mean_entanglement_entropy ~ depth_z * R", sub,
                              groups=sub["initialization_id"])
            fit = md.fit(reml=True)
            regression_results[f"E={e_val}"] = {
                "formula": "mean_entanglement_entropy ~ depth_z * R, groups=initialization_id",
                "n_obs": int(fit.nobs),
                "converged": bool(fit.converged),
                "params": {k: float(v) for k, v in fit.params.items()},
                "bse": {k: float(v) for k, v in fit.bse.items()},
                "pvalues": {k: float(v) for k, v in fit.pvalues.items()},
            }
        except Exception as exc:  # noqa: BLE001
            regression_results[f"E={e_val}"] = {"error": repr(exc)}

    out = {
        "max_L_induced_entropy_diff": max_l_diff,
        "note_L": "confirms L has exactly zero effect on entanglement diagnostics; "
                  "collapsed out before computing per-init SEM to avoid pseudo-replication",
        "per_E_R_depth": per_erd.to_dict("records"),
        "per_E_depth_marginal": per_ed.to_dict("records"),
        "regression_entropy_vs_depth_z": regression_results,
        "n_initializations": int(d["initialization_id"].nunique()),
    }
    out_path = Path(__file__).parent / "entanglement_per_init_check_results.json"
    out_path.write_text(json.dumps(out, indent=2, default=str), encoding="utf-8")

    print("\n=== per (E, R, depth), n=50 real inits each ===")
    print(per_erd.round(4).to_string(index=False))
    print("\n=== per (E, depth) marginal over R, n=100 (2 systematically different R groups pooled) ===")
    print(per_ed.round(4).to_string(index=False))
    print("\n=== regression: entropy ~ depth_z * R, random intercept per init ===")
    for k, v in regression_results.items():
        print(f"-- {k} --")
        if "error" in v:
            print("  ERROR", v["error"])
            continue
        for coef in ("depth_z", "R", "depth_z:R"):
            if coef in v["params"]:
                p = v["params"][coef]
                se = v["bse"][coef]
                pv = v["pvalues"][coef]
                print(f"  {coef}: {p:.5f} (SE {se:.5f}, p={pv:.4f})")
    print(f"\nwrote {out_path}")


if __name__ == "__main__":
    main()
