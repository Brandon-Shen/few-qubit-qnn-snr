# H2 robustness and replication: final results

**Status: complete.** Governing plan: `verification/h2_robustness_replication_plan.md`
(frozen at commit `7b57e3e`, before any result below was inspected).
Machine-readable summary: `results/h2_robustness/h2_final_summary_table.csv`
(21 rows). Full test suite: 210/210 passing (156 pre-existing + 54 new).

No original confirmatory data, config, or output was modified. Everything
in this package lives under `scripts/run_h2_*.py`,
`results/h2_robustness/`, `results/h2_replication_v1/`,
`configs/h2_replication_v1_stage1.yaml`, and the corresponding new test
files.

---

## 1. Reproduced original findings (Phase 2)

Independently reproduced bit-for-bit from frozen `results/production_confirmatory/`
inputs (`scripts/run_h2_zero_variance_audit.py`):

- End-to-end pointwise cells: 102,400. Zero-variance excluded: 509
  (0.497%), **100% confined to `L=0`**.
- Adopted `E:L` (H2): `0.024995843985971582` (Wald 95% CI `[0.010729,
  0.039262]`), Holm-adjusted `p=0.00238`, rejected.
- Existing nested bootstrap (`n=443`): median `0.023685`, 95% CI
  `[-0.018024, 0.065688]` — **includes zero**.
- Residual heteroscedasticity by depth (SD 0.659→0.276) and budget (SD
  0.301→0.513) reproduced exactly.
- **New in this pass**: all 509 zero-variance cells have `mu_hat` exactly
  `0.0`, not merely a tied nonzero value.

## 2. Mechanism: what drives the interaction? (Phase 3, diagnostic)

| model | response | `E:L` estimate | 95% CI |
|---|---|---:|---|
| numerator (gradient-mean magnitude) | `arcsinh(\|mu_hat\|)` | +0.004315 | [0.003076, 0.005554] |
| denominator (repeated-shot SD) | `log(shot_sd)` | -0.149866 | [-0.173538, -0.126194] |

Both components move in the direction that increases `SNR_est`, and
neither's 95% CI includes zero. **The interaction is not an artifact of
one component** — the gradient signal genuinely gets larger and the
finite-shot noise genuinely gets smaller under `E=L=1`, and these combine
multiplicatively in the ratio. Extended to all 50 leave-one-initialization-out
deletions (Phase 4E): **no sign reversal in either component** (numerator
always +0.0038 to +0.0049; denominator always -0.122 to -0.172) — this
mechanistic finding is solid.

## 3. Is the statistical significance robust? (Phase 4, robustness — NO, not to three independent checks)

| method | `E:L` 95% CI | excludes zero? |
|---|---|:-:|
| Prespecified Wald/Holm (mixed model) | [0.010729, 0.039262] | **Yes** (rejected) |
| Existing nested bootstrap (n=443) | [-0.018024, 0.065688] | No |
| Cluster-robust OLS (initialization-level, single fit, n=50 clusters) | [-0.021739, 0.068839] | No |
| Initialization-level resampling, new implementation (n=50, with explicit zero-variance logging) | [-0.003038, 0.066606] | No |

**Three methodologically distinct ways of relaxing the mixed model's
homoscedasticity/variance-structure assumptions — a nested bootstrap
(pre-existing), a single-fit cluster-robust reanalysis (new), and an
independently-implemented initialization-level resampling with explicit
diagnostic logging (new) — all produce a CI that includes zero.** Only
the prespecified Wald/Holm test itself rejects. This is reported as a
genuine, unresolved tension: the prespecified analysis plan's decision
stands (H2 is rejected under the confirmatory procedure), but that
decision is not independent of the specific variance assumptions of the
mixed model.

### 3.1 Depth-stratified: the effect's sign is not stable (exploratory)

| depth | `E:L` estimate | 95% CI | n_obs |
|---:|---:|---|---:|
| 1 | -0.090293 | [-0.182127, 0.001541] | 6,235 |
| 2 | **-0.111762** | **[-0.164917, -0.058608]** | 12,716 |
| 3 | +0.098048 | [0.061440, 0.134656] | 19,121 |
| 4 | +0.066700 | [0.040925, 0.092475] | 25,521 |
| 6 | +0.024632 | [0.009123, 0.040140] | 38,298 |

The effect is significantly *negative* at `D=2` and reverses to positive
only from `D=3` onward; the pooled positive estimate is a weighted
average dominated by the three deeper block counts (81% of eligible
rows). Budget-stratified diagnostics show no comparable instability
(both `B≤500` and `B>500` strata are positive and significant). This is
new information, not previously documented anywhere in the existing
verification record or the manuscript.

