"""QMI/QIP robustness package, Task 3 parts A-C: convergence/singularity
diagnostics, independent-optimizer comparison, and residual diagnostics for
the adopted end-to-end full-sweep H2-H4 fit (and, where relevant, the
D!=1 sensitivity fit from Task 1).

Part D (leave-one-initialization-out, 50 refits) is a separate, much
longer-running script: run_loo_initialization.py.

Run from the repo root: python verification/run_model_diagnostics.py
"""
from __future__ import annotations

import json
import warnings
from pathlib import Path

import sys

import numpy as np
import pandas as pd
import statsmodels.formula.api as smf
import matplotlib.pyplot as plt
from scipy import stats

from qnn_snr.stats.models import H2_H4_FORMULA, build_h2h4_dataset, fit_h2h4_model, _add_nested_id

REPO_ROOT = Path(__file__).resolve().parent.parent
TARGET_COEFS = ["E:L", "E:R", "L:R:depth_z"]

sys.path.insert(0, str(REPO_ROOT / "paper" / "scripts"))
from plot_style import (  # noqa: E402
    COLOR_SERIES_A, COLOR_SERIES_B, COLOR_ACCENT, COLUMN_WIDTH_IN,
    TITLE_FONT_SIZE, LABEL_FONT_SIZE, apply_style,
)


