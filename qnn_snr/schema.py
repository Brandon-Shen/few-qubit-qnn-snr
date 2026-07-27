"""Tidy replicate-level dataset schema (Section 8)."""
from __future__ import annotations

from pathlib import Path

import pandas as pd

REQUIRED_COLUMNS = [
    "experiment_id",
    "analysis_mode",
    "pilot_or_confirmatory",
    "configuration_id",
    "E",
    "L",
    "R",
    "depth",
    "depth_centered",
    "depth_z",
    "budget",
    "log2_budget",
    "initialization_id",
    "initialization_seed",
    "parameter_id",
    "parameter_index",
    "block_index",
    "qubit_index",
    "replicate_id",
    "gradient_hat",
    "exact_gradient",
    "cost_type",
    "gamma",
    "total_shots",
    "total_circuit_evaluations",
    "quantum_framework",
    "simulator_backend",
    "software_version",
    "git_commit",
    "config_hash",
]


def rows_to_dataframe(rows: list[dict]) -> pd.DataFrame:
    df = pd.DataFrame(rows)
    missing = [c for c in REQUIRED_COLUMNS if c not in df.columns]
    if missing:
        raise ValueError(f"generated rows are missing required columns: {missing}")
    return df[REQUIRED_COLUMNS]


def write_tidy_dataset(rows: list[dict], path: str | Path) -> pd.DataFrame:
    df = rows_to_dataframe(rows)
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    df.to_parquet(path, index=False)
    return df


def read_tidy_dataset(path: str | Path) -> pd.DataFrame:
    return pd.read_parquet(path)
