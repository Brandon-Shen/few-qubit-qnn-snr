# `fig0_el_primary.pdf` regeneration: reproducible, data-derived replacement

## Why the prior PDF was treated as untrusted

`paper/main.tex` referenced `figures/fig0_el_primary.pdf` (label
`fig:el-primary`) with a caption quoting $J_{EL}=1.242$ and $I_{EL}=1.034$,
but the file **did not exist anywhere in the repository** --
`paper/scripts/structural_check.py` reported it as a `MISSING GRAPHIC` both
during Task 5's integration pass and again at the start of this task.
Searched exhaustively before writing anything:

- `paper/scripts/` and `verification/`: no `make_fig0_el_primary.py` or
  similarly-named generation script existed.
- Git history: `git log --all --diff-filter=D --name-only` shows no commit
  ever added or deleted a file matching `fig0`/`el_primary`/`el_interaction`.
  No other branches exist (`git branch -a`: `main` only).
- No copy of the PDF was found under any name, anywhere in the working tree.

**Conclusion: no original generation script or trusted PDF was ever
recovered.** The caption's numbers were real (they match a genuine
derivation documented in prose, see below) but there was no reproducible
artifact behind the referenced file, and no numeric value from the old
(nonexistent) PDF was used as an input anywhere in this task.

## Numerical source, traced before any script was written

`qnn_snr/stats/interactions.py::compute_interaction_indices(pointwise_df,
exact_df)` is the validated, tested (`tests/test_interactions.py`)
production function computing `I_AB`/`J_AB` for all three pairs (E_L, E_R,
L_R), using the exact configuration mapping (`PAIR_SPECS`:
`("E_L", 1, 2, 3, 5)`) and formula (`combined * baseline / (single_A *
single_B)`, RMS aggregates) specified for this task.

`results/interaction_indices.csv` exists but is **pooled** (both estimator
modes) and was **not used** as a source for `I_EL`.
`verification/mode_split_descriptive_stats.md` documents the actual
end-to-end-only derivation the manuscript caption's numbers come from
(`I_AB(E_L)` end-to-end-only $=1.034074$; `J_AB` mode-invariant
$=1.241760$) but never persisted it as a machine-readable table -- prose
only. This gap is what `paper/figure_data/fig0_el_primary_source.csv`
(new) now closes.

## Inputs

| File | Filter | SHA-256 |
|---|---|---|
| `results/pointwise_gradient_statistics.parquet` | `analysis_mode == "finite_shot_end_to_end"` | `99a4decf8597c9fcc5a61a8e59075d34e1cf6668714ee19e38b39258e15d1342` (whole file, unchanged by this task) |
| `results/raw/exact.parquet` | `analysis_mode == "statevector_exact"` | `77e54bed863de79be0d1ebb4937f015fe29a1b1cb5d58e0f216f3acd4b9bb542` (whole file, unchanged by this task) |

Per-run hashes of the two files are also recorded directly inside
`paper/figure_data/fig0_el_primary_source.csv`'s `source_file_sha256`
column, computed fresh on every script run rather than pasted once.

## Verified structural properties of the inputs (not assumed)

- `results/raw/exact.parquet`: `budget` is uniformly `0` for
  `statevector_exact` rows (no real budget dependence), and there is
  **exactly one row per `(configuration_id, depth, parameter_id,
  initialization_id)` cell** (min and max group size both 1, checked
  directly) -- confirms no risk of exact rows being duplicated across
  budgets or estimator modes, and no deduplication step was needed.
- Raw row counts for configurations 1 (baseline), 2 (E-only), 3 (L-only),
  and 5 (E+L) are identical across both the end-to-end pointwise data
  (12,800 each) and the exact data (3,200 each) -- the matched-point
  structure guaranteed by the shared factorial design, verified rather
  than assumed.
