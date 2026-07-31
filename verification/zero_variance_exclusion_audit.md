# QMI/QIP robustness package -- Task 2: zero-variance exclusion audit

Uses the production `zero_variance_flag` column in
`results/pointwise_gradient_statistics.parquet` directly (exactly-zero
across-replicate sample variance, `ddof=1`, `ZERO_VARIANCE_TOL=0.0`,
`qnn_snr/stats/pointwise.py`) -- not re-derived from any rounded output.
Confirmed this is the *only* exclusion mechanism the confirmatory model
uses: every row with non-finite `SNR_est` has `zero_variance_flag=True`
(0 rows in `verification/_zero_variance_other_exclusion_reasons.csv`), so
there is no other exclusion reason to separately account for.

## Headline finding, stated before the tables

**Zero-variance exclusion is perfectly and deterministically confined to
`L=0` (global-cost/infidelity configurations) across the *entire* dataset --
not just at `D=1`, and not just in end-to-end mode.** Checked directly
across all 204,800 pointwise cells in both `finite_shot_end_to_end` and
`finite_shot_conditional`: **zero cells with `L=1` are ever flagged
zero-variance, in either mode, at any depth, budget, or `E`/`R` value**
(1,833 total flagged cells across both modes, all with `L=0`). This is a
previously-unreported, exact (not approximate) structural pattern, not a
D=1-specific artifact -- D=1 simply has the highest *rate* of this L=0-only
phenomenon, it does not introduce a new failure mode absent elsewhere.

**This is flagged per the QMI/QIP prompt's own stop condition ("zero-variance
exclusions are strongly concentrated in one intervention configuration
rather than mainly explained by D=1")**, read here as applying to
concentration in one intervention *factor level* (`L=0`, spanning
configurations 1, 2, 4, 6) rather than literally one single configuration
number, since that is the pattern actually present. **No manuscript prose
has been written asserting a mechanism for this pattern or declaring it
inconsequential; it is reported here for the user's judgment.** Two
observations relevant to that judgment, offered without resolving the
question:

- The pattern is *exact*, not merely more common at `L=0` -- every one of
  102,400 `L=1` cells per mode has nonzero replicate variance, with no
  exceptions, across 5 depths, 4 budgets, 2 `E` values, 2 `R` values, and 2
  modes. An exact zero-rate over that many cells is a strong signature of a
  structural property of the local-cost estimator (normalized TFIM energy)
  rather than a coincidental sampling outcome.
- `L` is one of the two factors in `beta_EL` (H2, the rejected
  entanglement-by-local-cost interaction) and appears in the `H2_H4_FORMULA`
  model both as a main effect and inside every interaction term involving
  `L`. Since exclusions never touch `L=1` rows, the fitted model's `L=1`
  arm is, in this specific sense, complete (no cell ever drops out) while
  its `L=0` arm loses up to 11.5% of cells in the worst single
  configuration/budget/depth combination (`D=1`, config 1, `B=250`). This is
  reported as a structural asymmetry in the model's effective input, not as
  evidence that any coefficient is biased -- resolving whether it matters
  for `beta_EL`, `beta_ER`, or `beta_LRd` specifically is not attempted
  here.

## Primary table: end-to-end, D=1, configuration x budget

| Config | E | L | R | B=250 | B=500 | B=1000 | B=2000 | All budgets |
|---:|:-:|:-:|:-:|---|---|---|---|---|
| 1 | 0 | 0 | 0 | 23/200 (11.5%) | 13/200 (6.5%) | 13/200 (6.5%) | 7/200 (3.5%) | 56/800 (7.00%) |
| 2 | 1 | 0 | 0 | 12/200 (6.0%) | 8/200 (4.0%) | 4/200 (2.0%) | 3/200 (1.5%) | 27/800 (3.375%) |
| 3 | 0 | 1 | 0 | 0/200 (0.0%) | 0/200 (0.0%) | 0/200 (0.0%) | 0/200 (0.0%) | 0/800 (0.0%) |
| 4 | 0 | 0 | 1 | 21/200 (10.5%) | 18/200 (9.0%) | 7/200 (3.5%) | 10/200 (5.0%) | 56/800 (7.00%) |
| 5 | 1 | 1 | 0 | 0/200 (0.0%) | 0/200 (0.0%) | 0/200 (0.0%) | 0/200 (0.0%) | 0/800 (0.0%) |
| 6 | 1 | 0 | 1 | 14/200 (7.0%) | 10/200 (5.0%) | 1/200 (0.5%) | 1/200 (0.5%) | 26/800 (3.25%) |
| 7 | 0 | 1 | 1 | 0/200 (0.0%) | 0/200 (0.0%) | 0/200 (0.0%) | 0/200 (0.0%) | 0/800 (0.0%) |
| 8 | 1 | 1 | 1 | 0/200 (0.0%) | 0/200 (0.0%) | 0/200 (0.0%) | 0/200 (0.0%) | 0/800 (0.0%) |

Full precision in `results/zero_variance_exclusions_d1_config_budget.csv`.
Figure `figures/fig7_zero_variance_exclusion_rates.pdf` renders this table as
an annotated heatmap.

## Marginal totals, D=1 end-to-end (`verification/_zero_variance_d1_marginals.json`)

| Factor | Level | Excluded | Total | Pct |
|---|---|---:|---:|---:|
| `E` | 0 | 112 | 3,200 | 3.500% |
| `E` | 1 | 53 | 3,200 | 1.656% |
| `L` | 0 | 165 | 3,200 | 5.156% |
| `L` | 1 | 0 | 3,200 | 0.000% |
| `R` | 0 | 83 | 3,200 | 2.594% |
| `R` | 1 | 82 | 3,200 | 2.563% |

