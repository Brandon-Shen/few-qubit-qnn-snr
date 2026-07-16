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
