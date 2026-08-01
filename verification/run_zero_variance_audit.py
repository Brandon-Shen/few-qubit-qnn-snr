"""QMI/QIP robustness package, Task 2: zero-variance exclusion audit.

Uses the production `zero_variance_flag` column in
results/production_confirmatory/pointwise_gradient_statistics.parquet directly (qnn_snr/stats/pointwise.py:
exactly-zero across-replicate sample variance, ddof=1, ZERO_VARIANCE_TOL=0.0)
-- not re-derived from any rounded output column.

Run from the repo root: python verification/run_zero_variance_audit.py
"""
from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

REPO_ROOT = Path(__file__).resolve().parent.parent
CONFIRMATORY_MODE = "finite_shot_end_to_end"
DIAGNOSTIC_MODE = "finite_shot_conditional"
BUDGETS = [250, 500, 1000, 2000]
CONFIGS = list(range(1, 9))

# configuration_id -> (E, L, R), matching Table 1 of the paper
CONFIG_ELR = {
    1: (0, 0, 0), 2: (1, 0, 0), 3: (0, 1, 0), 4: (0, 0, 1),
    5: (1, 1, 0), 6: (1, 0, 1), 7: (0, 1, 1), 8: (1, 1, 1),
}


def config_budget_table(df: pd.DataFrame, depth: int | None = None) -> pd.DataFrame:
    d = df if depth is None else df[df["depth"] == depth]
    rows = []
    for cfg in CONFIGS:
        row = {"configuration_id": cfg}
        for b in BUDGETS:
            sub = d[(d["configuration_id"] == cfg) & (d["budget"] == b)]
            total = len(sub)
            excluded = int(sub["zero_variance_flag"].sum())
            pct = 100.0 * excluded / total if total else float("nan")
            row[f"total_B{b}"] = total
            row[f"excluded_B{b}"] = excluded
            row[f"pct_B{b}"] = pct
        rows.append(row)
    out = pd.DataFrame(rows)
    total_cols = [c for c in out.columns if c.startswith("total_")]
    excl_cols = [c for c in out.columns if c.startswith("excluded_")]
    out["total_all_budgets"] = out[total_cols].sum(axis=1)
    out["excluded_all_budgets"] = out[excl_cols].sum(axis=1)
    out["pct_all_budgets"] = 100.0 * out["excluded_all_budgets"] / out["total_all_budgets"]
    return out


def marginal_by(df: pd.DataFrame, col: str) -> pd.DataFrame:
    g = df.groupby(col)["zero_variance_flag"].agg(total="count", excluded="sum").reset_index()
    g["pct"] = 100.0 * g["excluded"] / g["total"]
    return g


def by_config_depth_budget(df: pd.DataFrame) -> pd.DataFrame:
    g = df.groupby(["configuration_id", "depth", "budget"])["zero_variance_flag"].agg(
        total="count", excluded="sum").reset_index()
    g["pct"] = 100.0 * g["excluded"] / g["total"]
    return g


