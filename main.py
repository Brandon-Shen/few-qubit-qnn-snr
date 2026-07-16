"""End-to-end orchestration: run the experiment, analyze it, plot it, and
write RESULTS.md. `python main.py` is the single entry point for the whole
project.
"""
import json
import os
import time

import experiment
import analysis
import plots

RESULTS_DIR = os.path.join(os.path.dirname(__file__), "results")


def _fmt_p(p):
    if p is None:
        return "n/a"
    return f"{p:.4f}" if p >= 0.0001 else f"{p:.2e}"


def write_results_md(hyp_results, runtime_info):
    h1, h2a, h2b, h3 = hyp_results["H1"], hyp_results["H2a"], hyp_results["H2b"], hyp_results["H3"]
    config_summary = {row["config_name"]: row for row in hyp_results["config_summary"]}

    lines = []
    lines.append("# Results\n")
    lines.append(f"Total experiment runtime: **{runtime_info['total_seconds']:.1f}s** "
                  f"(main experiment {runtime_info['main_experiment_seconds']:.1f}s, "
                  f"depth sweep {runtime_info['depth_sweep_seconds']:.1f}s).\n")

    lines.append("## Configuration summary (mean gradient SNR across 50 seeds, L=3)\n")
    lines.append("| # | Configuration | Mean SNR | Median SNR | Std |")
    lines.append("|---|---|---|---|---|")
    order = ["baseline", "entanglement_only", "local_cost_only", "residual_only",
              "entanglement_local", "entanglement_residual", "combined"]
    for i, name in enumerate(order, start=1):
        row = config_summary[name]
        lines.append(f"| {i} | {row['config_label']} | {row['mean_of_seed_means']:.3f} "
                      f"| {row['median_of_seed_means']:.3f} | {row['std_of_seed_means']:.3f} |")
    lines.append("")

    lines.append("## H1: does the combined configuration (7) beat configs 1-4 individually?\n")
    if h1["combined_exceeds_all_four"]:
        result_text = ("**Result: YES** -- combined mean SNR exceeds all four individual/"
                        "no-mitigation baselines")
    else:
        beats = [c["config_b"] for c in h1["comparisons"] if c["a_greater_than_b"]]
        beats_text = ", ".join(beats) if beats else "none of them"
        result_text = (f"**Result: NO** -- combined mean SNR does *not* exceed all four "
                        f"individual baselines (it only exceeds: {beats_text})")
    sig_text = ("all differences significant at p<0.05" if h1["all_differences_significant_p<0.05"]
                else "not all differences are significant at p<0.05")
    lines.append(f"{result_text} ({sig_text}).\n")
    lines.append("| vs. config | mean(combined) | mean(other) | Wilcoxon p | combined > other |")
    lines.append("|---|---|---|---|---|")
    for c in h1["comparisons"]:
        lines.append(f"| {c['config_b']} | {c['mean_a']:.3f} | {c['mean_b']:.3f} "
                      f"| {_fmt_p(c['pvalue'])} | {c['a_greater_than_b']} |")
    lines.append("")

    def additivity_block(h, cfg5_name, cfg5_label):
        a = h["additivity"]
        lines.append(f"- Gain over baseline: entanglement alone = {a['gain_a_over_baseline']:.3f}, "
                      f"other factor alone = {a['gain_b_over_baseline']:.3f}, "
                      f"{cfg5_label} actual = {a['gain_combined_over_baseline_actual']:.3f}")
        lines.append(f"- **Sum framing**: additive prediction = {a['sum_framing_additive_prediction']:.3f} "
                      f"-> {'sub-additive' if a['sum_framing_sub_additive'] else 'super-additive/additive'} "
                      f"(actual {'<' if a['sum_framing_sub_additive'] else '>='} prediction)")
        lines.append(f"- **Product/ratio framing**: multiplicative prediction = "
                      f"{a['product_framing_multiplicative_prediction']:.3f}x -> "
                      f"{'sub-additive' if a['product_framing_sub_additive'] else 'super-additive/additive'} "
                      f"(actual ratio {a['ratio_combined_over_baseline_actual']:.3f}x)")

    lines.append("## H2a: entanglement + local cost (config 5) vs. entanglement (2) and local cost (3) alone\n")
    c1, c2 = h2a["wilcoxon_config5_vs_config2"], h2a["wilcoxon_config5_vs_config3"]
    lines.append(f"- Wilcoxon config 5 vs. config 2: mean {c1['mean_a']:.3f} vs {c1['mean_b']:.3f}, "
                  f"p = {_fmt_p(c1['pvalue'])}")
    lines.append(f"- Wilcoxon config 5 vs. config 3: mean {c2['mean_a']:.3f} vs {c2['mean_b']:.3f}, "
                  f"p = {_fmt_p(c2['pvalue'])}")
    additivity_block(h2a, "entanglement_local", "config 5")
    lines.append("")

    lines.append("## H2b: entanglement + residual (config 6) vs. entanglement (2) and residual (4) alone\n")
    c1, c2 = h2b["wilcoxon_config6_vs_config2"], h2b["wilcoxon_config6_vs_config4"]
    lines.append(f"- Wilcoxon config 6 vs. config 2: mean {c1['mean_a']:.3f} vs {c1['mean_b']:.3f}, "
                  f"p = {_fmt_p(c1['pvalue'])}")
    lines.append(f"- Wilcoxon config 6 vs. config 4: mean {c1['mean_a']:.3f} vs {c2['mean_b']:.3f}, "
                  f"p = {_fmt_p(c2['pvalue'])}")
    additivity_block(h2b, "entanglement_residual", "config 6")
    lines.append("")

    lines.append("## H3: depth-dependence of local-cost vs. residual mitigation\n")
    lines.append("Seed-level SNR is heavy-tailed (a near-deterministic shallow circuit can send "
                  "one parameter's shot-noise variance close to zero while its gradient stays "
                  "finite, producing an SNR blowup for that single seed) -- the crossover below "
                  "is therefore located using the **median** across seeds, matching "
                  "`results/plots/snr_vs_depth.png` (log-scale, median + IQR). Per-depth means "
                  "are also reported for transparency but can be pulled far above the bulk of the "
                  "distribution by such outliers.\n")
    if h3["crossover_depth_L"] is not None:
        if h3["crossover_direction"] == "local_overtakes_residual":
            lines.append(f"**Crossover found at L = {h3['crossover_depth_L']}**: residual-only's "
                          f"median SNR dominates at shallower depth and local-cost-only's median "
                          f"SNR dominates from this depth onward -- the **opposite** direction from "
                          f"the H3 hypothesis (which predicted local-cost dominating shallow, "
                          f"residual dominating deep), within the swept depths "
                          f"{sorted({d['L'] for d in h3['per_depth']})}.\n")
        else:
            lines.append(f"**Crossover found at L = {h3['crossover_depth_L']}**: local-cost-only's "
                          f"median SNR dominates at shallower depths and residual-only's median SNR "
                          f"dominates from this depth onward, matching the H3 hypothesis direction, "
                          f"within the swept depths {sorted({d['L'] for d in h3['per_depth']})}.\n")
    else:
        lines.append("**No crossover found** within the swept depths -- one configuration dominates "
                      "at every depth tested by the median criterion (see table below).\n")
    lines.append("| L | median SNR (local) | median SNR (residual) | median SNR (local+residual) | mean SNR (local) | mean SNR (residual) | local > residual (median) |")
    lines.append("|---|---|---|---|---|---|---|")
    for d in h3["per_depth"]:
        lines.append(f"| {d['L']} | {d['median_local_cost_only']:.3f} | {d['median_residual_only']:.3f} "
                      f"| {d['median_local_and_residual']:.3f} | {d['mean_local_cost_only']:.3f} "
                      f"| {d['mean_residual_only']:.3f} | {d['local_beats_residual_by_median']} |")
    lines.append("")

    lines.append("## Notes\n")
    lines.append("- All comparisons use the Wilcoxon signed-rank test on 50 paired seed-level "
                  "mean-SNR values (identical seeds -> identical theta draws across configurations).")
    lines.append("- Full per-parameter raw data: `results/main_experiment_per_parameter.json`, "
                  "`results/depth_sweep_per_parameter.json`.")
    lines.append("- Landscape gradient variance (Var_theta across seeds, secondary measure): "
                  "`results/main_landscape_variance.csv`.")
    lines.append("- Plots: `results/plots/`.")

    out_path = os.path.join(os.path.dirname(__file__), "RESULTS.md")
    with open(out_path, "w") as f:
        f.write("\n".join(lines) + "\n")
    print(f"Wrote {out_path}")


def main():
    t0 = time.time()
    experiment.main()
    hyp_results = analysis.run_all_analyses()
    plots.generate_all_plots()

    with open(os.path.join(RESULTS_DIR, "runtime.json")) as f:
        runtime_info = json.load(f)
    write_results_md(hyp_results, runtime_info)

    total = time.time() - t0
    print(f"\nEnd-to-end total wall time (including analysis + plotting): {total:.1f}s")


if __name__ == "__main__":
    main()
