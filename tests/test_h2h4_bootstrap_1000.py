from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]


def test_final_h2h4_bootstrap_has_exactly_1000_unique_valid_fits():
    draws = pd.read_parquet(ROOT / "results/production_corrected_end_to_end/bootstrap_end_to_end_h2_h4_iterations.parquet")
    assert len(draws) == 1000
    assert draws.global_iteration_id.nunique() == 1000
    assert draws.global_iteration_id.tolist() == list(range(1000))
    assert draws.converged.all()
    assert draws.valid_for_percentile.all()
    assert set(draws.fit_status) == {"successful"}
    assert set(draws._stream).isdisjoint({"regression_b"})


def test_final_h2h4_intervals_use_1000_draws():
    summary = pd.read_csv(ROOT / "results/production_corrected_end_to_end/bootstrap_end_to_end_h2_h4_summary.csv")
    assert set(summary.n_successful) == {1000}
    assert set(summary.n_rejected) == {0}
    assert len(summary) == 3
    current = pd.read_csv(ROOT / "results/primary_corrected/effect_coded/corrected_bootstrap_intervals_current_draws.csv")
    assert set(current.query("hypothesis in ['H2','H3','H4']").completed_bootstrap_iterations) == {1000}
