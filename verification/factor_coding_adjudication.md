# Factor-coding adjudication

**Status:** frozen before any corrected coefficient, corrected covariance, corrected p-value, or corrected bootstrap value was calculated or inspected.

## Decision

Centered effect coding, `E_c = E - 1/2`, `L_c = L - 1/2`, and `R_c = R - 1/2`, is the corrected primary coding for H1--H4. This is an implementation correction under decision-rule branch 3: the accessible protocol evidence does not unambiguously specify direct `0/1` coding or define H1 as conditional on `R=0`, while the reviewed manuscript explicitly defines centered coding and an averaged lower-order factorial interpretation.

Historical direct-`0/1` results will be preserved as superseded audit outputs and interpreted as reference-level/simple-interaction quantities. They will not be relabeled as centered effects.

## Protocol and source evidence

### Published protocol article

The repository cites Brandon Shen and Karena Ling, “Gradient usability in few-qubit quantum neural networks: A signal-to-noise ratio framework for evaluating mitigation strategies,” *Journal of High School Science* 10(3), 2026, pp. 358--393, DOI `10.64336/001c.166201` (`paper/references.bib`, entry `shen2026gradient`). The article text, PDF, source manuscript, and attachments are not stored in this repository. On 2026-08-02, searches of the DOI, exact title, article identifier, journal site, and authors did not return retrievable article text. Consequently no claim about its factor coding can be made from inaccessible text.

The repository README at pre-result commit `cbbeafa853b0e87e153a783296fed1f9c750681a` describes the cited work as a “review paper” that “does not fully determine every implementation detail.” `ASSUMPTIONS.md` similarly records implementation choices where the paper was underdetermined. Neither accessible record quotes a protocol requirement for direct `0/1` regression coding, reference-level interactions, or conditioning H1 on `R=0`.

### Pre-result committed implementation

Commit `cbbeafa853b0e87e153a783296fed1f9c750681a` (“Replace pilot codebase with full QNN-SNR confirmatory pipeline,” 2026-07-26) predates production result generation. It contains:

- `CONFIGURATION_TABLE` with stored design indicators `(E,L,R)` in `{0,1}`;
- `H1_FORMULA = "a ~ E*L*R + depth_z + E:depth_z + L:depth_z + R:depth_z"`;
- `H2_H4_FORMULA = "y ~ E*L*R + depth_z + log2_budget + E:depth_z + L:depth_z + R:depth_z + L:R:depth_z"`;
- a code comment stating the predictors are numeric `0/1`; and
- documentation naming `E:L` as H1/H2 and `E:R` as H3.

This proves the historical implementation used direct `0/1` predictors. It does **not** state that the scientific target was deliberately an `E:L` simple interaction at `R=0`, does not discuss reference levels, and does not say lower-order terms should be conditional rather than averaged. The configuration table's storage coding is not by itself an unambiguous estimand specification.

Earlier commits (`45f8a524`, `7035e23e`, and `8945a757`) contain exploratory predecessor analyses and generated results, not a committed H1--H4 factorial analysis specification resolving this issue.

### Current manuscript

`paper/main.tex` states precisely that `E`, `L`, and `R` are effect coded as `{-1/2,+1/2}` and that effect coding makes lower-order coefficients average across the other factorial conditions. It defines H1 as the `E x L` coefficient `eta_EL`. Thus the manuscript's stated H1 is averaged across `R`, not conditional on `R=0`.

## Answers to the adjudication questions

- **Was coding specified by accessible protocol evidence?** No. The accessible records specify the factorial levels and model terms, but not regression contrasts or reference-level interpretation.
- **Were lower-order interactions intended to average across the third factor?** The current manuscript says yes. No pre-result protocol record was found that says otherwise.
- **Was H1 intended as R-averaged or conditional at R=0?** The current manuscript defines the averaged interpretation. Historical code accidentally produced the `R=0` simple interaction. No accessible protocol evidence intentionally selects that conditional estimand.
- **Was the protocol silent or ambiguous?** Coding is unresolved in the accessible protocol record. The direct implementation is clear; its intended scientific interpretation is not.

## Applied decision rule

Rule 3 applies: coding is unspecified in accessible protocol evidence. Centered coding is adopted as the corrected primary estimand because it matches the manuscript's stated factorial interpretation. This is labeled an implementation correction, not a favorable-result-driven sensitivity analysis.

If the protocol article or a genuinely pre-result specification is later produced and unambiguously mandates direct `0/1` coding and an `R=0` H1, this adjudication must be reopened before further primary reporting.

## Sources

- Repository citation: `paper/references.bib`, DOI `https://doi.org/10.64336/001c.166201`.
- Journal site queried: `https://jhss.scholasticahq.com/` and its article search.
- Pre-result implementation: commit `cbbeafa853b0e87e153a783296fed1f9c750681a`.
- Current manuscript: `paper/main.tex`, mixed-model Methods paragraph.
- Initial blocking audit: `verification/h1_finalization_blocking_report.md`.
