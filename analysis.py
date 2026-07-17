"""Hypothesis tests (H1, H2a, H2b, H3) and summary statistics.

All cross-configuration comparisons use the seed-level mean SNR (mean over a
seed's per-parameter SNRs, as saved in the *_summary.csv "mean_snr" column).
Since every configuration in the main experiment is evaluated on the
identical 50 seeds (paired design: seed s produces the same theta draw
regardless of configuration, per snr.init_params), comparisons use the
Wilcoxon signed-rank test on the 50 paired differences -- never Mann-Whitney
U, which assumes independence and would discard the pairing.
"""
import json
import os

import numpy as np
import pandas as pd
from scipy.stats import wilcoxon

RESULTS_DIR = os.path.join(os.path.dirname(__file__), "results")

METRIC = "mean_snr"


def paired_values(df, config_name, metric=METRIC, extra_filter=None):
    sub = df[df["config_name"] == config_name]
    if extra_filter is not None:
        sub = sub[extra_filter(sub)]
    sub = sub.sort_values("seed")
    return sub[metric].to_numpy()


def wilcoxon_compare(df, name_a, name_b, metric=METRIC, extra_filter=None):
    a = paired_values(df, name_a, metric, extra_filter)
    b = paired_values(df, name_b, metric, extra_filter)
    assert len(a) == len(b) and len(a) > 0, f"unpaired or empty samples: {name_a} vs {name_b}"
    diff = a - b
    result = {
        "config_a": name_a, "config_b": name_b,
        "mean_a": float(np.mean(a)), "mean_b": float(np.mean(b)),
        "median_a": float(np.median(a)), "median_b": float(np.median(b)),
        "mean_diff_a_minus_b": float(np.mean(diff)),
        "a_greater_than_b": bool(np.mean(a) > np.mean(b)),
        "n_pairs": len(a),
    }
    if np.allclose(diff, 0.0):
        result.update({"statistic": None, "pvalue": 1.0, "note": "all paired differences are zero"})
    else:
        stat, p = wilcoxon(a, b, zero_method="wilcox")
        result.update({"statistic": float(stat), "pvalue": float(p)})
    return result


def summarize_configs(df, metric=METRIC):
    rows = []
    for name, sub in df.groupby("config_name"):
        rows.append({
            "config_name": name,
            "config_label": sub["config_label"].iloc[0],
            "mean_of_seed_means": float(sub[metric].mean()),
            "median_of_seed_means": float(sub[metric].median()),
            "std_of_seed_means": float(sub[metric].std()),
            "n_seeds": len(sub),
        })
    return pd.DataFrame(rows)


def analyze_h1(df):
    """H1: does config 7 (combined) exceed each of configs 1-4 individually?"""
    comparisons = []
    for baseline_cfg in ["baseline", "entanglement_only", "local_cost_only", "residual_only"]:
        comparisons.append(wilcoxon_compare(df, "combined", baseline_cfg))
    all_exceed = all(c["a_greater_than_b"] for c in comparisons)
    all_significant = all((c["pvalue"] is not None and c["pvalue"] < 0.05) for c in comparisons)
    return {
        "hypothesis": "H1: combined (config 7) SNR > configs 1-4 individually",
        "comparisons": comparisons,
        "combined_exceeds_all_four": all_exceed,
        "all_differences_significant_p<0.05": all_significant,
    }


def _additivity_framings(mean_baseline, mean_a, mean_b, mean_ab):
    gain_a = mean_a - mean_baseline
    gain_b = mean_b - mean_baseline
    gain_ab_actual = mean_ab - mean_baseline
    sum_prediction = gain_a + gain_b
    sub_additive_sum_framing = gain_ab_actual < sum_prediction

    ratio_a = mean_a / mean_baseline if mean_baseline else float("nan")
    ratio_b = mean_b / mean_baseline if mean_baseline else float("nan")
    ratio_ab_actual = mean_ab / mean_baseline if mean_baseline else float("nan")
    product_prediction = ratio_a * ratio_b
    sub_additive_product_framing = ratio_ab_actual < product_prediction

    return {
        "gain_a_over_baseline": float(gain_a),
        "gain_b_over_baseline": float(gain_b),
        "gain_combined_over_baseline_actual": float(gain_ab_actual),
        "sum_framing_additive_prediction": float(sum_prediction),
        "sum_framing_sub_additive": bool(sub_additive_sum_framing),
        "ratio_a_over_baseline": float(ratio_a),
        "ratio_b_over_baseline": float(ratio_b),
        "ratio_combined_over_baseline_actual": float(ratio_ab_actual),
        "product_framing_multiplicative_prediction": float(product_prediction),
        "product_framing_sub_additive": bool(sub_additive_product_framing),
    }


