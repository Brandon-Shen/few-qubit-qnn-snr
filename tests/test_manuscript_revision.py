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


def test_centered_notation_and_bootstrap_provenance():
    main = (ROOT / "paper/sn-article.tex").read_text(encoding="utf-8")
    supplement = (ROOT / "paper/supplemental.tex").read_text(encoding="utf-8")
    for forbidden in (r"\widetilde E_c", r"\widetilde L_c", r"\widetilde R_c"):
        assert forbidden not in main + supplement
    assert "D_z=(D-3.2)/1.7204650534085253" in main
    assert all(term in main for term in ("E_cL_cR_c", "E_cD_{z,d}", "L_cD_{z,d}", "R_cD_{z,d}", "L_cR_cD_{z,d}"))
    assert "443" in supplement and "zero failures" in supplement


def test_canonical_submission_sources_are_byte_identical():
    main = (ROOT / "paper/sn-article.tex").read_text(encoding="utf-8")
    assert (ROOT / "paper/sn-article.tex").read_bytes() == (ROOT / "submission_package/main.tex").read_bytes()
    assert (ROOT / "paper/supplemental.tex").read_bytes() == (ROOT / "submission_package/ESM_1.tex").read_bytes()
    assert "0.004346" not in main and "0.024996" not in main


def test_final_availability_identifiers_are_explicit():
    main = (ROOT / "paper/sn-article.tex").read_text(encoding="utf-8")
    supplement = (ROOT / "paper/supplemental.tex").read_text(encoding="utf-8")
    required = (
        "results/final\\_submission\\_v1/manifest.json",
        "submission-numerical-results-freeze-v1",
        "sncs-submission-v1",
        "https://github.com/Brandon-Shen/few-qubit-qnn-snr/tree/sncs-submission-v1",
        "MANUSCRIPT\\_COMMIT.txt",
    )
    assert all(token in main for token in required)
    assert all(token in supplement for token in required)
