"""Mixed-effects models for H1 (exact-signal) and H2-H4 (estimator-SNR)
(Sections 10-12).

ASSUMPTION A20: the nested random-effect unit "matched parameter within
initialization" is `(initialization_id, depth, parameter_id)`, i.e. it
includes depth, not just `(initialization_id, parameter_id)`. Reason: under
ASSUMPTION A17, each depth level draws an *independent* theta value, so
"theta_ell1_q0" at depth=2 and depth=4 are different underlying numbers with
only a shared label -- what is genuinely matched (identical value) across
rows is a parameter *within one initialization and one depth*, shared only
across the 8 E/L/R configurations. Implemented via a combined nested-id
column so statsmodels' `vc_formula` variance-component machinery treats it
as nested within the outer `initialization_id` grouping factor.

Uses `E*L*R` in the patsy formula, which expands to the exact fixed-effect
set required by Sections 10/11 (`E+L+R+E:L+E:R+L:R+E:L:R`) since E, L, R are
numeric (not categorical) 0/1 columns.
"""
from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np
import pandas as pd
import statsmodels.formula.api as smf

OPTIMIZER_FALLBACK_ORDER = ["lbfgs", "bfgs", "cg", "powell", "nm"]

H1_FORMULA = "a ~ E*L*R + depth_z + E:depth_z + L:depth_z + R:depth_z"
H2_H4_FORMULA = "y ~ E*L*R + depth_z + log2_budget + E:depth_z + L:depth_z + R:depth_z + L:R:depth_z"
SENSITIVITY_FORMULA = H2_H4_FORMULA + " + E:L:depth_z + E:R:depth_z"

# The paper's Methods designate finite_shot_end_to_end as the confirmatory
# estimator; finite_shot_conditional is a diagnostic only (see
# verification/conditional_vs_endtoend_comparison.md). Silently pooling both
# into one fit was a bug (verification/mode_pooling_guard.md), not a valid
# alternative design -- build_h2h4_dataset()/fit_h2h4_model() below refuse to
# fit mixed-mode data unless the caller explicitly opts in.
CONFIRMATORY_MODE = "finite_shot_end_to_end"


@dataclass
class MixedModelResult:
    formula: str
    converged: bool
    optimizer_used: str | None
    attempted_optimizers: list[str]
    params: dict
    bse: dict
    cov_params: pd.DataFrame | None
    random_effect_variances: dict
    n_obs: int
    n_groups: int
    n_vc_levels: int
    condition_number: float
    singular_fit: bool
    residual_diagnostics: dict
    raw_result: object = field(repr=False, default=None)
    error: str | None = None


def _add_nested_id(df: pd.DataFrame) -> pd.DataFrame:
    d = df.copy()
    d["nested_param_id"] = (
        d["initialization_id"].astype(str) + "__d" + d["depth"].astype(str) + "__" + d["parameter_id"].astype(str)
    )
    return d


def _fit_with_fallback(formula: str, data: pd.DataFrame, groups: pd.Series) -> tuple[object, str | None, list[str], str | None]:
    attempted = []
    for method in OPTIMIZER_FALLBACK_ORDER:
        attempted.append(method)
        try:
            model = smf.mixedlm(formula, data=data, groups=groups, re_formula="1",
                                 vc_formula={"param": "0 + C(nested_param_id)"})
            result = model.fit(method=method, reml=True)
            if result.converged:
                return result, method, attempted, None
        except Exception as exc:  # noqa: BLE001 -- genuinely need to try the next optimizer
            last_error = str(exc)
            continue
        last_error = "optimizer ran but did not report convergence"
    return None, None, attempted, last_error if attempted else "no optimizers attempted"


def _condition_number(exog: np.ndarray) -> float:
    if exog.size == 0:
        return float("nan")
    s = np.linalg.svd(exog, compute_uv=False)
    s = s[s > 1e-14]
    if len(s) == 0:
        return float("inf")
    return float(s.max() / s.min())


