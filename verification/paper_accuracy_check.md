# Paper accuracy check: every numeric claim in `main.tex`'s Results/Discussion/Appendix vs. the actual data

Independent cross-check of every specific numeric claim in `paper/main.tex`
(Abstract, Results §4, Discussion §5, Appendix A) against
`results/production_confirmatory/confirmatory_hypotheses.csv`, `results/production_confirmatory/holm_adjustment.csv`,
`results/production_confirmatory/snr_model_coefficients.csv`, `results/pilot_*.json`, the
`verification/*.md` documents, and (where a number wasn't already sitting in
a summary file) direct recomputation from `results/production_confirmatory/pointwise_gradient_statistics.parquet`,
`results/raw/*.parquet`, and `qnn_snr/` library calls. Every check below was
run against real files/code in this session, not recalled from memory.

## Result: 2 real discrepancies found and fixed; everything else confirmed

Both discrepancies traced to the same root cause: two auxiliary output files
(`results/production_confirmatory/pilot_initialization_selection.json` and the zero-variance-cell
rate computation feeding Section 4.1) were never regenerated after the
mode-pooling fix (`verification/mode_pooling_guard.md`), even though the
H2–H4 confirmatory fit itself was. Both are small numeric corrections that
leave every stated conclusion unchanged — neither meets the "serious enough
to change a Results or Discussion conclusion" bar, so both were fixed
directly rather than escalated.

### Fix 1 — Section 4.1, N_init pilot half-widths (stale, pooled-mode assumptions)

`results/production_confirmatory/pilot_initialization_selection.json`'s `true_coefs_from_pilot`
still held the old pooled-mode point estimates
(`E:L=0.023732, E:R=0.003528, L:R:depth_z=0.000511`) used to simulate
candidate-N half-widths, even though `cmd_pilot_initializations` itself was
already fixed (in the mode-pooling-guard pass) to filter to
`finite_shot_end_to_end` before fitting — the *code* path was correct, the
*stored output file* was simply never re-run through it. Reran
`python -m qnn_snr pilot-initializations --config configs/confirmatory.yaml`
for real (not a dry recomputation) to regenerate it:

| | Before (stale, pooled assumptions) | After (regenerated, end-to-end-only) |
|---|---|---|
| `true_coefs_from_pilot` | `E:L=0.023732, E:R=0.003528, L:R:depth_z=0.000511` (pooled) | `E:L=0.024996, E:R=-0.000958, L:R:depth_z=-0.010179` (matches adopted confirmatory numbers exactly) |
| 90th-pctile half-widths (E:L, E:R, L:R:depth_z) | 0.112, 0.112, 0.080 | **0.103, 0.103, 0.073** |
| Meets 0.20 target? | Yes | Yes (unchanged — comfortable margin either way) |
| Selected $N_{\mathrm{init}}$ | 50 | 50 (unchanged) |

**`main.tex` fixed**: "$0.112$, $0.112$, and $0.080$" → "$0.103$, $0.103$,
and $0.073$" (§4.1, sentence beginning "$N_{\mathrm{init}}$ converged
cleanly..."). The qualitative conclusion (converges cleanly at the floor
candidate, well under target) is unaffected — both old and new half-widths
clear the 0.20 target with room to spare.

### Fix 2 — Section 4.1, zero-replicate-variance rates (stale, pooled-mode)