- Finite `SNR_est` counts differ across these four configurations (1:
  12,571; 2: 12,723; 3: 12,800; 5: 12,800) **exactly as expected** from the
  already-documented, exactly-`L=0`-confined zero-variance exclusion
  pattern (`verification/zero_variance_exclusion_audit.md`): configs 1 and
  2 have `L=0` and show exclusions, configs 3 and 5 have `L=1` and show
  none. This is not an "unexpected" matched-point discrepancy and does not
  trigger a stop condition.

## Filters applied

- `I_EL`: `pw_all[pw_all["analysis_mode"] == "finite_shot_end_to_end"]`
  only -- conditional-mode rows are never read into this computation
  (verified both by direct filter logic and by
  `tests/test_fig0_el_primary.py::test_filter_pointwise_end_to_end_excludes_conditional_rows`).
- `J_EL`: `exact_all[exact_all["analysis_mode"] == "statevector_exact"]`
  only.

## Formulas and component RMS aggregates (full precision)

```
I_EL = (M_EL * M_0) / (M_E * M_L),   M = RMS(SNR_est)
J_EL = (G_EL * G_0) / (G_E * G_L),   G = RMS(abs(exact_gradient))
```

| | baseline (config 1) | E-only (config 2) | L-only (config 3) | E+L (config 5) |
|---|---:|---:|---:|---:|
| `M` (RMS `SNR_est`, end-to-end) | 1.3036802298943113 | 1.2524286845690007 | 1.950204926802554 | 1.9373763315763406 |
| `G` (RMS `abs(exact_gradient)`) | 0.05449746205328429 | 0.04456191131530095 | 0.06717810025113201 | 0.06821078510117906 |

## Cross-check: two independent computations, required to agree

1. The validated production function,
   `qnn_snr.stats.interactions.compute_interaction_indices(pw, exact_df)`.
2. An independent, from-scratch numpy recomputation written directly in
   `paper/scripts/make_fig0_el_primary.py`
   (`compute_indices_manual`) that does **not** call (1).

Both were run against the real, frozen data. They agree to
`atol=1e-9` (the script aborts otherwise): confirmed at runtime,
printed as `CONFIRMED: production function and independent recomputation
agree to atol=1e-09 for both I_EL and J_EL.`

## Results

- **Full precision**: $I_{EL} = 1.0340744657849426$,
  $J_{EL} = 1.2417603765323095$.
- **Rounded (regression targets, matched, not used as inputs)**:
  $I_{EL} \to 1.034$, $J_{EL} \to 1.242$ -- both match the values already
  quoted in the manuscript caption and in
  `verification/mode_split_descriptive_stats.md`, now backed by a real,
  reproducible, machine-readable artifact for the first time.

## Script and outputs

- **Script**: `paper/scripts/make_fig0_el_primary.py`. Deterministic given
  the frozen input files; fails loudly (raises, does not warn-and-continue)
  on: missing required `analysis_mode`, pooled-mode leakage, duplicated
  exact rows, more than one distinct exact-data budget value, mismatched
  raw row counts across the four configurations, a zero denominator in
  either index, disagreement between the two independent computations
  beyond tolerance, or a computed value that does not round to the
  expected validation target.
- **Figure-source CSV**: `paper/figure_data/fig0_el_primary_source.csv`
  (new path -- no `paper/figure_data/` directory existed before this task;
  documented here as the chosen location). Latest run SHA-256:
  `86a1fe7822df68bfdf28e66c8e210d1ff4705d97509beba174e4a4999f8ad38b`.
- **Figure**: `paper/figures/fig0_el_primary.pdf`. Latest run SHA-256:
  `c5ad0f29ae451eeffe00da8164499fffcd71c10678e7a21b84f2ff036244f6b1`. (Both
  hashes change slightly between runs because the CSV embeds a fresh
  `generated_at` timestamp each time; the underlying `I_EL`/`J_EL` values
  and all component aggregates are bit-for-bit stable across reruns,
  confirmed directly.)