def fit_mixed_model(formula: str, df: pd.DataFrame, response_col: str) -> MixedModelResult:
    d = _add_nested_id(df)
    d = d.dropna(subset=[response_col])
    n_obs = len(d)
    n_groups = d["initialization_id"].nunique()
    n_vc_levels = d["nested_param_id"].nunique()

    result, method, attempted, error = _fit_with_fallback(formula, d, d["initialization_id"])

    if result is None:
        return MixedModelResult(
            formula=formula, converged=False, optimizer_used=None, attempted_optimizers=attempted,
            params={}, bse={}, cov_params=None, random_effect_variances={}, n_obs=n_obs,
            n_groups=n_groups, n_vc_levels=n_vc_levels, condition_number=float("nan"),
            singular_fit=True, residual_diagnostics={}, raw_result=None, error=error,
        )

    exog = result.model.exog
    cond = _condition_number(exog)
    group_var = float("nan")
    if hasattr(result, "cov_re") and result.cov_re is not None and result.cov_re.size > 0:
        group_var = float(result.cov_re.iloc[0, 0])
    vc_var = float(result.vcomp[0]) if hasattr(result, "vcomp") and len(result.vcomp) else float("nan")
    singular = bool(np.isclose(group_var, 0.0, atol=1e-8)) or bool(np.isclose(vc_var, 0.0, atol=1e-8))

    resid = np.asarray(result.resid)
    residual_diag = {
        "resid_mean": float(np.mean(resid)),
        "resid_sd": float(np.std(resid, ddof=1)) if len(resid) > 1 else float("nan"),
        "resid_min": float(np.min(resid)) if len(resid) else float("nan"),
        "resid_max": float(np.max(resid)) if len(resid) else float("nan"),
    }

    try:
        cov_params_df = result.cov_params()
    except Exception:
        cov_params_df = None

    return MixedModelResult(
        formula=formula,
        converged=bool(result.converged),
        optimizer_used=method,
        attempted_optimizers=attempted,
        params={k: float(v) for k, v in result.params.items()},
        bse={k: float(v) for k, v in result.bse.items()},
        cov_params=cov_params_df,
        random_effect_variances={"group_intercept_var": group_var, "nested_param_var": vc_var},
        n_obs=n_obs,
        n_groups=n_groups,
        n_vc_levels=n_vc_levels,
        condition_number=cond,
        singular_fit=singular,
        residual_diagnostics=residual_diag,
        raw_result=result,
        error=None,
    )


def build_h1_dataset(exact_df: pd.DataFrame) -> pd.DataFrame:
    d = exact_df.copy()
    d["a"] = np.arcsinh(np.abs(d["exact_gradient"]))
    return d


def build_h2h4_dataset(pointwise_df: pd.DataFrame, pool_modes: bool = False) -> pd.DataFrame:
    d = pointwise_df.copy()
    if "analysis_mode" in d.columns:
        modes = sorted(d["analysis_mode"].dropna().unique().tolist())
        if len(modes) > 1 and not pool_modes:
            raise ValueError(
                f"build_h2h4_dataset() received {len(modes)} distinct analysis_mode values "
                f"{modes}; the H2-H4 model must be fit on a single analysis_mode "
                f"('{CONFIRMATORY_MODE}' is confirmatory, 'finite_shot_conditional' is a "
                f"diagnostic only -- see verification/conditional_vs_endtoend_comparison.md and "
                f"verification/mode_pooling_guard.md). Filter the input to one mode before "
                f"calling, or pass pool_modes=True if pooling is genuinely intended for some "
                f"future exploratory purpose."
            )
    d = d[np.isfinite(d["SNR_est"])]  # excludes inf (zero-variance) and nan (undefined) cells from the model
    d["y"] = np.arcsinh(d["SNR_est"])
    return d


def fit_h1_model(exact_df: pd.DataFrame) -> MixedModelResult:
    return fit_mixed_model(H1_FORMULA, build_h1_dataset(exact_df), "a")


def fit_h2h4_model(pointwise_df: pd.DataFrame, pool_modes: bool = False) -> MixedModelResult:
    return fit_mixed_model(H2_H4_FORMULA, build_h2h4_dataset(pointwise_df, pool_modes=pool_modes), "y")


def fit_sensitivity_model(pointwise_df: pd.DataFrame, pool_modes: bool = False) -> MixedModelResult:
    """Preregistered sensitivity model adding E:L:depth_z and E:R:depth_z
    (Section 11) -- descriptive only, never part of the H1-H4 Holm family."""
    return fit_mixed_model(SENSITIVITY_FORMULA, build_h2h4_dataset(pointwise_df, pool_modes=pool_modes), "y")