The stated rates ("$4.3\%$ at block count 1/budget 250 down to $1.3\%$...,
versus $0.4$–$1.5\%$ at every deeper block count") were checked by computing
`zero_variance_flag` rates directly from
`results/production_confirmatory/pointwise_gradient_statistics.parquet`, filtered three ways:

| | depth 1/budget 250 | depth 1/budget 2000 | deeper-depth range |
|---|---|---|---|
| Pooled (both modes) | 4.28% → rounds to **4.3%** | 1.31% | 0.37–1.53% → rounds to **0.4–1.5%** |
| **End-to-end-only (adopted confirmatory mode)** | **4.375% → rounds to 4.4%** | **1.31%** | **0.11–1.06% → rounds to 0.1–1.1%** |
| Conditional-only | 4.19% | 1.31% | 0.63–2.00% |

The paper's stated figures (4.3%, 0.4–1.5%) match the **pooled** computation,
not the end-to-end-only one that every other section of the paper now
uses — a direct instance of the "stale number left over from before the
mode-pooling fix" pattern the task asked to look for. The depth-1/budget-2000
figure (1.3%) happens to be numerically identical across all three
groupings at that specific cell, so it required no change.

**`main.tex` fixed**: "$4.3\%$ ... $0.4$--$1.5\%$" → "$4.4\%$ ...
$0.1$--$1.1\%$" (§4.1). The qualitative conclusion ("$R_{\mathrm{rep}}$ did
not converge uniformly," "block-count-1 estimates carry wider uncertainty")
is unaffected — if anything the corrected end-to-end-only range is a
*smaller* worst-case rate than the pooled figure it replaces, not a
concerning direction of change.

## Everything else: confirmed, no changes needed

Checked directly against source files/recomputation (representative subset —
essentially every specific number in the Results/Discussion/Appendix was
checked; listing the categories with their verification source):

| Claim category | Source checked | Status |
|---|---|---|
| H1–H4 point estimates, SEs, z, raw p, Holm p (§4.2–4.4, Table 2) | `results/production_confirmatory/confirmatory_hypotheses.csv`, `results/production_confirmatory/holm_adjustment.csv` (bit-for-bit) | Confirmed |
| Bootstrap CIs and achieved $n$ for H1–H4 (Table 2, §4.2–4.4) | `verification/h2h4_bootstrap_memory_redesign.md`, `verification/h2h4_bootstrap_endtoend_only.md` | Confirmed |
| H1 finite-difference validation (worst rel. error 1.27e-5/9.77e-7, 224 comparisons, 16 points) | `verification/h1_finite_difference_check.md` | Confirmed |
| H1 ad hoc $E{:}L{:}\widetilde D$ refit ($+0.003805$, $+0.001005$, SE $0.001125$) | `verification/h1_el_depth_sensitivity_results.json` / `.md` | Confirmed (see note below) |
| H1 $h$-convergence ratio 3.49 | `verification/h1_finite_difference_check.md` §3 | Confirmed (the "previously 4.1" prior value is not independently checkable from this session, but the corrected value 3.49 is verified) |
| H2 conditional/end-to-end split (0.0232, 0.0250) | `verification/conditional_vs_endtoend_comparison.md` | Confirmed |
| H2 bootstrap history ($n=8$ median 0.0215, $n=100$ median 0.0245, $n=100$ vs $n=400$ widths 0.078/0.084) | `verification/h2h4_bootstrap_memory_redesign.md` §5/§8 | Confirmed, incl. independently recomputed CI widths (0.077971→0.078, 0.083648→0.084) — note: the source doc's own §8 prose states "0.0776" for the $n=100$ width, which is itself a minor arithmetic slip (true value 0.077971→0.078); **`main.tex`'s "0.078" is the mathematically correct rounding and required no fix** |
| H3/H4 $D\ge3$ sensitivity fits | `verification/d_ge_3_sensitivity_refit.md` addendum | Confirmed |
| H4 mode-split ($+0.0104$/$p{=}0.094$ vs $-0.0102$/$p{=}0.058$) | `verification/conditional_vs_endtoend_comparison.md` | Confirmed |
| $\beta_{ELR}$ end-to-end-only vs. pooled | `verification/three_way_interaction_endtoend_only.md` | Confirmed |
| Fold-change indices $I_{AB}$/$J_{AB}$ | `verification/mode_split_descriptive_stats.md` | Confirmed |
| Q1 performance comparison (20/20, 4/20 vs 9/20) | `verification/q1_performance_comparison_endtoend_only.md` | Confirmed |
| Entanglement entropy/purity ranges, per-init SD, regression $p\approx0.30$–$0.35$ | `verification/depth_entanglement_by_depth_check.md` | Confirmed |
| Bias/sign-agreement by mode (0.842/0.869/0.814, 0.00329/0.00265/0.00416) | `verification/mode_split_descriptive_stats.md` | Confirmed |
| Resource accounting ($\sim$27% circuit-count gap at block count 6) | `verification/budget_definition_and_realized_shots.md` (48 vs. 61 circuits, $(61{-}48)/48=27.08\%$) | Confirmed |
| Memory/wall-clock figures (5.6GB, 4.8GB, 5.3GB, 11MB near-miss, 8.637GB margin) | `verification/h2h4_bootstrap_memory_redesign.md` §1/§6/§8 | Confirmed |
| Test suite count ("26 tests across five files") | Actually reran `pytest tests/test_models.py tests/test_bootstrap.py tests/test_pilot.py tests/test_report.py tests/test_cli.py -q` in this session | Confirmed — 26 passed |
| $E_0\approx-3.4270$, $E_{\max}\approx3.4270$ | Recomputed directly via `qnn_snr.hamiltonian.diagonalize_tfim(4, 1.0, 0.5)` + `np.linalg.eigvalsh` | Confirmed ($-3.427034...$, $3.427034...$) |
| $R_{\mathrm{rep}}=200\to500$ recheck (270, ~170$\times$) | `verification/r_calibration_depth1.md`, `qnn_snr/config.py` (`max_R: int = 200` default) | Confirmed |
| 6.14-million-row combined dataset | $2\times3{,}072{,}000=6{,}144{,}000$ | Confirmed |
| Abstract's rounded figures (0.0043/0.013, 0.025/0.002, $-0.001$/0.90, $-0.010$/0.12) | Consistent roundings of the body's full-precision H1–H4 numbers | Confirmed |

## One claim upgraded from asserted to independently verified

Appendix A.10 states the regression test "reproduces the original bug
against the pre-fix code and passes against the fixed code." The original
`mode_pooling_guard.md` write-up reasoned about this counterfactually
("run against the pre-fix code, it fails...") without actually executing
it against pre-fix code. This session closed that gap: reconstructed the
exact pre-fix `build_h2h4_dataset` body (no `analysis_mode` guard) and
confirmed directly that (a) it silently pools the same 2-mode synthetic
frame the regression test uses, with no exception raised — i.e. the test's
`pytest.raises(ValueError)` assertion would genuinely fail against it — and
(b) the current guarded code does raise as expected. A.10's claim is now an
empirically checked fact, not a plausible-sounding assertion.

## Reproduction

```bash
python -m qnn_snr pilot-initializations --config configs/confirmatory.yaml
```
```python
import pandas as pd, numpy as np
pw = pd.read_parquet("results/production_confirmatory/pointwise_gradient_statistics.parquet")
for mode in (None, "finite_shot_end_to_end", "finite_shot_conditional"):
    sub = pw if mode is None else pw[pw["analysis_mode"] == mode]
    print(mode, sub.groupby(["depth","budget"])["zero_variance_flag"].mean())
```
