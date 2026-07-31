# Three-way interaction coefficient (`beta_ELR`), end-to-end-only

**Status: exploratory only, as always.** `E:L:R` is a byproduct coefficient
of the same `H2_H4_FORMULA` fit that produces `beta_EL`/`beta_ER`/`beta_LRd`
(the formula's `E*L*R` term expands to include it), but it has never been
part of the Holm-corrected H1–H4 confirmatory family —
`qnn_snr/report.py` states this explicitly ("The E:L:R three-way
interaction... is exploratory only"). Nothing below changes that framing or
implies a confirmatory rejection.

## Task: pure extraction, no new fit needed

`results/snr_model_coefficients.csv` was already regenerated end-to-end-only
in the course of adopting the new confirmatory numbers
(`verification/confirmatory_numbers_adopted.md`, via a real rerun of the
guarded `cmd_fit` path). `E:L:R` was sitting in that file already — the
reporting pipeline (`qnn_snr/stats/holm.py::build_confirmatory_table`) only
*selects* four coefficients out of the fitted model's full parameter vector
for the Holm family; it never drops `E:L:R` from the underlying
`snr_model_coefficients.csv` dump, which records every fitted coefficient.
No refit was run for this task — the number below is a direct extraction:

```
E:L:R,-0.021315055158096483,0.010287355020239497
```

## Result

| | Estimate | SE | Wald z | p (unadjusted, 2-sided) | 95% CI |
|---|---:|---:|---:|---:|---|
| **`beta_ELR` (end-to-end-only, adopted confirmatory dataset)** | **-0.021315** | **0.010287** | **-2.072** | **0.0383** | **[-0.04148, -0.00115]** |
| `beta_ELR` (old pooled, superseded) | -0.011128 | 0.007988 | -1.393 | 0.1636 | [-0.02679, 0.00453] |

## Comparison against the old pooled estimate

- **Sign**: unchanged — negative in both.
- **CI overlap**: the two CIs do overlap ([-0.0268, -0.0012] is the
  intersection of [-0.0268, 0.0045] and [-0.0415, -0.0012]), but only in a
  narrow band near the pooled estimate's lower tail — this is a much thinner
  overlap than was seen for `beta_ER`/`beta_EL` in
  `verification/conditional_vs_endtoend_comparison.md`, where the two
  single-mode CIs sat almost on top of each other.
- **Magnitude**: the end-to-end-only estimate is **nearly double** the
  pooled magnitude (-0.0213 vs -0.0111, ~1.9x). This is the same qualitative
  pattern already seen for `beta_LRd` (which also grew substantially in
  magnitude relative to its pooled value once conditional-mode rows were
  removed) — **not** the same pattern as `beta_EL`/`beta_ER`, which stayed
  close to their pooled values. Read together with
  `verification/conditional_vs_endtoend_comparison.md`'s finding that
  `beta_LRd` flips sign between conditional-only and end-to-end-only fits,
  this is consistent with mode-pooling systematically attenuating
  depth/three-way-interaction-flavored coefficients specifically (those
  involving `depth_z` or the full `E:L:R` combination) more than it
  attenuates the simpler two-way `E:L`/`E:R` terms — plausible given the
  paper's own framing that end-to-end mode carries extra
  forward-feature-re-estimation noise that compounds with depth, but this is
  an observation about two data points (`beta_LRd`, `beta_ELR`), not an
  independently established general rule.
- **Statistical threshold, reported without over-reading it**: the
  end-to-end-only unadjusted p-value (0.038) crosses the nominal α=0.05
  line, unlike the pooled estimate's p=0.164. **This changes nothing about
  the Holm-corrected confirmatory conclusions** — `E:L:R` was never
  submitted to Holm correction and is not going to be submitted now; it
  remains reported purely as an exploratory descriptive quantity, exactly as
  `qnn_snr/report.py` has always treated it. The crossing is noted here
  because ignoring it would look like cherry-picking the parts of the
  mode-sensitivity story that are convenient; it is reported for
  completeness, not elevated into a new finding.

## Reproduction

```python
import pandas as pd
coefs = pd.read_csv("results/snr_model_coefficients.csv")
coefs[coefs["coefficient"] == "E:L:R"]
```
