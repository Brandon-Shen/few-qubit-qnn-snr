"""Figure 0 (fig:el-primary): secondary multiplicative interaction indices
I_EL_given_R0 (end-to-end estimator SNR) and J_EL_given_R0
(exact-gradient magnitude) for the E x L pair conditional on R=0.

This script replaces a prior `fig0_el_primary.pdf` that was found to be
untrusted: no generation script for it existed anywhere in this repository
or its git history (verified by direct search before writing this file),
and the file itself did not exist on disk at all (paper/scripts/structural_check.py
reported it as a MISSING GRAPHIC). Every number below is therefore computed
fresh from frozen machine-readable data, never read from any old PDF,
caption text, or manuscript prose.

Source-of-truth rules (see verification/fig0_el_primary_regeneration.md):
  - I_EL uses ONLY analysis_mode == "finite_shot_end_to_end" rows from
    results/production_confirmatory/pointwise_gradient_statistics.parquet
    (SNR_est column). The conditional-mode rows in that same file are never
    touched here.
  - J_EL uses results/production_confirmatory/raw/exact.parquet, analysis_mode == "statevector_exact"
    (exact_gradient column, absolute value). This mode has no budget/estimator
    dependence at all (budget is uniformly 0, exactly one row per
    (configuration, depth, parameter_id, initialization_id) cell -- verified
    directly, not assumed), so no deduplication step is needed or performed.
  - Configuration mapping (qnn_snr.stats.interactions.PAIR_SPECS, unchanged):
    baseline=1 (E=0,L=0,R=0), E-only=2 (E=1,L=0,R=0), L-only=3 (E=0,L=1,R=0),
    E+L=5 (E=1,L=1,R=0).
  - RMS = sqrt(mean(finite(x)**2)) (matches qnn_snr.stats.interactions._rms
    exactly).
  - I_EL/J_EL are computed TWO independent ways and required to agree to a
    strict tolerance before anything is written or plotted:
      (a) the validated production function
          qnn_snr.stats.interactions.compute_interaction_indices(), and
      (b) an independent, from-scratch numpy recomputation in this script
          that does not call (a) at all.
    Disagreement beyond the tolerance aborts the script (see `--tolerance`).
"""
from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

sys.path.insert(0, str(Path(__file__).parent))
from plot_style import (
    COLOR_SERIES_A, COLOR_SERIES_B, COLOR_NEUTRAL, TEXT_WIDTH_IN,
    ANNOTATION_FONT_SIZE, ZERO_LINE_KW, apply_style,
)

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT))
from qnn_snr.stats.interactions import compute_interaction_indices  # noqa: E402

POINTWISE_PATH = REPO_ROOT / "results" / "production_confirmatory" / "pointwise_gradient_statistics.parquet"
EXACT_PATH = REPO_ROOT / "results" / "production_confirmatory" / "raw" / "exact.parquet"
RUN_MANIFEST_PATH = REPO_ROOT / "results" / "production_confirmatory" / "run_manifest.json"
CONFIRMATORY_MODE = "finite_shot_end_to_end"
EXACT_MODE = "statevector_exact"

# baseline, E-only, L-only, E+L -- identical to qnn_snr.stats.interactions.PAIR_SPECS's E_L row
CONFIG_BASELINE, CONFIG_E, CONFIG_L, CONFIG_EL = 1, 2, 3, 5

CSV_OUT = REPO_ROOT / "paper" / "figure_data" / "fig0_el_primary_source.csv"
PDF_OUT = REPO_ROOT / "paper" / "figures" / "fig0_el_primary.pdf"
PNG_OUT = PDF_OUT.with_name(PDF_OUT.stem + "_preview.png")
BACKUP_OUT = REPO_ROOT / "paper" / "figures" / "fig0_el_primary.placeholder_backup.pdf"

STRICT_TOLERANCE = 1e-9  # for cross-checking the two independent computations
EXPECTED_I_EL_ROUNDED = 1.034
EXPECTED_J_EL_ROUNDED = 1.242


