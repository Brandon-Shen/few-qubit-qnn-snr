import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_protected_text_artifacts_use_lf():
    for path in (
        ROOT / "paper/sn-article.tex",
        ROOT / "paper/supplemental.tex",
        ROOT / "results/final_submission_v1/manifest.json",
        ROOT / "results/final_submission_v1/final_numerical_results.csv",
    ):
        assert b"\r\n" not in path.read_bytes(), path


def test_active_checksum_inventories_verify():
    subprocess.run([sys.executable, "scripts/regenerate_checksum_inventories.py", "--check"], cwd=ROOT, check=True)
