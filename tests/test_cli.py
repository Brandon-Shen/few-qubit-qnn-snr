import argparse
from pathlib import Path

import yaml

import qnn_snr
from qnn_snr import cli

CONFIG_DIR = Path(qnn_snr.__file__).resolve().parent.parent / "configs"


def _write_tmp_smoke_config(tmp_path: Path) -> Path:
    with open(CONFIG_DIR / "smoke.yaml") as fh:
        raw = yaml.safe_load(fh)
    raw["output"] = {"results_dir": str(tmp_path / "results")}
    out_path = tmp_path / "smoke.yaml"
    with open(out_path, "w") as fh:
        yaml.safe_dump(raw, fh)
    return out_path


def test_run_all_produces_every_required_output_file(tmp_path):
    config_path = _write_tmp_smoke_config(tmp_path)
    args = argparse.Namespace(config=str(config_path), overwrite=False, iterations=6,
                               pointwise_bootstrap_iterations=10)
    cli.cmd_run_all(args)

    results_dir = tmp_path / "results"
    required = [
        "data_validation_report.json", "run_manifest.json", "pointwise_gradient_statistics.parquet",
        "exact_model_coefficients.csv", "snr_model_coefficients.csv", "confirmatory_hypotheses.csv",
        "holm_adjustment.csv", "bootstrap_coefficients.parquet", "bootstrap_diagnostics.json",
        "configuration_summaries.csv", "interaction_indices.csv", "resource_accounting.csv",
        "exploratory_results.csv", "assumptions_snapshot.md", "statistical_methods.md",
        "results_summary.md",
    ]
    for name in required:
        assert (results_dir / name).exists(), name
    figures = list((results_dir / "figures").glob("*.png"))
    assert len(figures) == 12

    import pandas as pd
    confirmatory = pd.read_csv(results_dir / "confirmatory_hypotheses.csv")
    assert list(confirmatory["hypothesis"]) == ["H1", "H2", "H3", "H4"]


def test_generate_exact_resume_skips_existing(tmp_path, capsys):
    config_path = _write_tmp_smoke_config(tmp_path)
    args = argparse.Namespace(config=str(config_path), overwrite=False)
    cli.cmd_generate_exact(args)
    capsys.readouterr()
    cli.cmd_generate_exact(args)  # second call should skip, not regenerate
    out = capsys.readouterr().out
    assert "already exists" in out


def test_validate_command_exits_nonzero_on_failure(tmp_path):
    import pytest

    config_path = _write_tmp_smoke_config(tmp_path)
    args = argparse.Namespace(config=str(config_path), overwrite=False)
    cli.cmd_generate_exact(args)

    # corrupt the raw data on disk to force a validation failure
    import pandas as pd
    raw_path = tmp_path / "results" / "raw" / "exact.parquet"
    df = pd.read_parquet(raw_path)
    df = df[df["configuration_id"] != 8]
    df.to_parquet(raw_path, index=False)

    validate_args = argparse.Namespace(config=str(config_path))
    with pytest.raises(SystemExit) as exc_info:
        cli.cmd_validate(validate_args)
    assert exc_info.value.code != 0