- **Backup handling**: no pre-existing PDF was found on the first real run
  of this pipeline in this session, so `paper/figures/fig0_el_primary.placeholder_backup.pdf`
  was **not created** -- there was nothing genuine to back up (the file
  never existed). The script's backup logic was written, tested, and
  fixed to only treat a PDF as an untrusted placeholder if it exists
  *before* this script's own figure-source CSV does; a bug where re-running
  the script mislabeled its own prior validated output as an "untrusted
  placeholder" was caught during this task and corrected before finalizing
  (`paper/scripts/make_fig0_el_primary.py`'s `main()`, the `PDF_OUT.exists()
  and not CSV_OUT.exists()` guard).

## Manuscript caption

Reviewed the existing caption in `paper/main.tex` (H2 subsection, Figure
after item A.18's paragraph): it states $J_{EL}=1.242$ (24.2% shift, RMS
exact-gradient magnitude) and $I_{EL}=1.034$ (3.4% shift, RMS end-to-end
estimator SNR), notes the vertical reference at one as multiplicative
independence, and states the indices "complement, rather than replace,"
H1 and H2. **All of this is numerically and conceptually accurate against
the regenerated data** -- no caption edit was needed or made. H1 and H2's
confirmatory decisions were not touched.

## Tests

16 new tests in `tests/test_fig0_el_primary.py`, covering all 13 required
items (several are covered by more than one test): the script never reads
its own PDF as input; `I_EL` uses only `finite_shot_end_to_end`;
conditional-mode rows cannot enter it; exact rows are not duplicated across
budgets; the configuration mapping is exactly `(1, 2, 3, 5)`; RMS is
`sqrt(mean(x**2))`; the formula is `combined * baseline / (single_E *
single_L)`; matched-point identity is enforced; zero denominators raise;
recomputed values agree with the production function (both on synthetic
data and on the real frozen dataset); the generated values round to 1.242
and 1.034; the PDF and source CSV are created by an actual subprocess run;
and the manuscript-referenced figure path exists on disk. **16/16 pass.**
Full suite: **156/156 pass** (140 pre-existing, including the QMI/QIP
robustness package's 8 tests, plus 16 new for this task), confirmed by a
direct `pytest tests/ -q` run, not assumed from addition.

## Static checks

- `paper/scripts/structural_check.py`: **OK, zero problems** (26
  environments balanced, 23 unique labels, 50 refs resolve, **all 11**
  `\includegraphics` calls resolve -- `fig0_el_primary.pdf` no longer
  reported missing).
- `verification/task5_static_checks.py`: **OK**, unchanged from Task 5
  (no stale placeholders, no invented DOI/URL, no equivalence overclaim,
  historical chronology intact).

## Git status and simulation confirmation

No raw quantum simulation file (`results/raw/*.parquet`) was read for
writing, modified, or regenerated by this task -- only read for the
already-frozen `exact.parquet` and the already-computed
`pointwise_gradient_statistics.parquet`. Files added/changed by this task:
`paper/scripts/make_fig0_el_primary.py` (new),
`paper/figure_data/fig0_el_primary_source.csv` (new),
`paper/figures/fig0_el_primary.pdf` (new -- previously absent),
`paper/figures/fig0_el_primary_preview.png` (new),
`tests/test_fig0_el_primary.py` (new), this file (new). `paper/main.tex`
was **not** modified (caption already accurate).

## Task 5 verification record: status update

`verification/task5_manuscript_integration.md` and
`verification/task5_stale_reference_audit.md` both previously reported
`fig0_el_primary.pdf` as "found outside Task 5's scope, flagged rather than
fixed" / "blocks an actual compile." Both documents are updated (see their
"Status update" additions) to record: **resolved -- `fig0_el_primary.pdf`
has been reconstructed reproducibly from frozen machine-readable data (this
document), and `paper/scripts/structural_check.py` no longer reports it as
a missing graphic.** This update was made only after all of the above
checks passed.
