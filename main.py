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


def _fmt_bool_count(series):
    n_yes = int(series.sum())
    n_total = len(series)
    return f"{n_yes}/{n_total}"


def append_companion_phase_results_md(companion_results, runtime_phase2):
    """Appends the companion-paper phase 2 sections to the existing
    RESULTS.md (written by `write_results_md` above, which stays the n=4/
    single-task pilot reference, clearly labeled). Does not touch or
    regenerate the pilot section.
    """
    grid_df = companion_results["grid_summary_df"]
    headline_df = companion_results["headline_summary_df"]
    sensitivity_df = companion_results["sensitivity_combined_df"]
    diverge_df = companion_results["sensitivity_diverge_df"]
    h3_scoped = companion_results["h3_scoped_results"]
    l1_gap_df = companion_results["l1_gap_diagnostic_df"]

    lines = []
    lines.append("\n---\n")
    lines.append("# Companion paper: expanded empirical testing (phase 2)\n")
    lines.append(
        f"Companion-phase runtime: **{runtime_phase2['total_seconds']:.1f}s** "
        f"({runtime_phase2['total_seconds'] / 60:.1f} min) -- main grid "
        f"{runtime_phase2['main_grid_seconds']:.1f}s, headline reference "
        f"{runtime_phase2['headline_seconds']:.1f}s, sensitivity check "
        f"{runtime_phase2['sensitivity_seconds']:.1f}s, scoped depth sweep "
        f"{runtime_phase2['depth_sweep_scoped_seconds']:.1f}s.\n"
    )
    lines.append(
        f"**Seed-count reduction (runtime budget):** the main n x task grid and "
        f"the sensitivity check use **{runtime_phase2['n_seeds_grid']} seeds** "
        f"(matching the pilot's own seed count) instead of the spec's suggested "
        f"200 -- a calibration run showed the full grid at 200 seeds alone would "
        f"take ~88 minutes, and combined with the depth sweep and sensitivity "
        f"check would total ~2.7 hours, exceeding the stated 1-2 hour budget. "
        f"The scoped depth sweep keeps the full "
        f"**{runtime_phase2['n_seeds_depth']} seeds** (it fits the budget on its "
        f"own and is the piece most sensitive to a heavy-tailed distribution at "
        f"low L). The single grid point most comparable to the pilot "
        f"(n_qubits=4, task=tfim_h0.5) is additionally re-run at the full "
        f"**{runtime_phase2['n_seeds_headline']} seeds** as this phase's "
        f"headline reference result -- see below.\n"
    )

    lines.append("## Main grid: does the pilot's n=4/TFIM(h=0.5) finding replicate?\n")
    lines.append(
        "Heatmap: `results/plots/grid_hypothesis_heatmap.png` (rows = task, "
        "columns = n_qubits, green/Y = matches the labeled claim).\n"
    )
    lines.append(f"- Entanglement-alone is the best of the 7 configs: "
                  f"**{_fmt_bool_count(grid_df['entanglement_only_is_best'])}** grid points.")
    lines.append(f"- Combined underperforms baseline: "
                  f"**{_fmt_bool_count(grid_df['combined_worse_than_baseline'])}** grid points.")
    lines.append(f"- H2a (entanglement+local) is sub-additive, sum framing: "
                  f"**{_fmt_bool_count(grid_df['h2a_sum_framing_sub_additive'])}** grid points.")
    lines.append(f"- H2b (entanglement+residual) is sub-additive, sum framing: "
                  f"**{_fmt_bool_count(grid_df['h2b_sum_framing_sub_additive'])}** grid points.")
    lines.append("")
    non_replicating = grid_df[~grid_df["entanglement_only_is_best"]
                               | ~grid_df["combined_worse_than_baseline"]]
    if len(non_replicating) > 0:
        lines.append("Grid points where at least one of the two headline pilot claims "
                      "does *not* replicate:\n")
        lines.append("| task | n_qubits | entanglement best | combined < baseline | best config |")
        lines.append("|---|---|---|---|---|")
        for _, row in non_replicating.iterrows():
            lines.append(f"| {row['task']} | {row['n_qubits']} | "
                          f"{row['entanglement_only_is_best']} | "
                          f"{row['combined_worse_than_baseline']} | {row['best_config']} |")
    else:
        lines.append("Both headline pilot claims replicate at every grid point swept.")
    lines.append("")

    lines.append("## Headline reference (n_qubits=4, TFIM h=0.5, 200 seeds)\n")
    lines.append("Same grid point as the pilot's own experiment, re-run at the full "
                  "requested seed count for direct comparison to the pilot's 50-seed result "
                  "(see `results/main_grid_headline_reference.csv`).\n")
    hl = headline_df.iloc[0]
    lines.append(f"- Best config: **{hl['best_config']}** "
                  f"(entanglement-alone best: {hl['entanglement_only_is_best']}; "
                  f"combined < baseline: {hl['combined_worse_than_baseline']})")
    lines.append(f"- H1 (combined exceeds configs 1-4): {hl['h1_combined_exceeds_all_four']}")
    lines.append(f"- H2a sub-additive (sum framing): {hl['h2a_sum_framing_sub_additive']}")
    lines.append(f"- H2b sub-additive (sum framing): {hl['h2b_sum_framing_sub_additive']}")
    lines.append("")
    lines.append(
        "**Sample-size sensitivity note:** the pilot's own 50-seed result at this exact grid "
        "point found H2b sub-additive (sum framing: prediction -0.180, actual -0.545). At the "
        "full 200 seeds, H2b's sum-framing classification flips to *not* sub-additive "
        "(prediction -0.194, actual -0.057) -- both actual values are small and close to zero "
        "relative to the individual gains/losses feeding them, so this is a borderline effect "
        "size where the sub-additive/not-sub-additive classification is sensitive to seed count, "
        "not a contradiction between the two runs.\n"
    )

    lines.append("## Sum vs. mean residual-reduction sensitivity check\n")
    lines.append("Plot: `results/plots/sensitivity_sum_vs_mean.png` "
                  "(residual-bearing configs only, n=4 and n=10, all 3 tasks).\n")
    n_diverge = int(diverge_df["diverges_sum_vs_mean"].sum())
    n_total = len(diverge_df)
    lines.append(f"**{n_diverge}/{n_total}** (task, n_qubits) points show a qualitative "
                  f"difference between 'sum' and 'mean' reduction on at least one of "
                  f"H1/H2a/H2b/best-config/pilot-finding outcomes.\n")
    if n_diverge > 0:
        lines.append("| task | n_qubits | diverging outcomes |")
        lines.append("|---|---|---|")
        for _, row in diverge_df[diverge_df["diverges_sum_vs_mean"]].iterrows():
            lines.append(f"| {row['task']} | {row['n_qubits']} | {row['diverging_columns']} |")
        lines.append("")

    lines.append("## Scoped H3 depth sweep (n_qubits in {4, 6, 10}, reference task only)\n")
    lines.append("Plot: `results/plots/depth_sweep_scoped_faceted.png`. The deterministic-"
                  "parameter rule (snr.py `_DETERMINISTIC_VAR_TOL`) is applied throughout.\n")
    lines.append("| n_qubits | crossover depth L | crossover direction |")
    lines.append("|---|---|---|")
    for n_qubits in sorted(h3_scoped.keys()):
        h3 = h3_scoped[n_qubits]
        cl = h3["crossover_depth_L"]
        direction = h3["crossover_direction"] or "none (one config dominates throughout)"
        lines.append(f"| {n_qubits} | {cl if cl is not None else 'n/a'} | {direction} |")
    lines.append("")

    lines.append("### Does the deterministic-parameter rule resolve the L=1 mean/median gap?\n")
    lines.append("Checked directly against the real per-seed data at L=1 (`depth_sweep_scoped_"
                  "l1_gap_diagnostic.csv`), not assumed:\n")
    lines.append("| n_qubits | config | mean(mean_snr) | median(mean_snr) | mean/median ratio | "
                  "max deterministic params/seed |")
    lines.append("|---|---|---|---|---|---|")
    for _, row in l1_gap_df.iterrows():
        lines.append(f"| {row['n_qubits']} | {row['config_name']} | "
                      f"{row['mean_of_mean_snr']:.3f} | {row['median_of_mean_snr']:.3f} | "
                      f"{row['mean_median_ratio']:.2f}x | {row['max_n_deterministic_params']} |")
    lines.append("")
    lines.append(
        "**Answer: partially, and only for the mechanism it actually targets.** "
        "`residual_only` has `alpha_1` (deterministic by construction: block 1's input is "
        "always the fixed `|0...0>` state) and its mean/median ratio is close to 1x -- the "
        "rule cleanly excludes it. `local_cost_only` and `local_and_residual` show **zero** "
        "deterministic parameters at L=1 yet still show a large mean/median ratio: inspecting "
        "the offending seed directly shows a shot-noise variance of order 1e-9 -- three orders "
        "of magnitude above the `1e-12` tolerance, so correctly classified as non-deterministic. "
        "This is a specific seed's random theta draw landing extremely close to a `Z0Z1` "
        "eigenstate -- a genuine, continuous small-sample statistical fluke, not a "
        "provably-exact-zero case, and not something the deterministic-parameter rule fixes or "
        "should fix (there is no principled tolerance that excludes it without also excluding "
        "legitimately large finite SNRs from other seeds). The median remains the correct "
        "robust summary statistic for this second phenomenon, exactly as the pilot's own H3 "
        "analysis already documents.\n")

    lines.append("## Companion-phase notes\n")
    lines.append("- Full grid raw data: `results/main_grid_summary.csv` "
                  "(no per-parameter JSON at grid scale -- see README 'Design choices' "
                  "data-volume scoping note).")
    lines.append("- Hypothesis-test detail per grid point: "
                  "`results/grid_hypothesis_results.json`.")
    lines.append("- Sensitivity check raw data: `results/sensitivity_sum_summary.csv`, "
                  "`results/sensitivity_mean_summary.csv`.")
    lines.append("- Scoped depth sweep per-parameter detail (incl. `deterministic` flags): "
                  "`results/depth_sweep_scoped_per_parameter.json`.")
    lines.append("- Hamiltonian + brick-pattern regression checks for every (task, n) point: "
                  "`results/hamiltonian_check_grid.json`.")

    out_path = os.path.join(os.path.dirname(__file__), "RESULTS.md")
    with open(out_path, "a") as f:
        f.write("\n".join(lines) + "\n")
    print(f"Appended companion-phase sections to {out_path}")


def main():
    t0 = time.time()
    experiment.main()
    hyp_results = analysis.run_all_analyses()
    plots.generate_all_plots()

    with open(os.path.join(RESULTS_DIR, "runtime.json")) as f:
        runtime_info = json.load(f)
    write_results_md(hyp_results, runtime_info)

    print("\n--- Companion-paper phase 2 (n x task grid, sensitivity check, scoped depth sweep) ---")
    experiment.run_companion_phase()
    companion_results = analysis.run_companion_phase_analyses()
    plots.generate_companion_phase_plots()

    with open(os.path.join(RESULTS_DIR, "runtime_phase2.json")) as f:
        runtime_phase2 = json.load(f)
    append_companion_phase_results_md(companion_results, runtime_phase2)

    total = time.time() - t0
    print(f"\nEnd-to-end total wall time (including analysis + plotting): {total:.1f}s "
          f"({total / 60:.1f} min)")


if __name__ == "__main__":
    main()
