import json, subprocess, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

def test_manuscript_frozen_value_checker(tmp_path):
    out = tmp_path / "check.json"
    subprocess.run([sys.executable, "scripts/check_manuscript_frozen_values.py", "--output", str(out)], cwd=ROOT, check=True)
    result = json.loads(out.read_text())
    assert result["status"] == "pass"
    assert 150 <= result["abstract_word_count"] <= 250

def test_manuscript_and_supplement_sources_and_assets():
    main = (ROOT / "paper/sn-article.tex").read_text(encoding="utf-8")
    supp = (ROOT / "paper/supplemental.tex").read_text(encoding="utf-8")
    assert "Online Resource 1" in main and "Online Resource 1" in supp
    for source in (main, supp):
        for asset in __import__("re").findall(r"\\includegraphics(?:\[[^]]*\])?\{([^}]+)\}", source):
            assert (ROOT / "paper" / asset).exists(), asset

def test_frozen_figures_and_tables_are_consistent():
    main = (ROOT / "paper/sn-article.tex").read_text(encoding="utf-8")
    assert "2,000" in main and "443" in main and "50 independent" in main
    assert "I_{EL\\mid R=0}" in main and "J_{EL\\mid R=0}" in main
    assert "0.004346" not in main and "0.024996" not in main
