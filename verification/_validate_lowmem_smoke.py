"""Validate h2h4_bootstrap_lowmem reproduces the original pipeline bit-for-bit
on cheap smoke-scale data before trusting it on the full 6.14M-row dataset."""
import numpy as np
import pandas as pd

import qnn_snr
from pathlib import Path

from qnn_snr.config import load_config
from qnn_snr.replicate import generate_shot_rows
from qnn_snr.schema import rows_to_dataframe
from qnn_snr.stats.bootstrap import _inner_resample_replicates, _relabel_outer_resample
from qnn_snr.stats.pointwise import pointwise_statistics
from qnn_snr.stats.models import build_h2h4_dataset, fit_mixed_model, H2_H4_FORMULA

import sys
sys.path.insert(0, str(Path(__file__).parent))
from h2h4_bootstrap_lowmem import _precompute_cell_index, _one_iteration_lowmem

CONFIG_DIR = Path(qnn_snr.__file__).resolve().parent.parent / "configs"
cfg = load_config(CONFIG_DIR / "smoke.yaml")
parts = [rows_to_dataframe(generate_shot_rows(cfg, m)) for m in ("finite_shot_conditional", "finite_shot_end_to_end")]
raw = pd.concat(parts, ignore_index=True)
print(f"smoke combined shot df: {len(raw)} rows, {raw['initialization_id'].nunique()} inits")

pre = _precompute_cell_index(raw)
print(f"precomputed: {len(pre.sorted_full_keys)} cells")

failures = 0
for seed in (66001, 7, 42, 12346):
    for it in range(3):
        rng_orig = np.random.default_rng((seed, it))
        outer = _relabel_outer_resample(raw, rng_orig)
        inner = _inner_resample_replicates(outer, rng_orig)
        bootstrap_seed = int(rng_orig.integers(0, 2 ** 31 - 1))
        pw_orig = pointwise_statistics(inner, bootstrap_iterations=50, bootstrap_seed=bootstrap_seed)

        rng_new = np.random.default_rng((seed, it))
        pw_new = _one_iteration_lowmem(pre, rng_new, pointwise_bootstrap_iterations=50)

        # align row order (both should already be in the same canonical sorted order,
        # but sort explicitly by CELL_KEY_COLS-derived key to be safe before comparing)
        key_cols = ["analysis_mode", "configuration_id", "depth", "budget", "initialization_id", "parameter_id"]
        pw_orig_s = pw_orig.sort_values(key_cols).reset_index(drop=True)
        pw_new_s = pw_new.sort_values(key_cols).reset_index(drop=True)

        if pw_orig_s.shape != pw_new_s.shape:
            print(f"seed={seed} it={it}: SHAPE MISMATCH {pw_orig_s.shape} vs {pw_new_s.shape}")
            failures += 1
            continue

        # row order should already match without needing the sort (checks our precomputed
        # sorted-key order assumption); check that first, then check values regardless.
        same_order = pw_orig.reset_index(drop=True).equals(pw_new.reset_index(drop=True))
        print(f"seed={seed} it={it}: raw row order match (no re-sort) = {same_order}")

        numeric_cols = [c for c in pw_orig_s.columns if pd.api.types.is_numeric_dtype(pw_orig_s[c])]
        ok = True
        for c in numeric_cols:
            a = pw_orig_s[c].to_numpy(dtype=float)
            b = pw_new_s[c].to_numpy(dtype=float)
            if not np.allclose(a, b, atol=1e-12, rtol=1e-10, equal_nan=True):
                print(f"  MISMATCH in column {c}: max abs diff = {np.nanmax(np.abs(a-b))}")
                ok = False
        non_numeric = [c for c in pw_orig_s.columns if c not in numeric_cols]
        for c in non_numeric:
            if not (pw_orig_s[c].astype(str).to_numpy() == pw_new_s[c].astype(str).to_numpy()).all():
                print(f"  MISMATCH in non-numeric column {c}")
                ok = False
        if not ok:
            failures += 1
            continue

        # also check the downstream model fit matches
        ds_orig = build_h2h4_dataset(pw_orig)
        ds_new = build_h2h4_dataset(pw_new)
        r_orig = fit_mixed_model(H2_H4_FORMULA, ds_orig, "y")
        r_new = fit_mixed_model(H2_H4_FORMULA, ds_new, "y")
        if r_orig.converged and r_new.converged:
            for k in r_orig.params:
                if abs(r_orig.params[k] - r_new.params.get(k, np.nan)) > 1e-8:
                    print(f"  MODEL COEF MISMATCH {k}: {r_orig.params[k]} vs {r_new.params.get(k)}")
                    failures += 1
        print(f"seed={seed} it={it}: pointwise stats OK, model converged orig={r_orig.converged} new={r_new.converged}")

print(f"\nTOTAL FAILURES: {failures}")