def sha256_of(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def _rms(values: np.ndarray) -> float:
    finite = values[np.isfinite(values)]
    if len(finite) == 0:
        return float("nan")
    return float(np.sqrt(np.mean(finite ** 2)))


def filter_pointwise_end_to_end(pw_all: pd.DataFrame) -> pd.DataFrame:
    """Isolate I_EL's input to end-to-end-mode rows only. Raises if the
    requested mode is entirely absent (rather than silently returning an
    empty frame) and re-asserts, post-filter, that no other mode leaked in."""
    if CONFIRMATORY_MODE not in pw_all["analysis_mode"].unique():
        raise ValueError(f"input does not contain {CONFIRMATORY_MODE!r} rows")
    pw = pw_all[pw_all["analysis_mode"] == CONFIRMATORY_MODE].copy()
    if (pw["analysis_mode"] != CONFIRMATORY_MODE).any():
        raise ValueError("pooled analysis_mode leaked into the I_EL computation")
    return pw


def filter_exact(exact_all: pd.DataFrame) -> pd.DataFrame:
    """Isolate J_EL's input to statevector_exact rows only."""
    exact_df = exact_all[exact_all["analysis_mode"] == EXACT_MODE].copy()
    if (exact_df["analysis_mode"] != EXACT_MODE).any():
        raise ValueError("non-exact analysis_mode leaked into the J_EL computation")
    return exact_df


def check_no_duplicate_exact_rows(exact_df: pd.DataFrame) -> None:
    """Guards against exact rows being duplicated across budgets/estimator
    modes (exact_gradient has no such dependence): requires exactly one row
    per (configuration, depth, parameter, initialization) cell and a single
    distinct budget value."""
    dup_check = exact_df.groupby(["configuration_id", "depth", "parameter_id", "initialization_id"]).size()
    if (dup_check != 1).any():
        raise ValueError("exact data has duplicated (config, depth, parameter, init) rows -- "
                          "aborting rather than silently deduplicating or double-counting")
    if exact_df["budget"].nunique() != 1:
        raise ValueError("exact data unexpectedly has more than one distinct budget value")


def check_matched_row_counts(pw: pd.DataFrame, exact_df: pd.DataFrame, configs) -> dict:
    """Raises if the four configurations of interest do not share identical
    raw row counts (the shared-seed factorial design guarantees this; a
    mismatch would indicate a data problem, not something to paper over)."""
    pw_row_counts = {cfg: int((pw["configuration_id"] == cfg).sum()) for cfg in configs}
    exact_row_counts = {cfg: int((exact_df["configuration_id"] == cfg).sum()) for cfg in configs}
    if len(set(pw_row_counts.values())) != 1:
        raise ValueError(f"unexpected mismatch in raw pointwise row counts across configurations: "
                          f"{pw_row_counts}")
    if len(set(exact_row_counts.values())) != 1:
        raise ValueError(f"unexpected mismatch in raw exact row counts across configurations: "
                          f"{exact_row_counts}")
    return {"pointwise": pw_row_counts, "exact": exact_row_counts,
            "matched_point_count": next(iter(pw_row_counts.values()))}


def compute_indices_manual(pw: pd.DataFrame, exact_df: pd.DataFrame, configs) -> dict:
    """Independent, from-scratch recomputation of I_EL/J_EL (does not call
    qnn_snr.stats.interactions.compute_interaction_indices) -- exact formula:
    combined * baseline / (single_E * single_L), aggregate = RMS."""
    c0, cE, cL, cEL = configs
    M = {cfg: _rms(pw.loc[pw["configuration_id"] == cfg, "SNR_est"].to_numpy()) for cfg in configs}
    G = {cfg: _rms(np.abs(exact_df.loc[exact_df["configuration_id"] == cfg, "exact_gradient"].to_numpy()))
         for cfg in configs}
    M0, ME, ML, MEL = M[c0], M[cE], M[cL], M[cEL]
    G0, GE, GL, GEL = G[c0], G[cE], G[cL], G[cEL]
    if ME == 0.0 or ML == 0.0:
        raise ValueError(f"zero denominator in I_EL recomputation: M_E={ME}, M_L={ML}")
    if GE == 0.0 or GL == 0.0:
        raise ValueError(f"zero denominator in J_EL recomputation: G_E={GE}, G_L={GL}")
    return {
        "I_EL": (MEL * M0) / (ME * ML), "J_EL": (GEL * G0) / (GE * GL),
        "M_0": M0, "M_E": ME, "M_L": ML, "M_EL": MEL,
        "G_0": G0, "G_E": GE, "G_L": GL, "G_EL": GEL,
    }


def main():
    # Only back up an existing PDF the FIRST time this validated pipeline runs
    # (detected by the absence of its own source-of-truth CSV): a PDF present
    # at that point was never produced by this script and is untrusted by
    # definition. On every subsequent run, CSV_OUT already exists, so an
    # existing PDF_OUT is this script's own prior validated output, not a
    # placeholder -- it is simply overwritten (as savefig would do anyway),
    # not "backed up as untrusted" a second time.
    if PDF_OUT.exists() and not CSV_OUT.exists():
        BACKUP_OUT.parent.mkdir(parents=True, exist_ok=True)
        PDF_OUT.rename(BACKUP_OUT)
        print(f"Backed up pre-existing, untrusted (never produced by this script) {PDF_OUT} "
              f"-> {BACKUP_OUT} -- NOT described as a validated prior figure.")
    elif not PDF_OUT.exists():
        print(f"No existing {PDF_OUT} found -- nothing to back up "
              f"(consistent with structural_check.py's prior MISSING GRAPHIC report).")
    else:
        print(f"{PDF_OUT} already exists and {CSV_OUT.name} already exists, so this is a "
              f"regeneration of this script's own prior validated output, not an untrusted "
              f"placeholder -- overwriting directly, no additional backup made.")

    configs = (CONFIG_BASELINE, CONFIG_E, CONFIG_L, CONFIG_EL)

    # ---- load and filter, keeping end-to-end and exact strictly separate ----
    pw_all = pd.read_parquet(POINTWISE_PATH)
    pw_row_count_before = len(pw_all)
    pw = filter_pointwise_end_to_end(pw_all)
    pw_row_count_after = len(pw)

    exact_all = pd.read_parquet(EXACT_PATH)
    exact_row_count_before = len(exact_all)
    exact_df = filter_exact(exact_all)
    exact_row_count_after = len(exact_df)

    check_no_duplicate_exact_rows(exact_df)
    match_info = check_matched_row_counts(pw, exact_df, configs)
    matched_point_count = match_info["matched_point_count"]
    print(f"Matched raw row count per configuration (pointwise, end-to-end): {match_info['pointwise']}")
    print(f"Matched raw row count per configuration (exact): {match_info['exact']}")

    finite_snr_counts = {cfg: int(np.isfinite(pw.loc[pw["configuration_id"] == cfg, "SNR_est"]).sum())
                         for cfg in configs}
    print(f"Finite SNR_est count per configuration (after zero-variance exclusion): "
          f"{finite_snr_counts} -- L=0 configs (1, 2) show exclusions, L=1 configs (3, 5) do not, "
          f"consistent with the exactly-L=0-confined zero-variance pattern already documented "
          f"in verification/zero_variance_exclusion_audit.md; this is expected, not an error.")

    # ---- (a) production function ----
    prod_result = compute_interaction_indices(pw, exact_df)
    prod_row = prod_result[prod_result["pair"] == "E_L"].iloc[0]
    I_EL_prod, J_EL_prod = prod_row["I_AB"], prod_row["J_AB"]
    if prod_row["I_AB_undefined_reason"] is not None or prod_row["J_AB_undefined_reason"] is not None:
        raise ValueError(f"production interaction-index computation returned undefined: "
                          f"I reason={prod_row['I_AB_undefined_reason']!r}, "
                          f"J reason={prod_row['J_AB_undefined_reason']!r}")

    # ---- (b) independent from-scratch recomputation (does not call (a)) ----
    manual = compute_indices_manual(pw, exact_df, configs)
    I_EL_manual, J_EL_manual = manual["I_EL"], manual["J_EL"]
    M0, ME, ML, MEL = manual["M_0"], manual["M_E"], manual["M_L"], manual["M_EL"]
    G0, GE, GL, GEL = manual["G_0"], manual["G_E"], manual["G_L"], manual["G_EL"]

    # ---- cross-check ----
    for name, a, b in (("I_EL", I_EL_prod, I_EL_manual), ("J_EL", J_EL_prod, J_EL_manual)):
        if not np.isclose(a, b, rtol=0, atol=STRICT_TOLERANCE):
            raise ValueError(f"{name} disagreement between production function ({a!r}) and "
                              f"independent recomputation ({b!r}) exceeds tolerance {STRICT_TOLERANCE}")
    print(f"CONFIRMED: production function and independent recomputation agree to atol={STRICT_TOLERANCE} "
          f"for both I_EL and J_EL.")

    I_EL, J_EL = I_EL_manual, J_EL_manual  # use the from-scratch value; both are validated identical

    # ---- regression targets (validation, not input constants) ----
    if round(I_EL, 3) != EXPECTED_I_EL_ROUNDED:
        raise ValueError(f"I_EL={I_EL!r} rounds to {round(I_EL, 3)}, expected {EXPECTED_I_EL_ROUNDED} "
                          f"(manuscript/regression target) -- stopping rather than plotting a "
                          f"disagreeing value.")
    if round(J_EL, 3) != EXPECTED_J_EL_ROUNDED:
        raise ValueError(f"J_EL={J_EL!r} rounds to {round(J_EL, 3)}, expected {EXPECTED_J_EL_ROUNDED} "
                          f"(manuscript/regression target) -- stopping rather than plotting a "
                          f"disagreeing value.")
    print(f"CONFIRMED: I_EL rounds to {EXPECTED_I_EL_ROUNDED}, J_EL rounds to {EXPECTED_J_EL_ROUNDED} "
          f"(validation targets, matched).")

    print(f"\nFull precision: I_EL = {I_EL!r}")
    print(f"Full precision: J_EL = {J_EL!r}")
    print(f"Component aggregates (RMS): M_0={M0!r} M_E={ME!r} M_L={ML!r} M_EL={MEL!r}")
    print(f"Component aggregates (RMS): G_0={G0!r} G_E={GE!r} G_L={GL!r} G_EL={GEL!r}")

    # ---- write figure-source CSV ----
    source_manifest = json.loads(RUN_MANIFEST_PATH.read_text(encoding="utf-8"))
    git_commit = source_manifest["git_commit"]
    generated_at = source_manifest["end_time"]
    pw_hash = sha256_of(POINTWISE_PATH)
    exact_hash = sha256_of(EXACT_PATH)

    rows = [
        {
            "metric": "I_EL_given_R0", "analysis_mode": CONFIRMATORY_MODE,
            "baseline_aggregate": M0, "E_only_aggregate": ME, "L_only_aggregate": ML,
            "EL_aggregate": MEL, "interaction_index": I_EL,
            "formula": "combined * baseline / (single_E * single_L), aggregate = RMS(SNR_est)",
            "source_file": POINTWISE_PATH.relative_to(REPO_ROOT).as_posix(), "source_file_sha256": pw_hash,
            "row_count_before_filtering": pw_row_count_before, "row_count_after_filtering": pw_row_count_after,
            "matched_point_count": matched_point_count, "generated_at": generated_at, "git_commit": git_commit,
        },
        {
            "metric": "J_EL_given_R0", "analysis_mode": EXACT_MODE,
            "baseline_aggregate": G0, "E_only_aggregate": GE, "L_only_aggregate": GL,
            "EL_aggregate": GEL, "interaction_index": J_EL,
            "formula": "combined * baseline / (single_E * single_L), aggregate = RMS(abs(exact_gradient))",
            "source_file": EXACT_PATH.relative_to(REPO_ROOT).as_posix(), "source_file_sha256": exact_hash,
            "row_count_before_filtering": exact_row_count_before, "row_count_after_filtering": exact_row_count_after,
            "matched_point_count": matched_point_count, "generated_at": generated_at, "git_commit": git_commit,
        },
    ]
    CSV_OUT.parent.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(rows).to_csv(CSV_OUT, index=False)
    print(f"\nwrote {CSV_OUT}")
    print(f"source CSV sha256: {sha256_of(CSV_OUT)}")

    # ---- figure ----
    apply_style()
    fig, ax = plt.subplots(figsize=(TEXT_WIDTH_IN * 0.64, 1.8))

    rows_plot = [
        (r"Exact-gradient magnitude, $J_{EL\mid R=0}$", J_EL, COLOR_SERIES_A, "o"),
        (r"End-to-end estimator SNR, $I_{EL\mid R=0}$", I_EL, COLOR_SERIES_B, "s"),
    ]
    y_positions = np.arange(len(rows_plot))[::-1]
    for i, (_label, val, color, marker) in enumerate(rows_plot):
        y = y_positions[i]
        ax.plot(val, y, marker=marker, color=color, markersize=6, zorder=4)
        ax.annotate(f"{val:.3f}", xy=(val, y), xytext=(8, 0), textcoords="offset points",
                    va="center", ha="left", fontsize=ANNOTATION_FONT_SIZE, color=color)

    ax.axvline(1.0, **ZERO_LINE_KW)
    ax.annotate("Multiplicative\nindependence", xy=(1.0, -0.45), xycoords="data",
                ha="center", va="top", fontsize=ANNOTATION_FONT_SIZE - 0.5, color=COLOR_NEUTRAL,
                zorder=5, bbox=dict(facecolor="white", edgecolor="none", pad=1.2))

    ax.set_yticks(y_positions)
    ax.set_yticklabels([r[0] for r in rows_plot])
    ax.set_xlabel("Secondary multiplicative interaction index")
    ax.set_title(r"Primary $E \times L$ Interaction: Practical Magnitude",
                 fontsize=ANNOTATION_FONT_SIZE + 1)
    lo = min(1.0, I_EL, J_EL) - 0.06
    hi = max(1.0, I_EL, J_EL) + 0.09
    ax.set_xlim(lo, hi)
    ax.set_ylim(-1.35, len(rows_plot) - 0.35)

    fig.tight_layout()
    PDF_OUT.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(PDF_OUT, metadata={"CreationDate": None, "ModDate": None,
                                   "Creator": "few-qubit-qnn-snr deterministic figure generator"})
    fig.savefig(PNG_OUT, dpi=200)
    print(f"\nwrote {PDF_OUT}")
    print(f"PDF sha256: {sha256_of(PDF_OUT)}")
    print(f"wrote {PNG_OUT}")


if __name__ == "__main__":
    main()
