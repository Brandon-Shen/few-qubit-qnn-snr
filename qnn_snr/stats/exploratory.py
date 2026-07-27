"""Exploratory analyses (Section 16). Everything here is explicitly labeled
exploratory and must never be pooled into the H1-H4 Holm family or presented
as confirmatory.

Computed by default from the same generated dataset: the E:L:R three-way
interaction, whether configuration 8 exceeds the best single-intervention
configuration in SNR_est / final energy / global fidelity / circuit-cost-
normalized SNR. gamma-sensitivity, hardware-noise, and longitudinal
checkpoint analyses are *not* run by default (ASSUMPTIONS.md A6/A11) -- they
require additional generation passes outside the confirmatory pipeline and
are left as documented, configurable extensions rather than fabricated here.
"""
from __future__ import annotations

import pandas as pd

from qnn_snr.stats.models import MixedModelResult

SINGLE_INTERVENTION_CONFIGS = [2, 3, 4]  # E-only, L-only, R-only
BASELINE_CONFIG = 1
ALL_THREE_CONFIG = 8


def exploratory_three_way_interaction(h2h4_result: MixedModelResult) -> dict:
    coef = "E:L:R"
    if h2h4_result.error is not None or coef not in h2h4_result.params:
        return {"coefficient": coef, "estimate": float("nan"), "se": float("nan"), "note": "model unavailable"}
    return {
        "coefficient": coef,
        "estimate": h2h4_result.params[coef],
        "se": h2h4_result.bse.get(coef, float("nan")),
        "note": "exploratory only; not part of the H1-H4 Holm family",
    }


def exploratory_configuration_8_comparisons(configuration_summaries: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for depth, budget_df in configuration_summaries.groupby("depth"):
        for budget, cell in budget_df.groupby("budget"):
            best_single = cell[cell["configuration_id"].isin(SINGLE_INTERVENTION_CONFIGS)]
            all_three = cell[cell["configuration_id"] == ALL_THREE_CONFIG]
            baseline = cell[cell["configuration_id"] == BASELINE_CONFIG]
            if best_single.empty or all_three.empty or baseline.empty:
                continue
            best_row = best_single.loc[best_single["rms_SNR_est"].idxmax()]
            a3 = all_three.iloc[0]
            base = baseline.iloc[0]

            snr_exceeds = bool(a3["rms_SNR_est"] > best_row["rms_SNR_est"])
            energy_improves = bool(a3["final_tfim_energy_mean"] < base["final_tfim_energy_mean"])
            fidelity_improves = bool(a3["global_fidelity_mean"] > base["global_fidelity_mean"])

            a3_cost_norm = (a3["rms_SNR_est"] / a3["total_circuit_evaluations_mean"]
                             if "total_circuit_evaluations_mean" in a3 and a3.get("total_circuit_evaluations_mean", 0) else float("nan"))
            best_cost_norm = (best_row["rms_SNR_est"] / best_row["total_circuit_evaluations_mean"]
                               if "total_circuit_evaluations_mean" in best_row and best_row.get("total_circuit_evaluations_mean", 0) else float("nan"))
            cost_normalized_advantage_remains = (
                bool(a3_cost_norm > best_cost_norm) if pd.notna(a3_cost_norm) and pd.notna(best_cost_norm) else None
            )

            rows.append({
                "depth": depth, "budget": budget,
                "best_single_intervention_config": int(best_row["configuration_id"]),
                "config8_rms_SNR_est": a3["rms_SNR_est"],
                "best_single_rms_SNR_est": best_row["rms_SNR_est"],
                "config8_exceeds_best_single_SNR": snr_exceeds,
                "config8_final_energy": a3["final_tfim_energy_mean"],
                "baseline_final_energy": base["final_tfim_energy_mean"],
                "config8_energy_improves_on_baseline": energy_improves,
                "config8_global_fidelity": a3["global_fidelity_mean"],
                "baseline_global_fidelity": base["global_fidelity_mean"],
                "config8_fidelity_improves_on_baseline": fidelity_improves,
                "config8_cost_normalized_SNR": a3_cost_norm,
                "best_single_cost_normalized_SNR": best_cost_norm,
                "cost_normalized_advantage_remains": cost_normalized_advantage_remains,
                "label": "exploratory",
            })
    return pd.DataFrame(rows)


def build_exploratory_table(h2h4_result: MixedModelResult, configuration_summaries: pd.DataFrame) -> pd.DataFrame:
    three_way = exploratory_three_way_interaction(h2h4_result)
    comparisons = exploratory_configuration_8_comparisons(configuration_summaries)
    for k, v in three_way.items():
        comparisons[f"three_way_{k}"] = v if not isinstance(v, (int, float)) else v
    return comparisons
