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
every run's `run_manifest.json`.

**Block semantics are resolved, not open.** An earlier draft of this
README flagged whether blocks share a continued statevector or are
self-contained circuits (`ASSUMPTIONS.md` item `A15b`) as needing
double-checking before trusting depth-dependent conclusions. That question
has since been settled: the implementation uses self-contained blocks
connected only by classical features, confirmed against black-box finite
differences (a continued-state alternative tested during development did
not agree with them). See `paper/main.tex` Appendix A.2
("Block-semantics resolution") for the full argument, and
`verification/depth_semantics_resolution.md` for the underlying
verification record (which also flags one remaining wording tension in the
companion review's prose about the E=1 restricted schedule -- an
underspecification in that source paper, not an open implementation
question here).

## Install

```
pip install -e ".[dev]"
```

Requires Python 3.11+. Uses PennyLane (`default.qubit`) for statevector
simulation, `statsmodels` `MixedLM` for the confirmatory mixed models, and
`pyarrow`/pandas for the tidy Parquet dataset.

**For an exact reproduction of the manuscript's environment**, use the
pinned lockfile instead of the loose ranges above:

```
python -m venv .venv
.venv\Scripts\activate        # or `source .venv/bin/activate` on Linux/macOS
pip install -r requirements-lock.txt
pip install -e . --no-deps
```

`requirements-lock.txt` pins the exact versions recorded in
`results/production_confirmatory/run_manifest.json` and the paper's
Software Availability statement (Python 3.12.10; pennylane 0.45.1; numpy
2.5.1; pandas 3.0.3; scipy 1.18.0; statsmodels 0.14.6; pyarrow 25.0.0;
matplotlib 3.11.0; PyYAML 6.0.3). This exact combination has been verified
in a clean venv to install without conflicts and pass the full test suite
(`pytest tests/ -q`, 233/233). `pyproject.toml`'s ranges are looser and will
resolve to whatever the newest compatible releases are on install day,
which may drift by a patch version or two.

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
`results/_checkpoints/` (gitignored scratch space, not archived output) and
resumes automatically. Every command prints an estimated workload before
running the expensive steps.

**Running the full confirmatory-scale pipeline is a large job**: 8
configurations x 50 initializations x 30 replicates x 5 depths x 4 budgets
x 3 gradient modes, plus a 2000-iteration nested bootstrap. Budget
substantial wall-clock time and memory headroom; the pipeline checkpoints
so an interrupted `bootstrap` step resumes rather than restarts. A fresh
`run-all`/step-by-step invocation writes flatly to `<output.results_dir>`
(default `results/`) -- that is a *new* run's raw working output, separate
from the archived, categorized production data described next.

## Outputs and reproducing the manuscript's data

The data behind every reported number, table, and figure is archived under
`results/`, split into five clearly labeled directories -- see
**[`results/README.md`](results/README.md)** for the full breakdown
(`production_confirmatory/`, `production_corrected_end_to_end/`,
`superseded_pooled/`, `sensitivity_analyses/`, `smoke_test/`), SHA-256
checksums for every file, the exact frozen production config, and the
**exact command to regenerate every main figure and table** from that
archived data (no multi-hour rerun required for that -- see below for
regenerating the raw data itself).

The manuscript commit these files correspond to is recorded in
[`MANUSCRIPT_COMMIT.txt`](MANUSCRIPT_COMMIT.txt) at the repository root.

For what each output file *means* statistically, see `qnn_snr/report.py`
and `results/production_confirmatory/statistical_methods.md`.

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
  figures.py      the report figures (11 PNGs, see results/README.md)
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

233 tests as of this checkout; see `verification/` for the additional
audit-trail scripts and records (bootstrap sensitivity, mode-pooling
correction, sensitivity analyses, regression tests) that back the paper's
Appendix A and reproducibility index.

## Paper

`paper/main.tex` is the manuscript (`paper/scripts/` regenerates every
figure from the archived data in `results/`, and
`paper/scripts/structural_check.py` is a LaTeX-structure sanity check --
label/ref/includegraphics/environment consistency -- used in place of a
full `pdflatex` compile, since no LaTeX toolchain is available in this
checkout). `paper/references.bib` is the bibliography.

## Data and Code availability

This repository *is* the data/code deposit named in the manuscript's
Data/Code availability statements:

- **Data**: `results/README.md` (five labeled directories, SHA-256 hashes,
  the exact frozen production config, and per-figure/table reproduction
  commands).
- **Code**: `qnn_snr/` (pipeline), `paper/scripts/` (figure generation),
  `verification/` (audit trail and regression scripts), `tests/`
  (233-test regression suite).
- **Exact snapshot**: [`MANUSCRIPT_COMMIT.txt`](MANUSCRIPT_COMMIT.txt)
  records the commit these numbers were finalized against; check that
  commit out for a byte-for-byte match to what the manuscript cites.
