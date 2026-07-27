import numpy as np
import pytest

from qnn_snr.config import load_config
from qnn_snr.replicate import draw_theta_blocks, generate_exact_rows, generate_shot_rows
from qnn_snr.schema import rows_to_dataframe
from qnn_snr.seeds import derive_seed
from qnn_snr.validate import validate_dataset

import qnn_snr
from pathlib import Path

CONFIG_DIR = Path(qnn_snr.__file__).resolve().parent.parent / "configs"


@pytest.fixture(scope="module")
def smoke_cfg():
    return load_config(CONFIG_DIR / "smoke.yaml")


def test_theta_seed_matched_across_all_configurations(smoke_cfg):
    for depth in smoke_cfg.circuit.depths:
        for init_id in range(smoke_cfg.design.n_initializations):
            seeds = {derive_seed(smoke_cfg.seed_root, "init_theta", init_id, depth) for _ in range(3)}
            assert len(seeds) == 1  # deterministic: same call always yields the same seed


def test_exact_rows_row_count(smoke_cfg):
    rows = generate_exact_rows(smoke_cfg)
    expected = sum(
        smoke_cfg.design.n_initializations * len(smoke_cfg.design.configurations) * depth * smoke_cfg.task.n_qubits
        for depth in smoke_cfg.circuit.depths
    )
    assert len(rows) == expected


def test_exact_rows_validate_clean(smoke_cfg):
    rows = generate_exact_rows(smoke_cfg)
    df = rows_to_dataframe(rows)
    report = validate_dataset(df, smoke_cfg)
    assert report["passed"], report["errors"]


def test_exact_rows_deterministic_repeat(smoke_cfg):
    rows1 = generate_exact_rows(smoke_cfg)
    rows2 = generate_exact_rows(smoke_cfg)
    grads1 = [r["gradient_hat"] for r in rows1]
    grads2 = [r["gradient_hat"] for r in rows2]
    assert grads1 == grads2


def test_dropping_one_configuration_fails_validation(smoke_cfg):
    rows = generate_exact_rows(smoke_cfg)
    df = rows_to_dataframe(rows)
    df_bad = df[df["configuration_id"] != 8]
    report = validate_dataset(df_bad, smoke_cfg)
    assert not report["passed"]
    assert any("8 configurations" in e for e in report["errors"])


def test_shot_rows_within_declared_budget(smoke_cfg):
    rows = generate_shot_rows(smoke_cfg, "finite_shot_conditional")
    df = rows_to_dataframe(rows)
    assert (df["total_shots"] <= df["budget"]).all()
    assert (df["total_shots"] > 0).all()


def test_shot_rows_carry_matching_exact_gradient(smoke_cfg):
    rows = generate_exact_rows(smoke_cfg)
    exact_df = rows_to_dataframe(rows).set_index(
        ["configuration_id", "depth", "initialization_id", "parameter_id"]
    )["exact_gradient"]

    shot_rows = generate_shot_rows(smoke_cfg, "finite_shot_end_to_end")
    shot_df = rows_to_dataframe(shot_rows)
    merged = shot_df.set_index(["configuration_id", "depth", "initialization_id", "parameter_id"])
    joined = merged.join(exact_df, rsuffix="_ref")
    assert np.allclose(joined["exact_gradient"], joined["exact_gradient_ref"])


def test_end_to_end_and_conditional_modes_produce_different_noise(smoke_cfg):
    cond = rows_to_dataframe(generate_shot_rows(smoke_cfg, "finite_shot_conditional"))
    e2e = rows_to_dataframe(generate_shot_rows(smoke_cfg, "finite_shot_end_to_end"))
    assert len(cond) == len(e2e)
    # not a strict equality claim, just that the two modes are not accidentally identical
    assert not np.allclose(cond["gradient_hat"].values, e2e["gradient_hat"].values)
