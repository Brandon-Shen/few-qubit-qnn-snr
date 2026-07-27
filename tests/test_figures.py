from pathlib import Path

import pandas as pd
import pytest

import qnn_snr
from qnn_snr.config import load_config
from qnn_snr.figures import generate_all_figures
from qnn_snr.replicate import generate_exact_rows, generate_shot_rows
from qnn_snr.schema import rows_to_dataframe
from qnn_snr.stats.descriptive import configuration_summaries, physics_summary_rows, resource_accounting_table
from qnn_snr.stats.holm import build_confirmatory_table
from qnn_snr.stats.models import fit_h1_model, fit_h2h4_model
from qnn_snr.stats.pointwise import pointwise_statistics

CONFIG_DIR = Path(qnn_snr.__file__).resolve().parent.parent / "configs"


def test_generate_all_figures_smoke(tmp_path):
    cfg = load_config(CONFIG_DIR / "smoke.yaml")
    exact_df = rows_to_dataframe(generate_exact_rows(cfg))
    shot_df = rows_to_dataframe(generate_shot_rows(cfg, "finite_shot_end_to_end"))
    pw = pointwise_statistics(shot_df, bootstrap_iterations=20)
    physics_df = pd.DataFrame(physics_summary_rows(cfg))
    summaries = configuration_summaries(pw, exact_df, physics_df)
    resource_table = resource_accounting_table(shot_df)

    h1 = fit_h1_model(exact_df)
    h2h4 = fit_h2h4_model(pw)
    confirmatory = build_confirmatory_table(h1, h2h4)

    out_dir = tmp_path / "figures"
    generate_all_figures(
        out_dir, confirmatory_table=confirmatory, pointwise_df=pw, exact_df=exact_df,
        configuration_summaries=summaries, resource_table=resource_table,
        bootstrap_coef_df=pd.DataFrame({"E:L": [0.1, 0.2, -0.1]}), physics_df=physics_df,
    )
    pngs = list(out_dir.glob("*.png"))
    assert len(pngs) == 12