def main():
    pw = pd.read_parquet(REPO_ROOT / "results" / "production_confirmatory" / "pointwise_gradient_statistics.parquet")
    for cfg, (e, l, r) in CONFIG_ELR.items():
        pw.loc[pw["configuration_id"] == cfg, "_E_chk"] = e
    eo = pw[pw["analysis_mode"] == CONFIRMATORY_MODE].copy()
    cond = pw[pw["analysis_mode"] == DIAGNOSTIC_MODE].copy()
    eo_d1 = eo[eo["depth"] == 1].copy()

    print(f"end-to-end rows: {len(eo)} ({int(eo['zero_variance_flag'].sum())} excluded, "
          f"{100*eo['zero_variance_flag'].mean():.3f}%)")
    print(f"end-to-end D=1 rows: {len(eo_d1)} ({int(eo_d1['zero_variance_flag'].sum())} excluded, "
          f"{100*eo_d1['zero_variance_flag'].mean():.3f}%)")
    print(f"conditional rows: {len(cond)} ({int(cond['zero_variance_flag'].sum())} excluded, "
          f"{100*cond['zero_variance_flag'].mean():.3f}%)")

    # --- Primary table: end-to-end, D=1, config x budget ---
    primary = config_budget_table(eo, depth=1)
    primary_path = REPO_ROOT / "results" / "sensitivity_analyses" / "zero_variance_exclusions_d1_config_budget.csv"
    primary.to_csv(primary_path, index=False)
    print(f"\nwrote {primary_path}")
    print(primary[["configuration_id", "total_all_budgets", "excluded_all_budgets", "pct_all_budgets"]])

    # marginals at D=1, end-to-end
    marg_config = marginal_by(eo_d1, "configuration_id")
    marg_budget = marginal_by(eo_d1, "budget")
    marg_E = marginal_by(eo_d1, "E")
    marg_L = marginal_by(eo_d1, "L")
    marg_R = marginal_by(eo_d1, "R")
    print("\nD=1 end-to-end marginal by E:\n", marg_E)
    print("\nD=1 end-to-end marginal by L:\n", marg_L)
    print("\nD=1 end-to-end marginal by R:\n", marg_R)

    marginals_path = REPO_ROOT / "verification" / "_zero_variance_d1_marginals.json"
    import json
    marginals_path.write_text(json.dumps({
        "by_configuration": marg_config.to_dict("records"),
        "by_budget": marg_budget.to_dict("records"),
        "by_E": marg_E.to_dict("records"),
        "by_L": marg_L.to_dict("records"),
        "by_R": marg_R.to_dict("records"),
    }, indent=2, default=str), encoding="utf-8")
    print(f"wrote {marginals_path}")

    # --- Secondary 1: end-to-end exclusion rates by config, block count, budget (all D) ---
    eo_all_cells = by_config_depth_budget(eo)
    eo_all_path = REPO_ROOT / "results" / "sensitivity_analyses" / "zero_variance_exclusions_all_cells.csv"
    eo_all_cells.insert(0, "analysis_mode", CONFIRMATORY_MODE)

    # --- Secondary 2: conditional-mode rates, same breakdown, diagnostic only ---
    cond_all_cells = by_config_depth_budget(cond)
    cond_all_cells.insert(0, "analysis_mode", DIAGNOSTIC_MODE)

    all_cells = pd.concat([eo_all_cells, cond_all_cells], ignore_index=True)
    all_cells.to_csv(eo_all_path, index=False)
    print(f"\nwrote {eo_all_path} ({len(all_cells)} rows, both modes)")

    # --- Secondary 3: direct end-to-end vs conditional comparison at matched cells ---
    eo_keyed = eo_all_cells.set_index(["configuration_id", "depth", "budget"])[["total", "excluded", "pct"]]
    cond_keyed = cond_all_cells.set_index(["configuration_id", "depth", "budget"])[["total", "excluded", "pct"]]
    matched = eo_keyed.join(cond_keyed, lsuffix="_endtoend", rsuffix="_conditional", how="outer").reset_index()
    matched["pct_diff_endtoend_minus_conditional"] = matched["pct_endtoend"] - matched["pct_conditional"]
    by_mode_path = REPO_ROOT / "results" / "sensitivity_analyses" / "zero_variance_exclusions_by_mode.csv"
    matched.to_csv(by_mode_path, index=False)
    print(f"wrote {by_mode_path}")

    # --- Secondary 4: exclusions caused by reasons other than exactly zero variance ---
    # The production pipeline (qnn_snr/stats/pointwise.py) has exactly one exclusion
    # mechanism feeding the H2-H4 model: build_h2h4_dataset()'s np.isfinite(SNR_est)
    # filter, which is true iff zero_variance_flag is True (SNR_est=inf) OR mu_hat==0
    # AND exact==0 simultaneously under the zero-variance branch (SNR_est=nan). Check
    # directly whether any non-finite SNR_est row has zero_variance_flag == False.
    non_finite_but_not_flagged = pw[(~np.isfinite(pw["SNR_est"])) & (~pw["zero_variance_flag"])]
    print(f"\nnon-finite SNR_est rows NOT explained by zero_variance_flag: "
          f"{len(non_finite_but_not_flagged)} (should be 0 -- confirms zero variance is "
          f"the only exclusion mechanism in the production pipeline)")
    other_reasons_path = REPO_ROOT / "verification" / "_zero_variance_other_exclusion_reasons.csv"
    non_finite_but_not_flagged.to_csv(other_reasons_path, index=False)
    print(f"wrote {other_reasons_path} ({len(non_finite_but_not_flagged)} rows)")

    # --- Association diagnostic (D=1, end-to-end only) ---
    n_excluded_d1 = int(eo_d1["zero_variance_flag"].sum())
    print(f"\nD=1 end-to-end excluded cells for association model: {n_excluded_d1} of {len(eo_d1)}")


if __name__ == "__main__":
    main()
