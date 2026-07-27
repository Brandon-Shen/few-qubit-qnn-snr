# few-qubit-qnn-snr

Companion code for *Gradient Usability in Few-Qubit Quantum Neural Networks:
A Signal-to-Noise Ratio Framework for Evaluating Mitigation Strategies*
(Section 5.3): the four prespecified confirmatory hypothesis tests (H1-H4)
over the full 2x2x2 factorial design (restricted entanglement E, local cost
L, residual shortcut R) on a 4-qubit open-boundary transverse-field Ising
model.

**Read `ASSUMPTIONS.md` first.** The review paper does not fully determine
every implementation detail (how the residual architecture's classical
input enters the circuit, how depth maps onto hybrid blocks, the p-value
engine, etc.); every such choice is documented there with a rationale, is
exposed as a config field with a documented default, and is echoed into
every run's `run_manifest.json`. One item in particular (`A15b`, whether
blocks share a continued statevector or are self-contained circuits) is
flagged as worth double-checking against the paper's actual intent before
treating depth-dependent conclusions as final.

## Install

```
pip install -e ".[dev]"
```

Requires Python 3.11+. Uses PennyLane (`default.qubit`) for statevector
simulation, `statsmodels` `MixedLM` for the confirmatory mixed models, and
`pyarrow`/pandas for the tidy Parquet dataset.

## Pipeline

```
python -m qnn_snr validate    --config configs/confirmatory.yaml
python -m qnn_snr generate-exact --config configs/confirmatory.yaml
python -m qnn_snr generate-shots --config configs/confirmatory.yaml --mode finite_shot_end_to_end
python -m qnn_snr generate-shots --config configs/confirmatory.yaml --mode finite_shot_conditional
python -m qnn_snr validate    --config configs/confirmatory.yaml
python -m qnn_snr aggregate   --config configs/confirmatory.yaml
python -m qnn_snr fit         --config configs/confirmatory.yaml
python -m qnn_snr bootstrap   --config configs/confirmatory.yaml --iterations 2000
python -m qnn_snr report      --config configs/confirmatory.yaml
```

or, for any config, the whole pipeline in one call:

```
python -m qnn_snr run-all --config configs/smoke.yaml
```

Three configs are provided: `configs/smoke.yaml` (tiny, exercises every code
path, not statistically meaningful), `configs/dev.yaml` (full depth/budget
sweep, reduced replicate/init counts), `configs/confirmatory.yaml`
(publication scale -- update `design.replicates` / `design.n_initializations`
from the pilot utilities before a real run; see Section 17 / `qnn_snr/pilot.py`).

`generate-exact` and `generate-shots` skip regeneration if their output
already exists (pass `--overwrite` to force); `bootstrap` checkpoints to
`results/_checkpoints/` and resumes automatically. Every command prints an
estimated workload before running the expensive steps.

## Outputs (`results/`)

Tidy replicate-level data (`raw/*.parquet`, schema in `qnn_snr/schema.py`),
`data_validation_report.json`, `pointwise_gradient_statistics.parquet`,
per-model coefficient tables, `confirmatory_hypotheses.csv` (one row each
for H1-H4, Holm-adjusted), `bootstrap_coefficients.parquet` +
`bootstrap_diagnostics.json`, `configuration_summaries.csv`,
`interaction_indices.csv`, `resource_accounting.csv`,
`exploratory_results.csv`, `assumptions_snapshot.md`,
`statistical_methods.md`, `results_summary.md`, and `figures/` (12 PNGs).
See Section 18 of the task spec (or `qnn_snr/report.py`) for what each file
contains.

## Package layout

```
qnn_snr/
  config.py       YAML config schema, defaults, hashing, CNOT schedules
  hamiltonian.py  TFIM construction, exact diagonalization, validation
  costs.py        global (infidelity) / local (normalized energy) costs
  circuits.py     Ry+CNOT block propagation, entanglement diagnostics
  residual.py     classical W/b/gamma residual layer
  gradients.py    hybrid chain-rule total-gradient assembly (exact + finite-shot)
  budget.py       deterministic shot-budget allocator, resource accounting
  replicate.py    replicate generation orchestration (matched across all 8 configs)
  schema.py       tidy dataset schema, Parquet I/O
  validate.py     pre-analysis validation checks
  pilot.py        replicate-count / initialization-count pilot utilities
  manifest.py     run manifest (config, versions, seeds, git commit, formulas)
  report.py       publication tables + results_summary.md generation
  figures.py      the 12 required figures
  cli.py          command-line entry points
  stats/
    pointwise.py    per-cell SNR/bias/sign-agreement statistics (Section 9)
    models.py       H1 exact-signal and H2-H4 estimator-SNR mixed models
    holm.py         Wald tests + Holm-Bonferroni adjustment
    bootstrap.py    nested matched bootstrap (Section 14)
    interactions.py normalized interaction indices I_AB, J_AB (Section 15)
    descriptive.py  physics summaries (energy/fidelity/entanglement), resource accounting
    exploratory.py  Section 16 exploratory comparisons
tests/            unit + synthetic-data-recovery + CLI integration tests
```

## Tests

```
pytest tests/ -q
```