### 3.2 Zero-variance sensitivity (Phase 4F)

All 509 zero-variance cells have `mu_hat=0` exactly, so a variance floor
is mathematically irrelevant to `SNR_est` for those cells (0/anything=0);
all seven predefined nonzero floors (1e-12 to 1e-3) give the identical
result: `E:L=0.018170`, 95% CI `[0.003885, 0.032454]` (still excludes
zero). The only real choice is exclude (adopted, 0.024996) vs.
include-as-zero-response (0.018170) — a ~1-original-SE-unit shift, not a
reversal. The companion logistic model of `P(zero_variance_flag)` (F.2)
exhibits quasi-complete separation on `L` (expected, since `L=1` has zero
exclusions) and is reported as an inconclusive check, not misinterpreted
numerically.

## 4. Independent replication (Phase 5-7)

New seed namespace (`seed_root=3872531887`, verified non-overlapping),
Stage 1 design matching production exactly (`R_rep=30`, 8×5×4×50,
end-to-end mode). Executed in full: generation+fit+report in 19.4 minutes,
bootstrap (n=30) completed 30/30 for both H1 and H2-H4.

| | original | replication |
|---|---:|---:|
| `E:L` Wald estimate | 0.024996 | **0.049294** |
| Wald 95% CI | [0.010729, 0.039262] | [0.035236, 0.063352] |
| Bootstrap 95% CI | [-0.018024, 0.065688] (n=443) | [0.015691, 0.069828] (n=30) |
| Zero-variance excluded | 509/102,400 (0.497%) | 585/102,400 (0.571%) |
| Confined to `L=0`? | Yes | Yes (independently reconfirmed) |

**Interpretation (fixed decision rule, computed mechanically, `verification/h2_robustness_replication_plan.md`
Section 6): "direction replicated but magnitude uncertain."** The
replication independently reproduces a positive, significant `E:L`
effect and independently reconfirms the `L=0` zero-variance confinement
under entirely new randomness — both reassuring. But its point estimate
is roughly double the original's (3.34 original-SE units away), which
exceeds the frozen ≤2-SE-unit threshold for a clean match. This is
reported exactly as it came out — not rounded up to "confirmed," not
rounded down to "failed."

*Caveat on the replication's own bootstrap*: its CI excludes zero, but at
only `n=30` (vs. the original's `n=443`) this is a far less precise
estimate and is not treated as equally strong evidence as the original's
non-corroboration.

Stage 2 (`R_rep=300`) expansion rule was **not triggered**: the frozen
plan's only data-driven trigger (zero-variance rate diverging by >2x) was
not met (0.497% vs. 0.571%, a 1.15x ratio).

## 5. Interruptions (transparency note)

Background execution in this session was repeatedly interrupted by
something external (no Python-level error/traceback in any log; machine
clock evidence points to sleep/suspend cycles, later confirmed by the
user). Effect: zero data loss for (B) (checkpointed every 10 iterations)
and for the replication bootstrap's H1 portion (completed before the
first interruption); the replication bootstrap's H2-H4 portion had to
restart once because the generic CLI's checkpoint interval (50) never
triggered within a 30-iteration target — fixed by writing
`scripts/run_h2_replication_stage1_bootstrap.py` with
`checkpoint_every=3`. Recorded here per the task's own standard: record
failures and interruptions explicitly.

## 6. Final assessment

- **Reproduced original findings**: exact (Section 1).
- **Mechanism**: solid — both numerator and denominator contribute, no
  sign reversal under any single-initialization deletion (Section 2).
- **Statistical robustness of the prespecified rejection**: **not
  robust** to three independent methods that relax the mixed model's
  variance assumptions, and **not stable in sign** across block counts
  (Section 3). This is the most important limitation this package
  surfaces.
- **Independent replication**: direction and statistical significance
  replicate; magnitude does not (roughly 2x larger, 3.34 original-SE
  units) (Section 4). Not "confirmed."
- **Unresolved**: why the replication's magnitude is larger; why `D=2`
  specifically reverses sign; whether a hierarchical/hurdle model for the
  zero-inflated numerator would change the picture (not implemented —
  no vetted dependency for it in this stack, stated as a limitation,
  not forced).
- **Computational limits**: Stage 2 (`R_rep=300`) was designed but not
  executed (not triggered by the predefined rule, and not requested).
  This package's iteration counts (n=50 for initialization resampling,
  n=30 for both bootstraps) were revised down once from originally
  higher targets for measured feasibility reasons, documented
  transparently before any coefficient was inspected each time.
