# Reproducibility report

The bounded scientific checks, archived numerical calculations, selected tests and six figures are reproducible in the inspected local environment. Full independent reproduction of experimental generation, model fitting, bootstrap fitting, a clean environment and the revised manuscript build is not established. The open High bootstrap finding prevents unconditional acceptance of finite-shot inferential robustness.

## Repository and environment

Inspected HEAD/main is `ca058a70f49aa5c3300b2ea66e39421e0b0fed15`; local `sndc-submission-v1` resolves to it. Root revised inputs are untracked, differ from the tracked/released paper sources and retain the hashes in `SCIENTIFIC_CODE_AUDIT.md`. Existing user edits to plotting scripts/figures/results were preserved. Source/input hashes and ancestry scopes are in `inventory.json`, stage2–6 evidence and `stage7a_release_identity.json`.

Tracked `paper/sn-article.tex` and `submission_package/main.tex` are byte-identical; the corresponding supplement pair also matches, and both match release-tag contents. This does not establish that the distinct revised root documents are synchronized with the released submission. The two IDs in `MANUSCRIPT_COMMIT.txt` have different provenance roles; checked scientific/manuscript paths match across those related commits. No discrepancy was inferred solely from unequal IDs.

Current Python3.12.10 and Windows-11-10.0.26200-SP0 match recorded production information. Ten installed direct/dev versions match explicit pins:

| Package | Version |
|---|---|
| PennyLane |0.45.1|
| NumPy |2.5.1|
| pandas |3.0.3|
| SciPy |1.18.0|
| statsmodels |0.14.6|
| PyArrow |25.0.0|
| Matplotlib |3.11.0|
| PyYAML |6.0.3|
| pytest |9.1.1|
| pytest-cov |7.1.0|

Five freeze environment fields and eight production dependency entries agree. `stage7a_environment.json` snapshots69 current distributions; it is not a recovered full original transitive lock. No installation, dependency resolution, clean build, Linux execution or external CI was performed. Production source propagation uses NumPy linear algebra with PennyLane reference support; backend metadata alone does not establish hardware execution. Revised main560 still contains a software TODO (IA-009).

## Frozen integrity and numerical reproduction

All19 manifest component references, six self-checksums and primary input identities matched. The347-row frozen CSV/JSON tables agree; sources exist and do not substitute superseded paths. However, five entries in the separate component-reference list conflict with embedded hashes (IA-003), and bootstrap endpoint-source metadata is incomplete (IA-004). Freeze identity/tag roles are documented in [stage 4](STAGE_4_FROZEN_PRIMARY_RECONCILIATION.md).

| Component | Evidence class | Practical limit |
|---|---|---|
| Independent gates/TFIM/objectives and bounded hybrid finite differences |Verified independently|Bounded deterministic coverage, not every frozen case.|
| Estimator modes, metrics and shot budgets |Verified independently|Small executed vectors/cells plus complete design-table accounting; not full raw regeneration.|
| Primary coding transforms and Wald/Holm arithmetic |Verified independently|Archived coefficients/SEs are inputs; originating fits not refit.|
| Archived bootstrap transformations/percentiles and draw identities |Verified independently|No fresh model/bootstrap fits; does not settle sampling-unit validity.|
| J/I points, weighting contrasts and stored secondary aggregations |Verified independently|Some covariance/fit origins remain archived-only.|
| Model formulas/random-effect construction |Consistent by static inspection|No independent covariance-model adequacy demonstration.|
| Fit convergence, optimizer/LOO fits and some projected uncertainty |Verified by archived evidence only|No independently regenerated fit traces/covariance.|
| Selected repository tests and isolated figures |Reproduced using repository scripts|Selection and input/output isolation limits below.|
| Direct PDF rasterization |Blocked|Installed MiKTeX setup incomplete.|

Other explicit scope gaps are recorded as Not executed/Not verified, rather than misclassified as missing-resource blockers or failed scientific tests. Matrix candidate-line/comparison classifications also retain different-estimand/editorial/partial-verification labels where a single evidence class would be misleading.

