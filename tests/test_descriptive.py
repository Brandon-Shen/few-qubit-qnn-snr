import pandas as pd
import pytest

import qnn_snr
from pathlib import Path

from qnn_snr.config import load_config
from qnn_snr.replicate import generate_exact_rows, generate_shot_rows
from qnn_snr.schema import rows_to_dataframe
from qnn_snr.stats.descriptive import configuration_summaries, physics_summary_rows, resource_accounting_table
from qnn_snr.stats.pointwise import pointwise_statistics

CONFIG_DIR = Path(qnn_snr.__file__).resolve().parent.parent / "configs"


@pytest.fixture(scope="module")
def smoke_cfg():
    return load_config(CONFIG_DIR / "smoke.yaml")


def test_physics_summary_rows_covers_all_cells(smoke_cfg):
    rows = physics_summary_rows(smoke_cfg)
    expected = len(smoke_cfg.circuit.depths) * smoke_cfg.design.n_initializations * len(smoke_cfg.design.configurations)
    assert len(rows) == expected
    for r in rows:
        assert 0.0 <= r["global_fidelity"] <= 1.0 + 1e-9
        assert r["mean_entanglement_entropy"] >= -1e-9


def test_configuration_summaries_shape(smoke_cfg):
    exact_df = rows_to_dataframe(generate_exact_rows(smoke_cfg))
    shot_df = rows_to_dataframe(generate_shot_rows(smoke_cfg, "finite_shot_end_to_end"))
    pw = pointwise_statistics(shot_df, bootstrap_iterations=20)
    physics_df = pd.DataFrame(physics_summary_rows(smoke_cfg))
    summary = configuration_summaries(pw, exact_df, physics_df)
    assert set(summary["configuration_id"].unique()) == set(range(1, 9))
    assert (summary["n_matched_observations"] > 0).all()


def test_configuration_summaries_with_resource_table(smoke_cfg):
    exact_df = rows_to_dataframe(generate_exact_rows(smoke_cfg))
    shot_df = rows_to_dataframe(generate_shot_rows(smoke_cfg, "finite_shot_end_to_end"))
    pw = pointwise_statistics(shot_df, bootstrap_iterations=20)
    physics_df = pd.DataFrame(physics_summary_rows(smoke_cfg))
    resource_table = resource_accounting_table(shot_df)
    summary = configuration_summaries(pw, exact_df, physics_df, resource_table)
    assert "total_circuit_evaluations_mean" in summary.columns
    assert (summary["total_circuit_evaluations_mean"] > 0).all()


def test_resource_accounting_table(smoke_cfg):
    shot_df = rows_to_dataframe(generate_shot_rows(smoke_cfg, "finite_shot_conditional"))
    acc = resource_accounting_table(shot_df)
    assert (acc["total_shots_mean"] > 0).all()
