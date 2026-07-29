"""Validate h2h4_bootstrap_lowmem against the original pipeline at dev.yaml
scale (12 inits, 5 depths, 4 budgets, 8 configs, 30 replicates -- much closer
to production's key-structure complexity than the smoke config, while still
being cheap enough to run twice (once per implementation) for comparison)."""
import time
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
cfg = load_config(CONFIG_DIR / "dev.yaml")
t0 = time.time()
parts = [rows_to_dataframe(generate_shot_rows(cfg, m)) for m in ("finite_shot_conditional", "finite_shot_end_to_end")]
raw = pd.concat(parts, ignore_index=True)
print(f"dev combined shot df: {len(raw)} rows, {raw['initialization_id'].nunique()} inits, generated in {time.time()-t0:.1f}s")

t0 = time.time()
pre = _precompute_cell_index(raw)
print(f"precomputed: {len(pre.sorted_full_keys)} cells in {time.time()-t0:.1f}s")

failures = 0
for seed in (66001, 55001):
    for it in range(2):
        t0 = time.time()
        rng_orig = np.random.default_rng((seed, it))
        outer = _relabel_outer_resample(raw, rng_orig)
        inner = _inner_resample_replicates(outer, rng_orig)
        bootstrap_seed = int(rng_orig.integers(0, 2 ** 31 - 1))
        pw_orig = pointwise_statistics(inner, bootstrap_iterations=50, bootstrap_seed=bootstrap_seed)
        t_orig = time.time() - t0

        t0 = time.time()
        rng_new = np.random.default_rng((seed, it))
        pw_new = _one_iteration_lowmem(pre, rng_new, pointwise_bootstrap_iterations=50)
        t_new = time.time() - t0

        same_order = pw_orig.reset_index(drop=True).equals(pw_new.reset_index(drop=True))
        if pw_orig.shape != pw_new.shape:
            print(f"seed={seed} it={it}: SHAPE MISMATCH {pw_orig.shape} vs {pw_new.shape}")
            failures += 1
            continue

        numeric_cols = [c for c in pw_orig.columns if pd.api.types.is_numeric_dtype(pw_orig[c])]
        ok = True
        max_diffs = {}
        for c in numeric_cols:
            a = pw_orig[c].to_numpy(dtype=float)
            b = pw_new[c].to_numpy(dtype=float)
            d = np.nanmax(np.abs(a - b)) if len(a) else 0.0
            max_diffs[c] = d
            if not np.allclose(a, b, atol=1e-12, rtol=1e-10, equal_nan=True):
                ok = False
        worst = max(max_diffs.values()) if max_diffs else 0.0

        ds_orig = build_h2h4_dataset(pw_orig)
        ds_new = build_h2h4_dataset(pw_new)
        r_orig = fit_mixed_model(H2_H4_FORMULA, ds_orig, "y")
        r_new = fit_mixed_model(H2_H4_FORMULA, ds_new, "y")
        coef_ok = True
        coef_diffs = {}
        if r_orig.converged and r_new.converged:
            for k in r_orig.params:
                dd = abs(r_orig.params[k] - r_new.params.get(k, np.nan))
                coef_diffs[k] = dd
                if dd > 1e-8:
                    coef_ok = False
        print(f"seed={seed} it={it}: rows same_order={same_order} shape_ok pointwise_max_diff={worst:.3e} "
              f"model_converged(orig={r_orig.converged},new={r_new.converged}) coef_max_diff={max(coef_diffs.values()) if coef_diffs else float('nan'):.3e} "
              f"t_orig={t_orig:.1f}s t_new={t_new:.1f}s")
        if not (ok and coef_ok):
            failures += 1
            print(f"  FAILURE DETAILS: pointwise_ok={ok} coef_ok={coef_ok}")
            print(f"  max diffs by col: { {k:v for k,v in max_diffs.items() if v>1e-12} }")

print(f"\nTOTAL FAILURES: {failures}")
