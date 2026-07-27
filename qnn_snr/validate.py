"""Validation command (Section 8): fails loudly before any analysis runs if
the tidy dataset does not satisfy the matched-factorial-design invariants."""
from __future__ import annotations

import numpy as np
import pandas as pd

from qnn_snr.config import CONFIGURATION_TABLE, ExperimentConfig


def validate_dataset(df: pd.DataFrame, cfg: ExperimentConfig) -> dict:
    errors: list[str] = []
    warnings: list[str] = []

    # 1. required values missing / non-finite
    numeric_required = ["E", "L", "R", "depth", "budget", "gradient_hat", "exact_gradient",
                         "total_shots", "total_circuit_evaluations"]
    for col in numeric_required:
        if col not in df.columns:
            errors.append(f"missing required column: {col}")
            continue
        if df[col].isna().any():
            errors.append(f"column {col} has {int(df[col].isna().sum())} missing values")
        if not np.isfinite(pd.to_numeric(df[col], errors="coerce")).all():
            errors.append(f"column {col} has non-finite values")

    # 2. E/L/R match the configuration table
    for config_id, (E, L, R) in CONFIGURATION_TABLE.items():
        sub = df[df["configuration_id"] == config_id]
        if sub.empty:
            continue
        bad = sub[(sub["E"] != E) | (sub["L"] != L) | (sub["R"] != R)]
        if not bad.empty:
            errors.append(f"configuration_id={config_id} has {len(bad)} rows with E/L/R "
                           f"inconsistent with the canonical table ({E},{L},{R})")

    # 3. all eight factorial cells present per (analysis_mode, depth, budget, initialization_id)
    confirmatory = df[df["pilot_or_confirmatory"] == "confirmatory"]
    group_cols = ["analysis_mode", "depth", "budget", "initialization_id"]
    if not confirmatory.empty:
        present = confirmatory.groupby(group_cols)["configuration_id"].apply(lambda s: set(s.unique()))
        expected = set(CONFIGURATION_TABLE.keys())
        incomplete = present[present.apply(lambda s: s != expected)]
        if not incomplete.empty:
            errors.append(f"{len(incomplete)} (mode, depth, budget, initialization) cells are missing "
                           f"one or more of the 8 configurations")

    # 4. matched initialization/parameter IDs present across all 8 conditions
    if not confirmatory.empty:
        key_cols = ["analysis_mode", "depth", "budget", "initialization_id", "parameter_id"]
        counts = confirmatory.groupby(key_cols)["configuration_id"].nunique()
        mismatched = counts[counts != len(CONFIGURATION_TABLE)]
        if not mismatched.empty:
            errors.append(f"{len(mismatched)} (mode, depth, budget, initialization, parameter) keys "
                           f"do not appear in all 8 configurations")

    # 5. duplicate replicate keys
    replicate_key = ["analysis_mode", "configuration_id", "depth", "budget", "initialization_id",
                      "parameter_id", "replicate_id"]
    if all(c in df.columns for c in replicate_key):
        dup = df.duplicated(subset=replicate_key, keep=False)
        if dup.any():
            errors.append(f"{int(dup.sum())} duplicate replicate keys found")

    # 6. pilot data must not enter the confirmatory dataset
    if "pilot_or_confirmatory" in df.columns:
        bad_values = set(df["pilot_or_confirmatory"].unique()) - {"pilot", "confirmatory"}
        if bad_values:
            errors.append(f"unexpected pilot_or_confirmatory values: {bad_values}")

    # 7. depth/budget levels consistent across configurations
    if not confirmatory.empty:
        for mode, mode_df in confirmatory.groupby("analysis_mode"):
            per_config_depths = mode_df.groupby("configuration_id")["depth"].apply(lambda s: frozenset(s.unique()))
            if per_config_depths.nunique() > 1:
                errors.append(f"mode={mode}: depth levels differ across configurations: "
                               f"{per_config_depths.to_dict()}")
            per_config_budgets = mode_df.groupby("configuration_id")["budget"].apply(lambda s: frozenset(s.unique()))
            if per_config_budgets.nunique() > 1:
                errors.append(f"mode={mode}: budget levels differ across configurations: "
                               f"{per_config_budgets.to_dict()}")

    # 8. resource totals must not exceed the configured budget (finite-shot modes only)
    shot_modes = df[df["analysis_mode"].isin(["finite_shot_conditional", "finite_shot_end_to_end"])]
    if not shot_modes.empty:
        over = shot_modes[shot_modes["total_shots"] > shot_modes["budget"]]
        if not over.empty:
            errors.append(f"{len(over)} rows have total_shots exceeding the configured budget")

    # 9. exact gradients must agree across repeated rows for the same
    #    (mode-independent) matched cell -- i.e. across analysis_mode and replicate_id,
    #    exact_gradient for a given (configuration, depth, initialization, parameter) is a constant.
    key_cols_exact = ["configuration_id", "depth", "initialization_id", "parameter_id"]
    if all(c in df.columns for c in key_cols_exact):
        spread = df.groupby(key_cols_exact)["exact_gradient"].apply(lambda s: s.max() - s.min())
        bad_spread = spread[spread > 1e-6]
        if not bad_spread.empty:
            errors.append(f"{len(bad_spread)} matched cells have inconsistent exact_gradient values "
                           f"across repeated rows (should be identical)")

    return {
        "passed": len(errors) == 0,
        "errors": errors,
        "warnings": warnings,
        "n_rows": int(len(df)),
        "n_confirmatory_rows": int(len(confirmatory)),
    }
