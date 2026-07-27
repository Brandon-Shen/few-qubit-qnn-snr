"""Run manifest (Section 22): every configuration value, package version,
backend, host info, seeds, source commit, model formulas, transform
definitions, bootstrap iteration count, failed-fit counts, and
pilot/confirmatory status needed to reproduce a run from a clean checkout."""
from __future__ import annotations

import datetime
import json
import platform
import subprocess
from pathlib import Path

from qnn_snr.config import ExperimentConfig, config_hash, config_to_dict
from qnn_snr.stats.models import H1_FORMULA, H2_H4_FORMULA, SENSITIVITY_FORMULA


def get_git_commit() -> str:
    try:
        out = subprocess.run(["git", "rev-parse", "HEAD"], capture_output=True, text=True, timeout=10)
        if out.returncode == 0:
            return out.stdout.strip()
    except Exception:
        pass
    return "unknown"


def package_versions() -> dict:
    versions = {}
    for pkg in ("pennylane", "numpy", "pandas", "scipy", "statsmodels", "pyarrow", "matplotlib", "yaml"):
        try:
            mod = __import__(pkg)
            versions[pkg] = getattr(mod, "__version__", "unknown")
        except Exception:
            versions[pkg] = "not installed"
    return versions


def host_info() -> dict:
    return {
        "platform": platform.platform(),
        "python_version": platform.python_version(),
        "processor": platform.processor(),
    }


def build_manifest(cfg: ExperimentConfig, *, start_time: str, end_time: str | None = None,
                    steps_run: list[str] | None = None, bootstrap_iterations: dict | None = None,
                    failed_fit_counts: dict | None = None, pilot_status: dict | None = None) -> dict:
    return {
        "experiment_name": cfg.name,
        "config": config_to_dict(cfg),
        "config_hash": config_hash(cfg),
        "git_commit": get_git_commit(),
        "package_versions": package_versions(),
        "quantum_backend": "pennylane/default.qubit",
        "host_info": host_info(),
        "start_time": start_time,
        "end_time": end_time,
        "steps_run": steps_run or [],
        "random_seeds": {"seed_root": cfg.seed_root, "seed_streams": cfg.seed_streams},
        "model_formulas": {
            "H1_exact_signal": H1_FORMULA,
            "H2_H4_estimator_snr": H2_H4_FORMULA,
            "sensitivity_estimator_snr": SENSITIVITY_FORMULA,
        },
        "transform_definitions": {
            "H1_response": "a = asinh(abs(exact_gradient))",
            "H2_H4_response": "y = asinh(SNR_est)",
            "depth_standardization": "depth_z = (depth - mean(design.depths)) / std(design.depths, ddof=0)",
        },
        "bootstrap_iterations": bootstrap_iterations or {},
        "failed_fit_counts": failed_fit_counts or {},
        "pilot_status": pilot_status or {},
    }


def write_manifest(results_dir: Path, manifest: dict) -> Path:
    results_dir = Path(results_dir)
    results_dir.mkdir(parents=True, exist_ok=True)
    out_path = results_dir / "run_manifest.json"
    out_path.write_text(json.dumps(manifest, indent=2, default=str), encoding="utf-8")
    return out_path


def now_iso() -> str:
    return datetime.datetime.now(datetime.timezone.utc).isoformat()
