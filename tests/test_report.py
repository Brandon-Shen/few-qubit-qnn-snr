import pandas as pd

from qnn_snr.config import ExperimentConfig
from qnn_snr.report import generate_results_summary, write_assumptions_snapshot, write_statistical_methods


def _confirmatory_table():
    return pd.DataFrame([
        {"hypothesis": "H1", "coefficient_label": "eta_EL", "estimate": -0.5, "p_holm": 0.01,
         "reject_after_holm": True, "bootstrap_ci_lo": -0.8, "bootstrap_ci_hi": -0.2,
         "interpretation": "Rejected H0; CI entirely below zero (sub-additive)."},
        {"hypothesis": "H2", "coefficient_label": "beta_EL", "estimate": 0.1, "p_holm": 0.6,
         "reject_after_holm": False, "bootstrap_ci_lo": -0.3, "bootstrap_ci_hi": 0.4,
         "interpretation": "Failed to reject H0 after Holm correction; not evidence of additivity."},
        {"hypothesis": "H3", "coefficient_label": "beta_ER", "estimate": 0.05, "p_holm": 0.7,
         "reject_after_holm": False, "bootstrap_ci_lo": -0.2, "bootstrap_ci_hi": 0.3,
         "interpretation": "Failed to reject H0 after Holm correction; not evidence of additivity."},
        {"hypothesis": "H4", "coefficient_label": "beta_LRd", "estimate": 0.02, "p_holm": 0.9,
         "reject_after_holm": False, "bootstrap_ci_lo": -0.1, "bootstrap_ci_hi": 0.15,
         "interpretation": "Failed to reject H0 after Holm correction; not evidence of additivity."},
    ])


def test_results_summary_distinguishes_rejection_from_failure_to_reject():
    table = _confirmatory_table()
    interactions = pd.DataFrame([{"pair": "E_L", "I_AB": 0.7, "I_AB_undefined_reason": None,
                                   "interpretation": "sub-additive fold change"}])
    summaries = pd.DataFrame([{"configuration_id": 1, "final_tfim_energy_mean": -3.0,
                                "global_fidelity_mean": 0.5, "rms_SNR_est": 1.0, "n_matched_observations": 10}])
    exploratory = pd.DataFrame([{"config8_exceeds_best_single_SNR": True}])
    text = generate_results_summary(table, interactions, summaries, exploratory, ExperimentConfig())

    assert "rejected" in text
    assert "not rejected" in text
    assert "not evidence" in text.lower()
    assert "exact-gradient signal" in text
    assert "estimator-SNR" in text
    assert "exploratory" in text.lower()


def test_write_assumptions_snapshot_and_methods(tmp_path):
    p1 = write_assumptions_snapshot(tmp_path)
    p2 = write_statistical_methods(tmp_path)
    assert p1.exists() and p1.read_text(encoding="utf-8").startswith("# Implementation assumptions")
    assert p2.exists() and "Holm-Bonferroni" in p2.read_text(encoding="utf-8")