def analyze_h2a(df):
    """H2a: config 5 (entanglement+local) vs configs 2 (entanglement) and 3 (local),
    against baseline (config 1), in both sum- and product-additivity framings.
    """
    means = df.groupby("config_name")[METRIC].mean()
    framings = _additivity_framings(
        means["baseline"], means["entanglement_only"], means["local_cost_only"],
        means["entanglement_local"],
    )
    return {
        "hypothesis": "H2a: entanglement_local (config 5) vs entanglement_only (2) and local_cost_only (3)",
        "wilcoxon_config5_vs_config2": wilcoxon_compare(df, "entanglement_local", "entanglement_only"),
        "wilcoxon_config5_vs_config3": wilcoxon_compare(df, "entanglement_local", "local_cost_only"),
        "additivity": framings,
    }


def analyze_h2b(df):
    """H2b: config 6 (entanglement+residual) vs configs 2 (entanglement) and 4 (residual)."""
    means = df.groupby("config_name")[METRIC].mean()
    framings = _additivity_framings(
        means["baseline"], means["entanglement_only"], means["residual_only"],
        means["entanglement_residual"],
    )
    return {
        "hypothesis": "H2b: entanglement_residual (config 6) vs entanglement_only (2) and residual_only (4)",
        "wilcoxon_config6_vs_config2": wilcoxon_compare(df, "entanglement_residual", "entanglement_only"),
        "wilcoxon_config6_vs_config4": wilcoxon_compare(df, "entanglement_residual", "residual_only"),
        "additivity": framings,
    }


def analyze_h3(depth_df):
    """H3: is there a depth threshold below which local-cost dominates and
    above which residual connections dominate? For each depth, compares
    local_cost_only vs residual_only with a paired Wilcoxon test (same seeds
    at that depth), and reports per-depth means AND medians to locate any
    crossover.

    Seed-level mean SNR is heavy-tailed, especially at shallow depth: a
    near-deterministic circuit can send shot-noise variance for one parameter
    close to zero while its gradient stays finite, producing an SNR blowup
    for that single seed that dominates the arithmetic mean of 50 seeds. The
    Wilcoxon test itself is rank-based and unaffected by this, but a raw
    "mean_a > mean_b" comparison is not -- so the crossover determination
    below uses the **median** (matching the log-scale/median+IQR plot in
    plots.py), with the mean reported alongside for transparency.
    """
    depths = sorted(depth_df["L"].unique())
    per_depth = []
    for L in depths:
        sub = depth_df[depth_df["L"] == L]
        cmp_local_vs_residual = wilcoxon_compare(sub, "local_cost_only", "residual_only")
        cmp_local_vs_combo = wilcoxon_compare(sub, "local_cost_only", "local_and_residual")
        cmp_residual_vs_combo = wilcoxon_compare(sub, "residual_only", "local_and_residual")
        means = sub.groupby("config_name")[METRIC].mean()
        medians = sub.groupby("config_name")[METRIC].median()
        per_depth.append({
            "L": int(L),
            "mean_local_cost_only": float(means.get("local_cost_only", np.nan)),
            "mean_residual_only": float(means.get("residual_only", np.nan)),
            "mean_local_and_residual": float(means.get("local_and_residual", np.nan)),
            "median_local_cost_only": float(medians.get("local_cost_only", np.nan)),
            "median_residual_only": float(medians.get("residual_only", np.nan)),
            "median_local_and_residual": float(medians.get("local_and_residual", np.nan)),
            "local_beats_residual_by_mean": bool(cmp_local_vs_residual["a_greater_than_b"]),
            "local_beats_residual_by_median": bool(
                medians.get("local_cost_only", np.nan) > medians.get("residual_only", np.nan)
            ),
            "local_vs_residual_pvalue": cmp_local_vs_residual["pvalue"],
            "local_vs_combo": cmp_local_vs_combo,
            "residual_vs_combo": cmp_residual_vs_combo,
        })

    # locate crossover (median-based): first depth (ascending) where the winner flips,
    # in *either* direction -- we don't assume the H3-hypothesized direction in advance.
    crossover_L = None
    crossover_direction = None
    for i in range(1, len(per_depth)):
        prev_local_wins = per_depth[i - 1]["local_beats_residual_by_median"]
        curr_local_wins = per_depth[i]["local_beats_residual_by_median"]
        if prev_local_wins != curr_local_wins:
            crossover_L = per_depth[i]["L"]
            crossover_direction = ("residual_overtakes_local" if prev_local_wins
                                    else "local_overtakes_residual")
            break

    return {
        "hypothesis": "H3: depth threshold where residual connections overtake local cost",
        "per_depth": per_depth,
        "crossover_depth_L": crossover_L,
        "crossover_direction": crossover_direction,
        "note": ("crossover_depth_L (median-based, see docstring) is the first depth "
                 "(ascending) at which the local-vs-residual median-SNR ordering flips, "
                 "in either direction (crossover_direction records which way); null if "
                 "one configuration dominates at every swept depth"),
    }