`E=1` (restricted entanglement) roughly halves the exclusion rate within
`L=0` (3.5% vs 1.656% marginally; at matched budget the config-level table
shows configs 2/6 running at roughly half configs 1/4's rate). `R` has
essentially no effect on the exclusion rate (2.594% vs 2.563%, well within
what 3,200-cell binomial noise would produce). `L` is the only factor that
matters in an absolute (not just relative) sense.

## Secondary 1 -- end-to-end exclusion rates by configuration, block count, budget (all D)

Full table (320 rows: 8 configs x 5 depths x 4 budgets x 2 modes) in
`results/zero_variance_exclusions_all_cells.csv`. Depth marginal, end-to-end
mode only (all configs/budgets pooled per depth):

| Depth | Excluded | Total | Pct |
|---:|---:|---:|---:|
| 1 | 165 | 6,400 | 2.578% |
| 2 | 84 | 12,800 | 0.656% |
| 3 | 79 | 19,200 | 0.411% |
| 4 | 79 | 25,600 | 0.309% |
| 6 | 102 | 38,400 | 0.266% |

Exclusion rate falls monotonically with block count -- consistent with
Section 4.1's existing finding that block-count-1 replicate-count
calibration was the worst-converged stratum in the whole design. All of
these depth-marginal exclusions remain exclusively `L=0` (verified: 0
`L=1` exclusions at every depth individually, not just pooled -- see the
`depth x E x L` breakdown embedded in this script's run log).

## Secondary 2 -- conditional-mode exclusion rates, same breakdown (diagnostic only)

Same `results/zero_variance_exclusions_all_cells.csv` file
(`analysis_mode` column distinguishes the two). Conditional-mode total:
1,324 excluded of 102,400 (1.293%), noticeably higher than end-to-end's
509/102,400 (0.497%) -- consistent with conditional mode's generally
higher precision (lower forward-feature noise) producing tighter, more
frequently-degenerate replicate distributions at a fixed budget, though
this specific mechanism is not verified further here. The `L=0`-only
pattern is identical: 0 of 51,200 `L=1` conditional-mode cells flagged,
1,324 of 51,200 `L=0` cells flagged (2.586%).

## Secondary 3 -- direct end-to-end vs. conditional comparison at matched cells

`results/zero_variance_exclusions_by_mode.csv` (160 matched
configuration x depth x budget cells, both modes' total/excluded/pct plus
`pct_diff_endtoend_minus_conditional`). Conditional mode's rate exceeds
end-to-end's at most matched cells (median difference across all 160 cells
is negative, i.e. conditional rate is higher), most visibly at deeper block
counts and lower budgets (e.g. config 1, `D=2`, `B=250`: end-to-end 3.75%
vs. conditional 8.00%, a -4.25 point gap) -- opposite of the `D=1` region,
where the two modes are close and sometimes end-to-end is slightly higher
(e.g. config 1, `D=1`, `B=250`: end-to-end 11.5% vs. conditional 10.0%,
+1.5 points). No cell in either mode has any `L=1` exclusions.

## Secondary 4 -- exclusions from reasons other than exactly-zero variance

**None.** Every one of the 204,800 pointwise cells with a non-finite
`SNR_est` has `zero_variance_flag=True`
(`verification/_zero_variance_other_exclusion_reasons.csv`, 0 rows) --
confirms `build_h2h4_dataset`'s `np.isfinite(SNR_est)` filter and the
zero-variance flag are exactly coextensive in this dataset; there is no
second, undocumented exclusion mechanism to audit.

## Optional association diagnostic: attempted and abandoned per the prompt's own guidance

Fit `zero_variance_excluded ~ E * L * R + log2(B)` via `statsmodels.Logit`
on the 6,400 `D=1` end-to-end cells, as the prompt permits. **Result:
complete quasi-separation on `L`** -- statsmodels reports "Possibly complete
quasi-separation: A fraction 0.50 of observations can be perfectly
predicted" and the optimizer does not converge; `L`'s coefficient estimate
diverges to -22.9 with SE 8,683 (meaningless). This is the expected,
mechanical consequence of `L=1` having *zero* events in every stratum --
logistic regression cannot estimate a finite log-odds effect for a
predictor that perfectly separates the outcome. **Per the prompt's explicit
instruction ("If separation ... make this unreliable, do not force a model;
state that the descriptive table is the defensible result"), this model is
abandoned and the descriptive tables above are reported as the defensible
result.** The well-identified partial pattern within the non-separating
part of the model (fit with `L` dropped, `D=1` end-to-end only, for
descriptive interest only, not as a corroborated inferential result):
exclusion odds decrease with `E` (coefficient -0.796, `z=-4.64`) and with
`log2(B)` (coefficient -0.464, `z=-5.97`), both directionally consistent
with the marginal tables above; `R` is not distinguishable from zero
(`z=-0.08`) -- again consistent with the marginal table.

## Files produced

- `verification/run_zero_variance_audit.py`
- `results/zero_variance_exclusions_d1_config_budget.csv`
- `results/zero_variance_exclusions_all_cells.csv`
- `results/zero_variance_exclusions_by_mode.csv`
- `verification/_zero_variance_d1_marginals.json`
- `verification/_zero_variance_other_exclusion_reasons.csv` (0 rows, confirms no other exclusion reason)
- `paper/scripts/make_fig7_zero_variance_heatmap.py`, `paper/figures/fig7_zero_variance_exclusion_rates.pdf`
