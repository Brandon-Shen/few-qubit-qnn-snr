import pandas as pd

from qnn_snr.stats.exploratory import build_exploratory_table, exploratory_three_way_interaction
from qnn_snr.stats.models import MixedModelResult


def _mock_result(params, bse):
    return MixedModelResult(
        formula="mock", converged=True, optimizer_used="lbfgs", attempted_optimizers=["lbfgs"],
        params=params, bse=bse, cov_params=None, random_effect_variances={}, n_obs=10,
        n_groups=5, n_vc_levels=5, condition_number=1.0, singular_fit=False,
        residual_diagnostics={}, raw_result=None, error=None,
    )


def _config_summary_row(config_id, depth, budget, rms_snr, energy, fidelity, cost):
    return {
        "configuration_id": config_id, "depth": depth, "budget": budget,
        "rms_SNR_est": rms_snr, "final_tfim_energy_mean": energy,
        "global_fidelity_mean": fidelity, "total_circuit_evaluations_mean": cost,
    }


def test_three_way_interaction_labeled_exploratory():
    result = _mock_result({"E:L:R": 0.2}, {"E:L:R": 0.1})
    out = exploratory_three_way_interaction(result)
    assert out["coefficient"] == "E:L:R"
    assert "exploratory" in out["note"]


def test_config8_comparison_detects_snr_advantage():
    rows = [
        _config_summary_row(1, 2, 500, 1.0, -3.0, 0.5, 100),
        _config_summary_row(2, 2, 500, 1.5, -3.1, 0.55, 100),
        _config_summary_row(3, 2, 500, 1.2, -3.05, 0.52, 100),
        _config_summary_row(4, 2, 500, 1.1, -3.0, 0.5, 100),
        _config_summary_row(8, 2, 500, 2.0, -3.3, 0.7, 200),
    ]
    df = pd.DataFrame(rows)
    result = _mock_result({"E:L:R": 0.1}, {"E:L:R": 0.1})
    out = build_exploratory_table(result, df)
    assert len(out) == 1
    row = out.iloc[0]
    assert row["config8_exceeds_best_single_SNR"] == True
    assert row["config8_energy_improves_on_baseline"] == True
    assert row["config8_fidelity_improves_on_baseline"] == True
    assert row["label"] == "exploratory"