# ============================================================================
# Companion-paper phase 2: per-(task, n_qubits) grid analysis, sum-vs-mean
# sensitivity analysis, and scoped H3 analysis. All three reuse analyze_h1 /
# analyze_h2a / analyze_h2b / analyze_h3 unchanged -- those functions only
# ever look at a "config_name" column, so calling them once per grid cell
# (a df already filtered/grouped down to one (task, n_qubits) point) is all
# that's needed; no new hypothesis-testing logic here.
# ============================================================================

def analyze_pilot_finding_replication(df, metric=METRIC):
    """Checks the pilot's headline finding at a single (task, n_qubits) grid
    point: is entanglement_only the best (argmax mean seed-level SNR) of the
    7 configs, and does combined underperform baseline?
    """
    means = df.groupby("config_name")[metric].mean()
    best_config = means.idxmax()
    return {
        "best_config": best_config,
        "means": means.to_dict(),
        "entanglement_only_is_best": bool(best_config == "entanglement_only"),
        "combined_worse_than_baseline": bool(means["combined"] < means["baseline"]),
    }


def run_grid_analysis(main_grid_df, metric=METRIC):
    """Runs H1/H2a/H2b plus the pilot-finding-replication check at every
    (task, n_qubits) point in `main_grid_df`. Returns (grid_summary_df,
    full_results): `grid_summary_df` is a compact one-row-per-grid-point
    table (the basis for the heatmap deliverable), `full_results` keeps the
    complete nested H1/H2a/H2b dicts keyed by "{task}__n{n_qubits}".
    """
    rows = []
    full_results = {}
    for (task, n_qubits), sub in main_grid_df.groupby(["task", "n_qubits"]):
        h1 = analyze_h1(sub)
        h2a = analyze_h2a(sub)
        h2b = analyze_h2b(sub)
        pilot_check = analyze_pilot_finding_replication(sub, metric=metric)
        key = f"{task}__n{int(n_qubits)}"
        full_results[key] = {
            "task": task, "n_qubits": int(n_qubits),
            "H1": h1, "H2a": h2a, "H2b": h2b, "pilot_finding": pilot_check,
        }
        rows.append({
            "task": task, "n_qubits": int(n_qubits),
            "h1_combined_exceeds_all_four": h1["combined_exceeds_all_four"],
            "h2a_sum_framing_sub_additive": h2a["additivity"]["sum_framing_sub_additive"],
            "h2a_product_framing_sub_additive": h2a["additivity"]["product_framing_sub_additive"],
            "h2b_sum_framing_sub_additive": h2b["additivity"]["sum_framing_sub_additive"],
            "h2b_product_framing_sub_additive": h2b["additivity"]["product_framing_sub_additive"],
            "best_config": pilot_check["best_config"],
            "entanglement_only_is_best": pilot_check["entanglement_only_is_best"],
            "combined_worse_than_baseline": pilot_check["combined_worse_than_baseline"],
        })
    grid_summary_df = pd.DataFrame(rows).sort_values(["task", "n_qubits"]).reset_index(drop=True)
    return grid_summary_df, full_results


_SENSITIVITY_COMPARISON_COLS = [
    "h1_combined_exceeds_all_four", "h2a_sum_framing_sub_additive",
    "h2a_product_framing_sub_additive", "h2b_sum_framing_sub_additive",
    "h2b_product_framing_sub_additive", "best_config", "entanglement_only_is_best",
    "combined_worse_than_baseline",
]


