"""Regression tests for paper/scripts/make_fig0_el_primary.py -- the
regenerated, data-derived replacement for the previously-untrusted
fig0_el_primary.pdf (verification/fig0_el_primary_regeneration.md).
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

import qnn_snr

REPO_ROOT = Path(qnn_snr.__file__).resolve().parent.parent
SCRIPTS_DIR = REPO_ROOT / "paper" / "scripts"
sys.path.insert(0, str(SCRIPTS_DIR))

import make_fig0_el_primary as fig0  # noqa: E402
from qnn_snr.stats.interactions import compute_interaction_indices


def _pointwise(config_snr: dict[int, list[float]], mode: str = "finite_shot_end_to_end") -> pd.DataFrame:
    rows = []
    for cid, vals in config_snr.items():
        for v in vals:
            rows.append({"configuration_id": cid, "SNR_est": v, "analysis_mode": mode})
    return pd.DataFrame(rows)


def _exact(config_grad: dict[int, list[float]], depth=1, budget=0) -> pd.DataFrame:
    rows = []
    for cid, vals in config_grad.items():
        for i, v in enumerate(vals):
            rows.append({"configuration_id": cid, "exact_gradient": v, "analysis_mode": "statevector_exact",
                         "depth": depth, "parameter_id": i, "initialization_id": i, "budget": budget})
    return pd.DataFrame(rows)


CONFIGS = (fig0.CONFIG_BASELINE, fig0.CONFIG_E, fig0.CONFIG_L, fig0.CONFIG_EL)


# --- 1. the plotting script never reads fig0_el_primary.pdf as input ---

def test_script_never_reads_its_own_pdf_output():
    src = (SCRIPTS_DIR / "make_fig0_el_primary.py").read_text(encoding="utf-8")
    # the only permitted operations on PDF_OUT are existence checks and a rename (backup);
    # there must be no open()/read_bytes()/read() call against it.
    assert "PDF_OUT.exists()" in src
    assert "PDF_OUT.rename(" in src
    forbidden = ["PDF_OUT.read_bytes(", "open(PDF_OUT", "PDF_OUT.open("]
    for pat in forbidden:
        assert pat not in src, f"script must never read {pat!r}"


# --- 2 & 3. I_EL uses only finite_shot_end_to_end; conditional rows cannot enter it ---

def test_filter_pointwise_end_to_end_excludes_conditional_rows():
    mixed = pd.concat([
        _pointwise({1: [1.0]}, mode="finite_shot_end_to_end"),
        _pointwise({1: [999.0]}, mode="finite_shot_conditional"),
    ], ignore_index=True)
    filtered = fig0.filter_pointwise_end_to_end(mixed)
    assert (filtered["analysis_mode"] == "finite_shot_end_to_end").all()
    assert 999.0 not in filtered["SNR_est"].to_numpy()


def test_filter_pointwise_end_to_end_raises_if_mode_absent():
    conditional_only = _pointwise({1: [1.0]}, mode="finite_shot_conditional")
    with pytest.raises(ValueError, match="finite_shot_end_to_end"):
        fig0.filter_pointwise_end_to_end(conditional_only)


# --- 4. exact rows are not duplicated across budgets or estimator modes ---

def test_duplicate_exact_rows_across_budgets_raise():
    ex = _exact({1: [1.0]})
    dup = pd.concat([ex, ex.assign(budget=1)], ignore_index=True)  # same cell, different budget
    with pytest.raises(ValueError, match="duplicated"):
        fig0.check_no_duplicate_exact_rows(dup)


def test_clean_exact_rows_pass_duplication_check():
    ex = _exact({c: [1.0, 2.0, 3.0] for c in CONFIGS})
    fig0.check_no_duplicate_exact_rows(ex)  # must not raise


# --- 5. configuration mapping is exactly 1, 2, 3, 5 ---

def test_configuration_mapping_is_1_2_3_5():
    assert (fig0.CONFIG_BASELINE, fig0.CONFIG_E, fig0.CONFIG_L, fig0.CONFIG_EL) == (1, 2, 3, 5)


# --- 6. RMS is computed as sqrt(mean(x**2)) ---

def test_rms_formula():
    vals = np.array([3.0, 4.0])
    assert fig0._rms(vals) == pytest.approx(np.sqrt(np.mean(vals ** 2)))
    assert fig0._rms(vals) == pytest.approx(np.sqrt((9 + 16) / 2))


def test_rms_drops_non_finite():
    vals = np.array([3.0, 4.0, np.inf, np.nan])
    assert fig0._rms(vals) == pytest.approx(np.sqrt((9 + 16) / 2))


# --- 7. formula is exactly combined * baseline / (single_E * single_L) ---

def test_compute_indices_manual_formula():
    pw = _pointwise({1: [2.0], 2: [2.0], 3: [2.0], 5: [4.0]})
    ex = _exact({1: [1.0], 2: [1.0], 3: [1.0], 5: [2.0]})
    out = fig0.compute_indices_manual(pw, ex, CONFIGS)
    # M_0=2, M_E=2, M_L=2, M_EL=4 -> I = (4*2)/(2*2) = 2.0
    assert out["I_EL"] == pytest.approx(2.0)
    # G_0=1, G_E=1, G_L=1, G_EL=2 -> J = (2*1)/(1*1) = 2.0
    assert out["J_EL"] == pytest.approx(2.0)


def test_compute_indices_manual_agrees_with_production_function():
    pw = _pointwise({c: [1.5, 2.5, 3.5] for c in range(1, 9)})
    ex = _exact({c: [0.5, 1.0] for c in range(1, 9)})
    manual = fig0.compute_indices_manual(pw, ex, CONFIGS)
    prod = compute_interaction_indices(pw, ex)
    prod_row = prod[prod["pair"] == "E_L"].iloc[0]
    assert manual["I_EL"] == pytest.approx(prod_row["I_AB"], abs=1e-12)
    assert manual["J_EL"] == pytest.approx(prod_row["J_AB"], abs=1e-12)


# --- 8. matched-point identity preserved across configurations ---

def test_matched_row_count_mismatch_raises():
    pw = _pointwise({1: [1.0, 1.0], 2: [1.0], 3: [1.0, 1.0], 5: [1.0, 1.0]})  # config 2 has 1 fewer row
    ex = _exact({c: [1.0, 1.0] for c in CONFIGS})
    with pytest.raises(ValueError, match="mismatch in raw pointwise row counts"):
        fig0.check_matched_row_counts(pw, ex, CONFIGS)


def test_matched_row_counts_pass_when_identical():
    pw = _pointwise({c: [1.0, 1.0] for c in CONFIGS})
    ex = _exact({c: [1.0, 1.0] for c in CONFIGS})
    info = fig0.check_matched_row_counts(pw, ex, CONFIGS)
    assert info["matched_point_count"] == 2


# --- 9. zero denominators raise an error ---

def test_zero_denominator_raises_not_epsilon():
    pw = _pointwise({1: [1.0], 2: [0.0], 3: [2.0], 5: [1.0]})  # M_E = 0
    ex = _exact({1: [1.0], 2: [1.0], 3: [1.0], 5: [1.0]})
    with pytest.raises(ValueError, match="zero denominator"):
        fig0.compute_indices_manual(pw, ex, CONFIGS)


# --- 10. recomputed values agree with the finalized table (production function), when one exists ---
# covered by test_compute_indices_manual_agrees_with_production_function above; repeated here
# against the REAL repository data, matching the script's own dual-computation cross-check.

REAL_POINTWISE = REPO_ROOT / "results" / "production_confirmatory" / "pointwise_gradient_statistics.parquet"
REAL_EXACT = REPO_ROOT / "results" / "production_confirmatory" / "raw" / "exact.parquet"


@pytest.mark.skipif(not (REAL_POINTWISE.exists() and REAL_EXACT.exists()),
                     reason="full confirmatory dataset not present in this checkout")
def test_real_data_manual_and_production_agree_and_round_correctly():
    pw = fig0.filter_pointwise_end_to_end(pd.read_parquet(REAL_POINTWISE))
    ex = fig0.filter_exact(pd.read_parquet(REAL_EXACT))
    fig0.check_no_duplicate_exact_rows(ex)
    fig0.check_matched_row_counts(pw, ex, CONFIGS)

    manual = fig0.compute_indices_manual(pw, ex, CONFIGS)
    prod = compute_interaction_indices(pw, ex)
    prod_row = prod[prod["pair"] == "E_L"].iloc[0]
    assert manual["I_EL"] == pytest.approx(prod_row["I_AB"], abs=1e-9)
    assert manual["J_EL"] == pytest.approx(prod_row["J_AB"], abs=1e-9)

    # --- 11. generated values round to 1.242 and 1.034 ---
    assert round(manual["I_EL"], 3) == 1.034
    assert round(manual["J_EL"], 3) == 1.242


# --- 12. the PDF and figure-source CSV are created ---

@pytest.mark.skipif(not (REAL_POINTWISE.exists() and REAL_EXACT.exists()),
                     reason="full confirmatory dataset not present in this checkout")
def test_script_run_produces_pdf_and_source_csv():
    import subprocess
    result = subprocess.run([sys.executable, str(SCRIPTS_DIR / "make_fig0_el_primary.py")],
                             cwd=REPO_ROOT, capture_output=True, text=True)
    assert result.returncode == 0, result.stdout + result.stderr
    assert fig0.PDF_OUT.exists()
    assert fig0.CSV_OUT.exists()
    csv = pd.read_csv(fig0.CSV_OUT)
    required_cols = {"metric", "analysis_mode", "baseline_aggregate", "E_only_aggregate",
                      "L_only_aggregate", "EL_aggregate", "interaction_index", "formula",
                      "source_file", "source_file_sha256", "row_count_before_filtering",
                      "row_count_after_filtering", "matched_point_count", "generated_at", "git_commit"}
    assert required_cols <= set(csv.columns)
    assert set(csv["metric"]) == {"I_EL", "J_EL"}


# --- 13. the manuscript-referenced figure path exists ---

def test_manuscript_referenced_figure_path_exists():
    main_tex = (REPO_ROOT / "paper" / "main.tex").read_text(encoding="utf-8")
    assert "figures/fig0_el_primary.pdf" in main_tex
    assert (REPO_ROOT / "paper" / "figures" / "fig0_el_primary.pdf").exists()