## Executed repository tests

Stage7A inspected and ran `test_config.py`, `test_holm.py`, `test_validate.py`, `test_factor_coding.py`, `test_resource_accounting_submission.py`, and `test_line_endings_and_checksums.py::test_protected_text_artifacts_use_lf` under `tests/`. Result: **34 passed, 0 failed/errors/skipped**, confirmed in completed JUnit and stdout. Pytest time9.57seconds. These synthetic/read-only tests do not constitute34 independent scientific conclusions or the full principal-analysis test suite.

The exact command, test-source hashes and environment overrides are in `stage7a_tests.json`; stdout/JUnit are `stage7a_pytest.log/xml`. Python bytecode, pytest cache and third-party plugin autoload were disabled; temporary/JUnit/log/Matplotlib config paths were restricted to fresh audit locations. No model fitter or result generator was invoked. The checksum-inventory writer test and broader fit/generator paths were deliberately omitted.

Independent audit scripts and commands are indexed in each stage report. Stage3's incomplete initial JSON is superseded for interpretation by retry1; stage5's original Patsy namespace error is corrected in retry1. Stage6C's literal-format false alarm is corrected in reviewed/follow-up evidence; stage6D FINAL tables supersede intermediate mappings. Prior files remain preserved. These audit-tool problems are not additional scientific failures.

## Figures

Nine revised-document placements use six unique PDFs. All six paper/upload PDF pairs are byte-identical. Five renderer invocations in an isolated copied source/input tree produced all six figures:

| PDF | Source renderer | Comparison |
|---|---|---|
|fig0_el_primary.pdf|paper/scripts/make_fig0_el_primary.py|Exact bytes|
|fig1_confirmatory_forest.pdf|paper/scripts/make_fig1_forest.py|Identical after date metadata removal|
|fig12_j_conditional.pdf|paper/scripts/make_fig12_j_conditional.py|Exact bytes|
|fig13_h1_depth.pdf|scripts/run_h1_depth_weighting.py, figures() only|Identical after date metadata removal|
|fig14_h1_weighting.pdf|same figures() function|Identical after date metadata removal|
|fig16_architecture.pdf|paper/scripts/make_fig16_architecture.py|Exact bytes|

Only CreationDate/ModDate entries were removed for comparison; no numerical/content normalization was applied. Six preview PNGs are pixel-identical and were individually visually inspected. Twelve conditional-J artist coordinates independently match frozen point/endpoint values. The architecture is static; fig0 reaggregates frozen inputs, and depth/weighting consume archived plot sources without invoking refitting main. Renderer executions totaled about18seconds. Protected original hashes stayed unchanged.

One caption style claim fails (IA-010). Successful figure reproduction also inherits underlying uncertainty caveats, including IA-005 for affected finite-shot intervals.

Installed `pdftoppm` failed on the first attempted PDF, producing no image and reporting unfinished fresh MiKTeX setup. Further attempts stopped. No direct PDF screenshot was inspected; visual assessment used the pixel-matched renderer PNGs and PDF payload identity. Full LaTeX compilation, bare-filename figure search paths for root revised sources, flat-upload packaging and external journal rendering remain unverified. See [stage 7B](STAGE_7B_FIGURES.md) and its saved stderr, hashes, logs and artist traces.

## Assessment and remaining actions

Reproduction is strong for the bounded deterministic paths and source-to-output arithmetic, and successful for current renderers in this matching local environment. It is incomplete for the original environment closure, full raw-generation/fitting pipeline, independent pilot provenance, some inference origins and final revised release/build. Reproducing existing numerical endpoints does not establish statistical validity under lost vector dependence.

Before submission, address IA-005, explain seed reuse/pilot lineage, reconcile metadata and pooled reporting, correct documentation claims, then synchronize and validate the intended revised submission. A separately authorized sensitivity/refit/build scope may be needed; this audit neither changes frozen results nor chooses methods by favorable significance. Priorities and specific limits are in [SUBMISSION_READINESS.md](SUBMISSION_READINESS.md).
