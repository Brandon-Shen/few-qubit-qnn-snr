"""Generate the machine-readable pre-submission provenance freeze records."""
from __future__ import annotations

import hashlib
import importlib.metadata
import json
import platform
import subprocess
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "verification"
INPUTS = [
    "results/production_confirmatory/raw/exact.parquet",
    "results/production_confirmatory/raw/finite_shot_end_to_end.parquet",
    "results/production_confirmatory/raw/finite_shot_conditional.parquet",
    "results/h2_replication_v1/_pipeline_output_stage1/raw/exact.parquet",
    "results/h2_replication_v1/_pipeline_output_stage1/raw/finite_shot_end_to_end.parquet",
]
DOCUMENTS = ["paper/main.tex", "paper/supplemental.tex"]
PACKAGES = ["numpy", "pandas", "scipy", "statsmodels", "pyarrow", "pennylane", "matplotlib"]


def git(*args: str) -> str:
    return subprocess.check_output(["git", *args], cwd=ROOT, text=True).strip()


def sha256(relpath: str) -> str:
    digest = hashlib.sha256()
    with (ROOT / relpath).open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def main() -> None:
    files = INPUTS + DOCUMENTS
    missing = [path for path in files if not (ROOT / path).is_file()]
    if missing:
        raise FileNotFoundError(f"Freeze inputs missing: {missing}")
    checksums = {path: sha256(path) for path in files}
    manifest = {
        "schema_version": 1,
        "freeze_kind": "pre_submission_pre_analysis",
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "git": {
            "commit": git("rev-parse", "HEAD"),
            "branch": git("branch", "--show-current"),
            "tracked_file_status": git("status", "--short", "--untracked-files=no").splitlines(),
        },
        "scientific_input_datasets": [
            {"path": path, "sha256": checksums[path], "bytes": (ROOT / path).stat().st_size}
            for path in INPUTS
        ],
        "manuscript_documents": [
            {"path": path, "sha256": checksums[path], "bytes": (ROOT / path).stat().st_size}
            for path in DOCUMENTS
        ],
        "environment": {
            "operating_system": platform.platform(),
            "python": platform.python_version(),
            "packages": {name: importlib.metadata.version(name) for name in PACKAGES},
        },
        "deliberate_exclusions": [
            ".claude/settings.local.json (untracked local tooling configuration)",
            "caches, virtual environments, downloaded dependencies, and temporary files",
        ],
    }
    (OUT / "pre_submission_freeze.json").write_text(
        json.dumps(manifest, indent=2) + "\n", encoding="utf-8"
    )
    (OUT / "input_checksums.sha256").write_text(
        "".join(f"{checksums[path]}  {path}\n" for path in files), encoding="utf-8"
    )


if __name__ == "__main__":
    main()
