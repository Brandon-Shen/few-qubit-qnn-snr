from pathlib import Path

import qnn_snr
from qnn_snr.config import load_config
from qnn_snr.pilot import select_initialization_count, select_replicate_count
from qnn_snr.replicate import generate_exact_rows, generate_shot_rows
from qnn_snr.schema import rows_to_dataframe
from qnn_snr.stats.models import fit_h2h4_model
from qnn_snr.stats.pointwise import pointwise_statistics

CONFIG_DIR = Path(qnn_snr.__file__).resolve().parent.parent / "configs"


def test_select_replicate_count_smoke():
    cfg = load_config(CONFIG_DIR / "smoke.yaml")
    cfg.pilot.replicate_count.start_R = 5
    cfg.pilot.replicate_count.increment = 5
    cfg.pilot.replicate_count.max_R = 10
    cfg.pilot.replicate_count.abs_halfwidth_tolerance = 10.0  # loose, just exercise the loop
    cfg.pilot.replicate_count.representative_cells = [{"configuration_id": 1, "depth": 1, "budget": 64}]
    out = select_replicate_count(cfg)
    assert out["selected_R_overall"] in (5, 10)
    assert len(out["per_cell"]) == 1
    assert out["per_cell"][0]["history"][0]["R"] == 5


def test_select_initialization_count_smoke():
    cfg = load_config(CONFIG_DIR / "smoke.yaml")
    shot_df = rows_to_dataframe(generate_shot_rows(cfg, "finite_shot_end_to_end"))
    pw = pointwise_statistics(shot_df, bootstrap_iterations=20)
    h2h4 = fit_h2h4_model(pw)

    cfg.pilot.initialization_count.start_n = 5
    cfg.pilot.initialization_count.increment = 5
    cfg.pilot.initialization_count.max_n = 10
    out = select_initialization_count(cfg, None, h2h4)
    assert len(out["candidates"]) >= 1
    assert "p90_halfwidth" in out["candidates"][0]
