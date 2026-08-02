"""Factor-coding correction utilities for the H1--H4 mixed models."""
from __future__ import annotations

import numpy as np
import pandas as pd

H1_CENTERED_FORMULA = (
    "a ~ E_c*L_c*R_c + depth_z + E_c:depth_z + L_c:depth_z + R_c:depth_z"
)
H2_H4_CENTERED_FORMULA = (
    "y ~ E_c*L_c*R_c + depth_z + log2_budget + E_c:depth_z + "
    "L_c:depth_z + R_c:depth_z + L_c:R_c:depth_z"
)


def add_centered_factors(df: pd.DataFrame) -> pd.DataFrame:
    """Return a copy with explicit {-1/2,+1/2} factor columns."""
    out = df.copy()
    for source, target in (("E", "E_c"), ("L", "L_c"), ("R", "R_c")):
        values = set(out[source].dropna().unique())
        if not values.issubset({0, 1, 0.0, 1.0}):
            raise ValueError(f"{source} is not binary 0/1: {sorted(values)}")
        out[target] = out[source].astype(float) - 0.5
    return out


def design_coefficient_map(direct_result, centered_result) -> tuple[pd.DataFrame, dict]:
    """Map direct fixed coefficients to centered coefficients from fitted designs.

    If X_direct b_direct == X_centered b_centered and X_direct = X_centered A,
    then b_centered = A b_direct and V_centered = A V_direct A'.
    """
    xd = np.asarray(direct_result.model.exog, dtype=float)
    xc = np.asarray(centered_result.model.exog, dtype=float)
    if xd.shape[0] != xc.shape[0]:
        raise ValueError("Direct and centered fits used different row counts")
    mapping, _, rank, _ = np.linalg.lstsq(xc, xd, rcond=None)
    reconstructed = xc @ mapping
    projection_error = float(np.max(np.abs(xd - reconstructed)))
    direct_names = list(direct_result.model.exog_names)
    centered_names = list(centered_result.model.exog_names)
    table = pd.DataFrame(mapping, index=centered_names, columns=direct_names)
    diagnostics = {
        "n_rows": int(xd.shape[0]),
        "direct_columns": int(xd.shape[1]),
        "centered_columns": int(xc.shape[1]),
        "direct_rank": int(np.linalg.matrix_rank(xd)),
        "centered_rank": int(np.linalg.matrix_rank(xc)),
        "mapping_rank": int(rank),
        "max_column_space_projection_error": projection_error,
    }
    return table, diagnostics


def transform_fixed_effects(direct_result, mapping: pd.DataFrame) -> tuple[pd.Series, pd.DataFrame]:
    direct_names = list(mapping.columns)
    b = direct_result.fe_params.loc[direct_names].to_numpy(dtype=float)
    cov_all = direct_result.cov_params()
    v = cov_all.loc[direct_names, direct_names].to_numpy(dtype=float)
    a = mapping.to_numpy(dtype=float)
    transformed = pd.Series(a @ b, index=mapping.index, name="estimate")
    transformed_cov = pd.DataFrame(a @ v @ a.T, index=mapping.index, columns=mapping.index)
    return transformed, transformed_cov


def transform_bootstrap_draws(draws: pd.DataFrame, family: str) -> pd.DataFrame:
    """Transform historical direct-coding draws to centered target draws."""
    required = {"E:L", "E:R", "E:L:R"}
    missing = required - set(draws.columns)
    if missing:
        raise ValueError(f"Bootstrap draws lack required coefficients: {sorted(missing)}")
    out = draws.copy()
    out["E_c:L_c"] = out["E:L"] + 0.5 * out["E:L:R"]
    out["E_c:R_c"] = out["E:R"] + 0.5 * out["E:L:R"]
    if "L:R" in out:
        out["L_c:R_c"] = out["L:R"] + 0.5 * out["E:L:R"]
    if family == "h2h4":
        if "L:R:depth_z" not in out:
            raise ValueError("H2-H4 draws lack L:R:depth_z")
        out["L_c:R_c:depth_z"] = out["L:R:depth_z"]
    return out
