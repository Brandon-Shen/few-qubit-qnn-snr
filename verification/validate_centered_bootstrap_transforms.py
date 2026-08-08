"""Validate transformed historical H1 and H2--H4 draws by explicit refit."""
from __future__ import annotations

import json
import sys
import warnings
from pathlib import Path

import numpy as np
import pandas as pd

from qnn_snr.stats.bootstrap import _relabel_outer_resample
from qnn_snr.stats.factor_coding import H1_CENTERED_FORMULA, H2_H4_CENTERED_FORMULA, add_centered_factors
from qnn_snr.stats.models import build_h1_dataset, build_h2h4_dataset, fit_mixed_model

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "verification"))
from h2h4_bootstrap_lowmem import _one_iteration_lowmem, _precompute_cell_index  # noqa: E402


def main() -> None:
    results = {"h1": [], "h2h4": []}
    exact = pd.read_parquet(ROOT / "results/production_confirmatory/raw/exact.parquet")
    archived_h1 = pd.read_parquet(ROOT / "verification/_bootstrap_checkpoints/h1_boot.parquet").set_index("iteration")
    for iteration in range(10):
        rng = np.random.default_rng((55001, iteration))
        sample = _relabel_outer_resample(exact, rng)
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            fit = fit_mixed_model(H1_CENTERED_FORMULA, add_centered_factors(build_h1_dataset(sample)), "a")
        expected = archived_h1.loc[iteration, "E:L"] + 0.5 * archived_h1.loc[iteration, "E:L:R"]
        difference = float(fit.params["E_c:L_c"] - expected)
        if not np.isclose(difference, 0.0, atol=1e-8, rtol=1e-7):
            raise AssertionError(f"H1 iteration {iteration} mismatch {difference}")
        results["h1"].append({"seed": 55001, "iteration": iteration, "difference": difference})

    raw = pd.read_parquet(ROOT / "results/production_confirmatory/raw/finite_shot_end_to_end.parquet")
    pre = _precompute_cell_index(raw)
    del raw
    archived_h2 = pd.read_parquet(
        ROOT / "results/production_corrected_end_to_end/bootstrap_end_to_end_h2_h4_iterations.parquet"
    )
    archived_h2 = archived_h2[archived_h2._stream == "regression_a"].set_index("iteration")
    for iteration in range(3):
        rng = np.random.default_rng((266001, iteration))
        pw = _one_iteration_lowmem(pre, rng, pointwise_bootstrap_iterations=50)
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            fit = fit_mixed_model(H2_H4_CENTERED_FORMULA, add_centered_factors(build_h2h4_dataset(pw)), "y")
        old = archived_h2.loc[iteration]
        expected = {
            "E_c:L_c": old["E:L"] + 0.5 * old["E:L:R"],
            "E_c:R_c": old["E:R"] + 0.5 * old["E:L:R"],
            "L_c:R_c:depth_z": old["L:R:depth_z"],
        }
        differences = {name: float(fit.params[name] - value) for name, value in expected.items()}
        if any(not np.isclose(value, 0.0, atol=1e-8, rtol=1e-7) for value in differences.values()):
            raise AssertionError(f"H2-H4 iteration {iteration} mismatch {differences}")
        results["h2h4"].append({"seed": 266001, "iteration": iteration, "differences": differences})
    results["status"] = "passed"
    results["tolerances"] = {"atol": 1e-8, "rtol": 1e-7}
    (ROOT / "results/primary_corrected/effect_coded/bootstrap_transform_validation.json").write_text(
        json.dumps(results, indent=2) + "\n", encoding="utf-8"
    )


if __name__ == "__main__":
    main()
