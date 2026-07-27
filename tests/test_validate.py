import numpy as np
import pandas as pd
import pytest

from qnn_snr.config import CONFIGURATION_TABLE, ExperimentConfig
from qnn_snr.schema import REQUIRED_COLUMNS
from qnn_snr.validate import validate_dataset


def _minimal_clean_df(n_params=2, n_init=2):
    rows = []
    for init_id in range(n_init):
        for config_id, (E, L, R) in CONFIGURATION_TABLE.items():
            for p in range(n_params):
                rows.append({
                    "experiment_id": "exp", "analysis_mode": "statevector_exact",
                    "pilot_or_confirmatory": "confirmatory", "configuration_id": config_id,
                    "E": E, "L": L, "R": R, "depth": 2, "depth_centered": 0.0, "depth_z": 0.0,
                    "budget": 0, "log2_budget": float("nan"), "initialization_id": init_id,
                    "initialization_seed": 1, "parameter_id": f"theta_{p}", "parameter_index": p,
                    "block_index": 1, "qubit_index": p, "replicate_id": 0,
                    "gradient_hat": 0.1 * p, "exact_gradient": 0.1 * p, "cost_type": "global",
                    "gamma": 0.0, "total_shots": 0, "total_circuit_evaluations": 0,
                    "quantum_framework": "pennylane", "simulator_backend": "default.qubit",
                    "software_version": "x", "git_commit": "abc", "config_hash": "hash",
                })
    return pd.DataFrame(rows)[REQUIRED_COLUMNS]


def test_clean_dataset_passes():
    df = _minimal_clean_df()
    report = validate_dataset(df, ExperimentConfig())
    assert report["passed"], report["errors"]


def test_wrong_E_L_R_fails():
    df = _minimal_clean_df()
    df.loc[df["configuration_id"] == 2, "E"] = 0  # config 2 should have E=1
    report = validate_dataset(df, ExperimentConfig())
    assert not report["passed"]
    assert any("inconsistent" in e for e in report["errors"])


def test_duplicate_replicate_key_fails():
    df = _minimal_clean_df()
    dup = df.iloc[[0]].copy()
    df = pd.concat([df, dup], ignore_index=True)
    report = validate_dataset(df, ExperimentConfig())
    assert not report["passed"]
    assert any("duplicate" in e for e in report["errors"])


def test_missing_values_fail():
    df = _minimal_clean_df()
    df.loc[0, "gradient_hat"] = np.nan
    report = validate_dataset(df, ExperimentConfig())
    assert not report["passed"]
    assert any("missing values" in e for e in report["errors"])


def test_inconsistent_exact_gradient_fails():
    df = _minimal_clean_df()
    # add a second replicate of row 0's cell with a mismatched exact_gradient
    extra = df.iloc[[0]].copy()
    extra["replicate_id"] = 1
    extra["exact_gradient"] = 999.0
    df = pd.concat([df, extra], ignore_index=True)
    report = validate_dataset(df, ExperimentConfig())
    assert not report["passed"]
    assert any("inconsistent exact_gradient" in e for e in report["errors"])


def test_shots_exceeding_budget_fails():
    df = _minimal_clean_df()
    df["analysis_mode"] = "finite_shot_conditional"
    df["budget"] = 100
    df.loc[0, "total_shots"] = 500
    report = validate_dataset(df, ExperimentConfig())
    assert not report["passed"]
    assert any("exceeding" in e for e in report["errors"])


def test_bad_pilot_flag_fails():
    df = _minimal_clean_df()
    df.loc[0, "pilot_or_confirmatory"] = "maybe"
    report = validate_dataset(df, ExperimentConfig())
    assert not report["passed"]
    assert any("pilot_or_confirmatory" in e for e in report["errors"])
