"""Read-only audit tests for the frozen centered-H3 package."""
from pathlib import Path
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "results/h3_centered_robustness"


def test_h3_simple_contrast_identities_and_average():
    d = pd.read_csv(OUT / "simple_and_sensitivity_contrasts.csv").set_index("contrast")
    l0 = d.loc["full_end_to_end_L0", "estimate"]
    l1 = d.loc["full_end_to_end_L1", "estimate"]
    avg = d.loc["full_end_to_end_L_average", "estimate"]
    assert np.isclose((l0 + l1) / 2, avg, atol=1e-12)
    assert np.isclose(avg, -0.011615106336627561, atol=1e-12)


def test_h3_bootstrap_transformation_draw_by_draw():
    source = pd.read_parquet(ROOT / "results/production_corrected_end_to_end/bootstrap_end_to_end_h2_h4_iterations.parquet")
    frozen = pd.read_parquet(OUT / "bootstrap_draws.parquet")
    merged = frozen.merge(source, left_on=["stream", "iteration", "seed"],
                          right_on=["_stream", "iteration", "_seed"], validate="one_to_one")
    assert len(merged) == 443
    assert np.allclose(merged.ER_L0, merged["E:R"])
    assert np.allclose(merged.ER_L1, merged["E:R"] + merged["E:L:R"])
    assert np.allclose(merged.ER_L_average, merged["E:R"] + .5 * merged["E:L:R"])


def test_h3_active_depth_and_mode_separation():
    d = pd.read_csv(OUT / "simple_and_sensitivity_contrasts.csv").set_index("contrast")
    assert d.loc["active_Dge3_L_average", "estimate"] < 0
    assert d.loc["conditional_mode_L_average", "estimate"] > 0
    assert d.loc["full_end_to_end_L_average", "estimate"] < 0


def test_h3_depths_and_loo_complete():
    depth = pd.read_csv(OUT / "depth_contrasts.csv")
    loo = pd.read_csv(OUT / "leave_one_initialization_out.csv")
    assert depth.depth.tolist() == [1, 2, 3, 4, 6]
    assert len(loo) == 50 and (loo.status == "completed").all()
    assert (loo.ER_average < 0).all()
