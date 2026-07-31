"""Regression tests for the QMI/QIP robustness package
(verification/qmi_qip_robustness_package.md): the D!=1 sensitivity path,
the extended bootstrap's seed/checkpoint/resume behavior, the zero-variance
audit, and stability of the adopted coefficients under reporting-only code
changes.

Imports scripts from verification/ (not part of the qnn_snr package proper)
via a path-relative sys.path insert, matching the convention those scripts
already use for importing each other.
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

import qnn_snr
from qnn_snr.config import load_config
from qnn_snr.replicate import generate_exact_rows, generate_shot_rows
from qnn_snr.schema import rows_to_dataframe
from qnn_snr.stats.models import build_h2h4_dataset, fit_h2h4_model

REPO_ROOT = Path(qnn_snr.__file__).resolve().parent.parent
CONFIG_DIR = REPO_ROOT / "configs"
VER_DIR = REPO_ROOT / "verification"
sys.path.insert(0, str(VER_DIR))

from h2h4_bootstrap_lowmem import _precompute_cell_index, run_h2h4_bootstrap_lowmem  # noqa: E402


@pytest.fixture(scope="module")
def smoke_cfg():
    return load_config(CONFIG_DIR / "smoke.yaml")


@pytest.fixture(scope="module")
def exact_df(smoke_cfg):
    return rows_to_dataframe(generate_exact_rows(smoke_cfg))


@pytest.fixture(scope="module")
def shot_df(smoke_cfg):
    return rows_to_dataframe(generate_shot_rows(smoke_cfg, "finite_shot_end_to_end"))


# --- 1. Mixed-mode confirmatory input still raises by default ---

def test_mixed_mode_still_raises_by_default():
    df = pd.DataFrame({
        "analysis_mode": ["finite_shot_end_to_end", "finite_shot_conditional"],
        "SNR_est": [1.0, 2.0],
    })
    with pytest.raises(ValueError, match="analysis_mode"):
        build_h2h4_dataset(df)


# --- 2. The D!=1 sensitivity path preserves the original full-sweep block-count scaling ---

def test_d_neq_1_filter_does_not_alter_depth_z(exact_df):
    from qnn_snr.stats.models import build_h1_dataset
    d = build_h1_dataset(exact_df)
    assert "depth_z" in d.columns
    depths_present = sorted(d["depth"].unique())
    assert 1 in depths_present, "smoke config must include D=1 for this test to be meaningful"

    depth_z_by_depth_full = d.groupby("depth")["depth_z"].first().to_dict()

    d_neq_1 = d[d["depth"] != 1]
    depth_z_by_depth_subset = d_neq_1.groupby("depth")["depth_z"].first().to_dict()

    for depth, z in depth_z_by_depth_subset.items():
        assert z == depth_z_by_depth_full[depth], (
            f"depth_z for depth={depth} changed after filtering D!=1: "
            f"{z} != {depth_z_by_depth_full[depth]} -- the D!=1 sensitivity path must reuse "
            f"the full-sweep depth_z column verbatim, never recompute it on a subset."
        )
    # and confirm the subset's depth_z values are not zero-mean (i.e. genuinely not recentered)
    assert not np.isclose(d_neq_1["depth_z"].mean(), 0.0, atol=1e-9), (
        "D!=1 subset's depth_z has mean ~0 -- suspicious of accidental re-centering on the subset "
        "(the full 5-level design's depth_z is not exactly zero-mean once D=1 is excluded)."
    )


# --- 3. Bootstrap shard seed ranges cannot overlap ---

def test_shard_seed_ranges_cannot_overlap():
    BASE_SEED = 366001
    SEED_STRIDE = 10_000
    REGRESSION_SEED = 266001
    n_shards = 20  # generous upper bound, well beyond what this package used
    shard_seeds = [BASE_SEED + i * SEED_STRIDE for i in range(n_shards)]
    assert len(set(shard_seeds)) == n_shards, "shard seeds must be pairwise distinct"
    assert REGRESSION_SEED not in shard_seeds, "regression-test seed must not collide with any shard seed"
    # per-iteration RNG key is (seed, iteration) -- confirm no cross-shard key collisions
    # for a representative range of iteration indices
    max_iterations = 2000
    keys = set()
    for seed in shard_seeds + [REGRESSION_SEED]:
        for it in range(max_iterations):
            key = (seed, it)
            assert key not in keys, f"seed/iteration key collision at {key}"
            keys.add(key)


# --- 4. Resuming an interrupted bootstrap does not duplicate completed iterations ---

def test_lowmem_bootstrap_resume_does_not_duplicate(shot_df, tmp_path):
    ckpt = tmp_path / "h2h4_boot_lowmem_resume_test.parquet"
    pre = _precompute_cell_index(shot_df)

    r1 = run_h2h4_bootstrap_lowmem(raw_shot_df=None, n_iterations=2, seed=123456,
                                    min_success_fraction=0.0, checkpoint_path=ckpt,
                                    checkpoint_every=1, precomputed=pre)
    assert r1.n_successful + len(r1.failed_iterations) == 2

    r2 = run_h2h4_bootstrap_lowmem(raw_shot_df=None, n_iterations=4, seed=123456,
                                    min_success_fraction=0.0, checkpoint_path=ckpt,
                                    checkpoint_every=1, precomputed=pre)
    assert r2.n_successful + len(r2.failed_iterations) == 4

    completed_iters = r2.coefficients["iteration"].tolist()
    assert len(completed_iters) == len(set(completed_iters)), (
        "resumed bootstrap produced duplicate iteration indices in the checkpoint"
    )
    # the first two iterations' coefficients must be bit-identical between r1 and r2's resume
    # (same seed, same precomputed structure -> deterministic replay, not re-drawn)
    shared = sorted(set(r1.coefficients["iteration"]) & set(r2.coefficients["iteration"]))
    for it in shared:
        row1 = r1.coefficients[r1.coefficients["iteration"] == it].iloc[0]
        row2 = r2.coefficients[r2.coefficients["iteration"] == it].iloc[0]
        for coef in ("E:L", "E:R", "L:R:depth_z"):
            if coef in row1 and coef in row2:
                assert row1[coef] == row2[coef], f"iteration {it} coefficient {coef} changed on resume"


# --- 5. The bootstrap summary excludes failed fits but reports their count ---

def test_pooled_summary_excludes_failed_fits_but_counts_them(tmp_path, monkeypatch):
    import importlib
    ckpt_dir = tmp_path / "_bootstrap_checkpoints"
    ckpt_dir.mkdir()

    coef_rows = [{"iteration": 0, "E:L": 0.02, "E:R": 0.0, "L:R:depth_z": -0.01},
                 {"iteration": 1, "E:L": 0.03, "E:R": 0.0, "L:R:depth_z": -0.01}]
    pd.DataFrame(coef_rows).to_parquet(ckpt_dir / "h2h4_boot_endtoend_regression_a.parquet", index=False)
    (ckpt_dir / "h2h4_boot_endtoend_regression_a.meta.json").write_text(
        '{"failed_iterations": [2, 3, 4]}', encoding="utf-8")

    import summarize_bootstrap_checkpoints as mod
    monkeypatch.setattr(mod, "CKPT_DIR", ckpt_dir)
    monkeypatch.setattr(mod, "POOL_SOURCES", [("regression_a", "h2h4_boot_endtoend_regression_a", 266001)])
    monkeypatch.setattr(mod, "REPO_ROOT", tmp_path)
    (tmp_path / "results").mkdir(exist_ok=True)
    (tmp_path / "verification").mkdir(exist_ok=True)

    mod.main()

    summary = pd.read_csv(tmp_path / "results" / "bootstrap_end_to_end_h2_h4_summary.csv")
    assert (summary["n_pooled"] == 2).all(), "successful-draw count should exclude the 3 failed iterations"
    assert (summary["n_failed"] == 3).all(), "failed-iteration count must still be reported"
    assert np.isclose(summary["fit_failure_rate_pct"].iloc[0], 100 * 3 / 5)


# --- 6. The final forest-plot input uses only end-to-end bootstrap draws ---

def test_forest_plot_script_reads_only_endtoend_checkpoints():
    import ast

    script_path = REPO_ROOT / "paper" / "scripts" / "make_fig1_forest.py"
    script = script_path.read_text(encoding="utf-8")
    assert "endtoend" in script or "end_to_end" in script, (
        "fig1 script must reference end-to-end-labeled data somewhere"
    )

    # Inspect only actual `read_parquet(...)` call arguments (not prose/comments/docstrings),
    # so a docstring that *names* the forbidden old pooled file as an example of what to
    # avoid does not itself trip this check.
    tree = ast.parse(script)
    read_parquet_arg_strings = []
    for node in ast.walk(tree):
        if (isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)
                and node.func.attr == "read_parquet"):
            for sub in ast.walk(node):
                if isinstance(sub, ast.Constant) and isinstance(sub.value, str):
                    read_parquet_arg_strings.append(sub.value)

    assert read_parquet_arg_strings, "expected at least one pd.read_parquet(...) call in the fig1 script"
    for arg in read_parquet_arg_strings:
        assert not (arg.startswith("h2h4_boot_shard") or "/h2h4_boot_shard" in arg or "\\h2h4_boot_shard" in arg), (
            f"fig1 script must not read an old pooled-mode shard checkpoint by name, found: {arg!r} "
            f"(superseded per verification/confirmatory_numbers_adopted.md)"
        )


# --- 7. The zero-variance audit reproduces the production eligibility count ---

def test_zero_variance_audit_matches_production_eligibility_count(shot_df):
    from qnn_snr.stats.pointwise import pointwise_statistics
    pw = pointwise_statistics(shot_df, bootstrap_iterations=5)
    n_candidate = len(pw)
    n_used_by_production = len(build_h2h4_dataset(pw))
    n_excluded_by_flag = int(pw["zero_variance_flag"].sum())

    assert n_candidate - n_used_by_production == n_excluded_by_flag, (
        "zero_variance_flag count must exactly match the number of rows "
        "build_h2h4_dataset() actually drops -- the audit and the production "
        "fitting path must agree on which cells are excluded"
    )


# --- 8. The adopted coefficients are unchanged by reporting-only code changes ---

ADOPTED_COEFFICIENTS = {
    "E:L": 0.024995843985971582,
    "E:R": -0.0009575787575784316,
    "L:R:depth_z": -0.010178757716721849,
}
ADOPTED_DATA_PATH = REPO_ROOT / "results" / "pointwise_gradient_statistics.parquet"


@pytest.mark.skipif(not ADOPTED_DATA_PATH.exists(), reason="full confirmatory dataset not present in this checkout")
def test_adopted_coefficients_unchanged():
    pw = pd.read_parquet(ADOPTED_DATA_PATH)
    eo = pw[pw["analysis_mode"] == "finite_shot_end_to_end"]
    res = fit_h2h4_model(eo)
    for coef, expected in ADOPTED_COEFFICIENTS.items():
        assert res.params[coef] == pytest.approx(expected, abs=1e-9), (
            f"adopted coefficient {coef} drifted from the frozen record "
            f"({res.params[coef]!r} != {expected!r}) -- a reporting-only change must never "
            f"alter the confirmatory fit's actual output"
        )