def run_sensitivity_analysis(sensitivity_sum_df, sensitivity_mean_df, metric=METRIC):
    """Compares H1/H2a/H2b/pilot-finding outcomes under residual_reduction=
    'sum' vs 'mean' at the sensitivity check's grid points (n in {4,10} x all
    3 tasks): does the qualitative picture change under the n-invariant
    'mean' formulation? Returns (combined_df, diverge_df): `combined_df` has
    one row per (task, n_qubits, residual_reduction); `diverge_df` flags
    which (task, n_qubits) points disagree between the two reductions on any
    of `_SENSITIVITY_COMPARISON_COLS`.
    """
    sum_grid, _ = run_grid_analysis(sensitivity_sum_df, metric=metric)
    sum_grid["residual_reduction"] = "sum"
    mean_grid, _ = run_grid_analysis(sensitivity_mean_df, metric=metric)
    mean_grid["residual_reduction"] = "mean"
    combined_df = pd.concat([sum_grid, mean_grid], ignore_index=True)

    diverge_rows = []
    for (task, n_qubits), sub in combined_df.groupby(["task", "n_qubits"]):
        sum_row = sub[sub["residual_reduction"] == "sum"].iloc[0]
        mean_row = sub[sub["residual_reduction"] == "mean"].iloc[0]
        diverging_cols = [c for c in _SENSITIVITY_COMPARISON_COLS if sum_row[c] != mean_row[c]]
        diverge_rows.append({
            "task": task, "n_qubits": n_qubits,
            "diverges_sum_vs_mean": len(diverging_cols) > 0,
            "diverging_columns": ";".join(diverging_cols),
        })
    diverge_df = pd.DataFrame(diverge_rows).sort_values(["task", "n_qubits"]).reset_index(drop=True)
    return combined_df, diverge_df


def run_scoped_h3_analysis(depth_scoped_df):
    """H3 analysis (crossover detection, reusing analyze_h3 unchanged) at
    each n_qubits in the scoped depth sweep (spec section 6): does the
    pilot's n=4 crossover direction hold, reverse, or disappear as n grows?
    Returns {n_qubits: analyze_h3(...) result}.
    """
    results = {}
    for n_qubits, sub in depth_scoped_df.groupby("n_qubits"):
        results[int(n_qubits)] = analyze_h3(sub)
    return results


def diagnose_l1_mean_median_gap(depth_scoped_df, L=1):
    """Reports, per (n_qubits, config), the mean-vs-median gap in seed-level
    mean_snr at depth L (default 1, where the pilot noted a ~20x gap) plus
    the maximum n_deterministic_nonzero_params observed -- computed directly
    from the real per-seed data, not assumed. Distinguishes two different
    phenomena: a config where deterministic-nonzero parameters (e.g. alpha_1,
    whose input is the fixed |0...0> state) are present and the mean/median
    gap is small is a case the snr.py deterministic-parameter rule actually
    resolves; a config with a persisting large gap despite zero
    deterministic-nonzero parameters is a separate, real small-sample
    heavy-tailed phenomenon (a specific seed's shallow circuit landing
    extremely close to a cost-function eigenstate, giving a tiny-but-nonzero
    shot-noise variance) that the rule correctly does not and should not
    suppress -- see README "Design choices".
    """
    sub = depth_scoped_df[depth_scoped_df["L"] == L]
    rows = []
    for (n_qubits, config_name), grp in sub.groupby(["n_qubits", "config_name"]):
        mean_v = grp["mean_snr"].mean()
        median_v = grp["mean_snr"].median()
        rows.append({
            "n_qubits": int(n_qubits), "config_name": config_name,
            "mean_of_mean_snr": float(mean_v), "median_of_mean_snr": float(median_v),
            "mean_median_ratio": float(mean_v / median_v) if median_v else float("nan"),
            "max_n_deterministic_nonzero_params": int(grp["n_deterministic_nonzero_params"].max()),
        })
    return pd.DataFrame(rows).sort_values(["n_qubits", "config_name"]).reset_index(drop=True)


def summarize_parameter_routing(df):
    """Aggregates the per-row parameter-type/classification counts (written
    by experiment._summarize_grid) across an entire grid/sensitivity
    DataFrame: total circuit_theta vs. residual_alpha parameters seen, and
    the operationally-resolvable fraction's min/mean/max across seeds. Every
    row's underlying per-parameter data already passed
    experiment.assert_no_residual_alpha_misrouting at generation time (see
    experiment.py); this is a summary for reporting, not a re-check.
    """
    return {
        "n_rows": int(len(df)),
        "total_circuit_theta_params": int(df["n_circuit_theta_params"].sum()),
        "total_residual_alpha_params": int(df["n_residual_alpha_params"].sum()),
        "total_deterministic_nonzero_params": int(df["n_deterministic_nonzero_params"].sum()),
        "total_inactive_zero_params": int(df["n_inactive_zero_params"].sum()),
        "operationally_resolvable_fraction_min": float(df["operationally_resolvable_fraction"].min()),
        "operationally_resolvable_fraction_mean": float(df["operationally_resolvable_fraction"].mean()),
        "operationally_resolvable_fraction_max": float(df["operationally_resolvable_fraction"].max()),
    }