def main():
    pw = pd.read_parquet(REPO_ROOT / "results" / "production_confirmatory" / "pointwise_gradient_statistics.parquet")
    eo_full = pw[pw["analysis_mode"] == "finite_shot_end_to_end"].copy()

    # ----- A. Convergence and singularity (adopted full-sweep fit) -----
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        res = fit_h2h4_model(eo_full)
        adopted_warnings = [str(w.message) for w in caught]

    raw = res.raw_result
    llf = float(raw.llf)
    a_diag = {
        "optimizer_exit_status_converged": res.converged,
        "optimizer_used": res.optimizer_used,
        "attempted_optimizers": res.attempted_optimizers,
        "warnings_emitted": adopted_warnings,
        "log_likelihood_reml": llf,
        "n_obs": res.n_obs,
        "n_groups": res.n_groups,
        "n_vc_levels": res.n_vc_levels,
        "condition_number": res.condition_number,
        "singular_fit": res.singular_fit,
        "singular_fit_tolerance_atol": 1e-8,
        "group_intercept_var": res.random_effect_variances["group_intercept_var"],
        "nested_param_var": res.random_effect_variances["nested_param_var"],
        "residual_diagnostics_from_fit": res.residual_diagnostics,
    }
    print("=== A. Convergence/singularity (adopted full-sweep) ===")
    print(json.dumps(a_diag, indent=2, default=str))

    # ----- B. Independent optimizer check: force bfgs, compare to lbfgs -----
    d = _add_nested_id(build_h2h4_dataset(eo_full))
    with warnings.catch_warnings(record=True) as caught_b:
        warnings.simplefilter("always")
        model_bfgs = smf.mixedlm(H2_H4_FORMULA, data=d, groups=d["initialization_id"], re_formula="1",
                                  vc_formula={"param": "0 + C(nested_param_id)"})
        result_bfgs = model_bfgs.fit(method="bfgs", reml=True)
        bfgs_warnings = [str(w.message) for w in caught_b]

    optimizer_rows = []
    for coef in TARGET_COEFS:
        optimizer_rows.append({
            "coefficient": coef,
            "lbfgs_estimate": res.params[coef], "lbfgs_se": res.bse[coef],
            "bfgs_estimate": float(result_bfgs.params[coef]), "bfgs_se": float(result_bfgs.bse[coef]),
            "abs_diff": float(result_bfgs.params[coef]) - res.params[coef],
        })
    optimizer_rows.append({
        "coefficient": "log_likelihood", "lbfgs_estimate": llf, "lbfgs_se": float("nan"),
        "bfgs_estimate": float(result_bfgs.llf), "bfgs_se": float("nan"),
        "abs_diff": float(result_bfgs.llf) - llf,
    })
    group_var_bfgs = float(result_bfgs.cov_re.iloc[0, 0]) if result_bfgs.cov_re is not None else float("nan")
    vc_var_bfgs = float(result_bfgs.vcomp[0]) if len(result_bfgs.vcomp) else float("nan")
    optimizer_rows.append({
        "coefficient": "group_intercept_var", "lbfgs_estimate": a_diag["group_intercept_var"], "lbfgs_se": float("nan"),
        "bfgs_estimate": group_var_bfgs, "bfgs_se": float("nan"),
        "abs_diff": group_var_bfgs - a_diag["group_intercept_var"],
    })
    optimizer_rows.append({
        "coefficient": "nested_param_var", "lbfgs_estimate": a_diag["nested_param_var"], "lbfgs_se": float("nan"),
        "bfgs_estimate": vc_var_bfgs, "bfgs_se": float("nan"),
        "abs_diff": vc_var_bfgs - a_diag["nested_param_var"],
    })
    opt_df = pd.DataFrame(optimizer_rows)
    opt_path = REPO_ROOT / "results" / "sensitivity_analyses" / "model_optimizer_comparison.csv"
    opt_df.to_csv(opt_path, index=False)
    print(f"\n=== B. Optimizer comparison (lbfgs [adopted] vs. bfgs [independent check]) ===")
    print(opt_df.to_string())
    print(f"bfgs converged: {result_bfgs.converged}; warnings: {bfgs_warnings}")
    print(f"wrote {opt_path}")

    # ----- C. Residual diagnostics -----
    resid = np.asarray(res.raw_result.resid)
    fitted = np.asarray(res.raw_result.fittedvalues)
    d_resid = d.loc[d.index[:len(resid)]].copy() if len(d) == len(resid) else d.iloc[:len(resid)].copy()
    d_resid["_resid"] = resid
    d_resid["_fitted"] = fitted
    d_resid["_std_resid"] = (resid - resid.mean()) / resid.std(ddof=1)

    apply_style()
    fig, axes = plt.subplots(2, 2, figsize=(COLUMN_WIDTH_IN * 1.9, COLUMN_WIDTH_IN * 1.55))
    axes[0, 0].scatter(fitted, resid, s=2.5, alpha=0.25, color=COLOR_SERIES_A, linewidths=0)
    axes[0, 0].axhline(0, color="black", linewidth=0.7)
    axes[0, 0].set_xlabel("Fitted value"); axes[0, 0].set_ylabel("Residual")
    axes[0, 0].set_title("Residual vs. fitted", fontsize=TITLE_FONT_SIZE)

    stats.probplot(resid, dist="norm", plot=axes[0, 1])
    axes[0, 1].set_title("Normal Q--Q", fontsize=TITLE_FONT_SIZE)
    axes[0, 1].set_xlabel("Theoretical quantiles"); axes[0, 1].set_ylabel("Ordered values")
    qq_line = axes[0, 1].get_lines()
    qq_line[0].set(marker="o", markersize=2.2, markerfacecolor=COLOR_SERIES_A,
                   markeredgecolor="none", linestyle="none", alpha=0.35)
    qq_line[1].set(color=COLOR_SERIES_B, linewidth=1.1)

    by_depth = d_resid.groupby("depth")["_resid"].std()
    axes[1, 0].bar(by_depth.index.astype(str), by_depth.values, color=COLOR_SERIES_B, width=0.65)
    axes[1, 0].set_xlabel("Block count $D$"); axes[1, 0].set_ylabel("Residual SD")
    axes[1, 0].set_title("Residual scale by block count", fontsize=TITLE_FONT_SIZE)

    by_config = d_resid.groupby("configuration_id")["_resid"].std()
    axes[1, 1].bar(by_config.index.astype(str), by_config.values, color=COLOR_ACCENT, width=0.65)
    axes[1, 1].set_xlabel("Configuration"); axes[1, 1].set_ylabel("Residual SD")
    axes[1, 1].set_title("Residual scale by configuration", fontsize=TITLE_FONT_SIZE)

    for ax_ in axes.ravel():
        ax_.spines["top"].set_visible(False)
        ax_.spines["right"].set_visible(False)

    fig.tight_layout()
    fig_path = REPO_ROOT / "paper" / "figures" / "fig8_model_residual_diagnostics.pdf"
    fig_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(fig_path)
    fig.savefig(fig_path.with_name(fig_path.stem + "_preview.png"), dpi=200)
    print(f"\nwrote {fig_path}")

    by_budget = d_resid.groupby("budget")["_resid"].std()
    extreme = d_resid.reindex(d_resid["_std_resid"].abs().sort_values(ascending=False).index).head(20)
    c_diag = {
        "resid_mean": float(resid.mean()), "resid_sd": float(resid.std(ddof=1)),
        "resid_by_depth_sd": by_depth.to_dict(),
        "resid_by_budget_sd": by_budget.to_dict(),
        "resid_by_config_sd": by_config.to_dict(),
        "n_extreme_std_resid_gt4": int((d_resid["_std_resid"].abs() > 4).sum()),
        "n_extreme_std_resid_gt3": int((d_resid["_std_resid"].abs() > 3).sum()),
        "max_abs_std_resid": float(d_resid["_std_resid"].abs().max()),
        "shapiro_note": "n too large for exact Shapiro-Wilk; using Q-Q plot + tail counts instead",
    }
    diag_path = REPO_ROOT / "verification" / "_residual_diagnostics.json"
    diag_path.write_text(json.dumps(c_diag, indent=2, default=str), encoding="utf-8")
    print(f"wrote {diag_path}")
    print(json.dumps(c_diag, indent=2, default=str))

    extreme_path = REPO_ROOT / "verification" / "_extreme_residuals.csv"
    extreme[["analysis_mode", "configuration_id", "E", "L", "R", "depth", "budget",
              "initialization_id", "parameter_id", "_fitted", "_resid", "_std_resid"]].to_csv(extreme_path, index=False)
    print(f"wrote {extreme_path}")


if __name__ == "__main__":
    main()