def run_companion_phase_analyses():
    """Reads the companion-phase-2 raw CSVs from results/ (written by
    experiment.run_companion_phase), runs the grid/sensitivity/scoped-H3
    analyses above, and writes their outputs back to results/. Does not
    touch or re-run `run_all_analyses` (the pilot's own analysis).
    """
    main_grid_df = pd.read_csv(os.path.join(RESULTS_DIR, "main_grid_summary.csv"))
    headline_df = pd.read_csv(os.path.join(RESULTS_DIR, "main_grid_headline_reference.csv"))
    sensitivity_sum_df = pd.read_csv(os.path.join(RESULTS_DIR, "sensitivity_sum_summary.csv"))
    sensitivity_mean_df = pd.read_csv(os.path.join(RESULTS_DIR, "sensitivity_mean_summary.csv"))
    depth_scoped_df = pd.read_csv(os.path.join(RESULTS_DIR, "depth_sweep_scoped_summary.csv"))

    grid_summary_df, grid_full_results = run_grid_analysis(main_grid_df)
    grid_summary_df.to_csv(os.path.join(RESULTS_DIR, "grid_hypothesis_summary.csv"), index=False)
    with open(os.path.join(RESULTS_DIR, "grid_hypothesis_results.json"), "w") as f:
        json.dump(grid_full_results, f, indent=2)

    headline_summary_df, headline_full_results = run_grid_analysis(headline_df)
    headline_summary_df.to_csv(os.path.join(RESULTS_DIR, "headline_hypothesis_summary.csv"),
                                index=False)
    with open(os.path.join(RESULTS_DIR, "headline_hypothesis_results.json"), "w") as f:
        json.dump(headline_full_results, f, indent=2)

    sensitivity_combined_df, sensitivity_diverge_df = run_sensitivity_analysis(
        sensitivity_sum_df, sensitivity_mean_df)
    sensitivity_combined_df.to_csv(
        os.path.join(RESULTS_DIR, "sensitivity_hypothesis_summary.csv"), index=False)
    sensitivity_diverge_df.to_csv(
        os.path.join(RESULTS_DIR, "sensitivity_divergence.csv"), index=False)

    h3_scoped_results = run_scoped_h3_analysis(depth_scoped_df)
    with open(os.path.join(RESULTS_DIR, "depth_sweep_scoped_hypothesis_results.json"), "w") as f:
        json.dump(h3_scoped_results, f, indent=2)

    l1_gap_diagnostic_df = diagnose_l1_mean_median_gap(depth_scoped_df)
    l1_gap_diagnostic_df.to_csv(
        os.path.join(RESULTS_DIR, "depth_sweep_scoped_l1_gap_diagnostic.csv"), index=False)

    parameter_routing_summary = summarize_parameter_routing(main_grid_df)
    with open(os.path.join(RESULTS_DIR, "parameter_routing_summary.json"), "w") as f:
        json.dump(parameter_routing_summary, f, indent=2)

    return {
        "grid_summary_df": grid_summary_df,
        "l1_gap_diagnostic_df": l1_gap_diagnostic_df,
        "parameter_routing_summary": parameter_routing_summary,
        "grid_full_results": grid_full_results,
        "headline_summary_df": headline_summary_df,
        "headline_full_results": headline_full_results,
        "sensitivity_combined_df": sensitivity_combined_df,
        "sensitivity_diverge_df": sensitivity_diverge_df,
        "h3_scoped_results": h3_scoped_results,
    }


def run_all_analyses():
    main_df = pd.read_csv(os.path.join(RESULTS_DIR, "main_experiment_summary.csv"))
    depth_df = pd.read_csv(os.path.join(RESULTS_DIR, "depth_sweep_summary.csv"))

    config_summary = summarize_configs(main_df)
    config_summary.to_csv(os.path.join(RESULTS_DIR, "config_summary.csv"), index=False)

    results = {
        "config_summary": config_summary.to_dict(orient="records"),
        "H1": analyze_h1(main_df),
        "H2a": analyze_h2a(main_df),
        "H2b": analyze_h2b(main_df),
        "H3": analyze_h3(depth_df),
    }

    with open(os.path.join(RESULTS_DIR, "hypothesis_test_results.json"), "w") as f:
        json.dump(results, f, indent=2)

    return results


if __name__ == "__main__":
    res = run_all_analyses()
    print(json.dumps(res, indent=2))
