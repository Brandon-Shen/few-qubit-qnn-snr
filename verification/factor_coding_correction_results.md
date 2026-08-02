# Factor-coding correction results

**Status:** correction frozen. Later post-primary analyses have not yet been run.

## 1. Protocol specification

The cited protocol article is identifiable by DOI `10.64336/001c.166201`, but neither its full text nor source is present in the repository and it was not retrievable from the journal on 2026-08-02. No accessible pre-result analysis specification states that H1 is intentionally conditional on `R=0`. Pre-result commit `cbbeafa8` proves the implementation used direct `0/1` columns, but provides no reference-level scientific interpretation. The current manuscript explicitly specifies `{-1/2,+1/2}` effect coding and says lower-order terms average across the third factor. Under the committed decision rule, the accessible protocol record is therefore coding-unspecified.

Full evidence and adjudication: `verification/factor_coding_adjudication.md`, commit `79b6b87bbde5228e1450fafcd6a8df132b56cf4d`.

## 2. Primary coding

The corrected primary analysis uses explicit `E_c=E-0.5`, `L_c=L-0.5`, and `R_c=R-0.5`. This is an implementation correction matching the manuscript's factorial interpretation. Historical direct-`0/1` pairwise coefficients are preserved as superseded reference-level/simple-interaction results under `results/superseded/direct_01_factor_coding/`.

## 3. Exact reparameterization audit

The centered and direct models span the same fixed-effect column spaces.

| Audit | H1 | H2--H4 |
|---|---:|---:|
| Rows | 25,600 | 101,891 |
| Columns/rank, each coding | 12/12 | 14/14 |
| Maximum column-space projection error | 4.97e-14 | 1.53e-13 |
| Maximum transformed-versus-refit coefficient difference | 4.09e-16 | 3.73e-14 |
| Maximum fitted-value difference | 2.72e-15 | 1.54e-11 |
| Log-likelihood difference | -1.46e-11 | 0 |

Residuals, residual scale, random-effect variances, and fixed-effect covariance transformations also agree within the frozen tolerances. H4 is invariant in this model: `L_c:R_c:depth_z = L:R:depth_z`; this was verified from the actual design matrices and centered refit rather than assumed.

The required identities hold:

- `EL_c = EL_01 + 0.5 ELR_01`;
- `ER_c = ER_01 + 0.5 ELR_01`;
- `EL(R=0)=EL_01`, `EL(R=1)=EL_01+ELR_01`, and their equal average is `EL_c`;
- corresponding ER identities hold across L.

## 4. Corrected primary H1--H4 family

Model-based intervals are two-sided 95% Wald intervals. Holm adjustment was recomputed across the four corrected raw p-values.

| Hypothesis | Corrected coefficient | Estimate | SE | 95% CI | Raw p | Holm p | Decision |
|---|---|---:|---:|---:|---:|---:|---|
| H1 | `E_c:L_c` | 0.00404280 | 0.00108127 | [0.00192355, 0.00616204] | 0.00018479 | 0.00073917 | Reject |
| H2 | `E_c:L_c` | 0.01433832 | 0.00514484 | [0.00425461, 0.02442202] | 0.00532100 | 0.01596300 | Reject |
| H3 | `E_c:R_c` | -0.01161511 | 0.00514368 | [-0.02169653, -0.00153368] | 0.02393739 | 0.04787478 | **Reject** |
| H4 | `L_c:R_c:depth_z` | -0.01017876 | 0.00536207 | [-0.02068823, 0.00033072] | 0.05765827 | 0.05765827 | Do not reject |

H1 and H2 remain rejected; H4 remains not rejected. **H3 changes from historical non-rejection to corrected rejection.** This unfavorable-to-current-manuscript change is reported without qualification or post hoc model modification. The centered H3 is an E-by-R interaction averaged across L; it does not contradict the historical near-zero `E:R` simple interaction at `L=0` because those are different estimands.

## 5. Corrected bootstrap intervals

- H1: 2,000 attempted and 2,000 completed initialization-cluster bootstrap fits, zero failures; percentile 95% interval **[0.00047341, 0.00753493]**, median 0.00406670. The original 400 draws are preserved exactly and transformed draw by draw; their centered interval is [0.00118990, 0.00765479]. Endpoint checkpoints are archived at 100, 250, 400, 1,000, and 2,000 completed fits.
- H2: 443 transformed completed end-to-end bootstrap fits; percentile interval **[-0.01663842, 0.04356252]**, median 0.01473355.
- H3: 443 transformed completed end-to-end bootstrap fits; percentile interval **[-0.03094347, 0.01025936]**, median -0.01135429.
- H4: 443 transformed completed end-to-end bootstrap fits; percentile interval **[-0.02697505, 0.00640311]**, median -0.01081126.

The H2/H3/H4 percentile intervals include zero. Thus corrected H3 is rejected by the protocol-derived Wald/Holm procedure but not corroborated by the existing nested bootstrap, paralleling the existing H2 inference tension.

Draw transformation was validated by regenerating and explicitly centered-refitting H1 iterations 0--9 and H2--H4 regression-stream iterations 0--2. Maximum observed target-coefficient discrepancy was below `2e-15`.

## 6. Superseded historical values

The following direct-`0/1` primary interpretations and their Holm values are superseded:

- H1 `E:L=0.00434593`, interaction conditional on `R=0`;
- H2 `E:L=0.02499584`, interaction conditional on `R=0`;
- H3 `E:R=-0.00095758`, interaction conditional on `L=0`;
- the historical four-test Holm table based on those reference-level pairwise coefficients.

H4's numeric coefficient is unchanged by the verified reparameterization, but its Holm p-value changes from 0.11532 to 0.05766 because the full corrected family was recomputed.

The historical `J_EL=1.242` is an `R=0` four-configuration index and must be renamed `J_EL_given_R0`; it is not the multiplicative equivalent of centered H1. No prospective `R=1` value has yet been calculated.

## 7. Manuscript consequences

Material revision is required before submission:

- **Abstract:** the statement that no interaction involving the residual shortcut is supported is no longer correct under the corrected primary Wald/Holm family; it must also disclose the H3 bootstrap non-corroboration.
- **Main Results and confirmatory table/forest figure:** replace all H1--H4 estimates, SEs, intervals, raw p-values, Holm p-values, decisions, and source data with corrected values.
- **Discussion and conclusion:** revise the claim of no residual-related interaction and distinguish the L-averaged H3 result from the historical `L=0` simple interaction. Preserve the inference-method tension.
- **J figure/caption/text:** rename the historical quantity `J_EL_given_R0` and remove any implication that it is R-marginal or directly equivalent to centered H1.
- **Supplement:** update primary-family, bootstrap, diagnostic, and historical-correction descriptions and label direct-`0/1` outputs superseded.

The manuscript title remains descriptively accurate and does not require correction solely because of factor coding. Per the original task, the abstract, conclusion, title, and headline prose have not been edited during this phase.

## 8. Commits and outputs

- Adjudication: `79b6b87bbde5228e1450fafcd6a8df132b56cf4d`.
- Frozen correction plan: `ec35570569cb0078bbf3f49a4b1b421ccad8c1c4`.
- Centered model/family correction: `948e81c5087d6a829d3aa698c7cc623799177a36`.
- Completed 2,000-fit bootstrap and explicit validation: `c6c9f2a05ece0d42f09c3ebbf486e1c3e10a5040`.
- Machine-readable corrected outputs: `results/primary_corrected/effect_coded/`.
- Preserved superseded artifacts: `results/superseded/direct_01_factor_coding/`.

## 9. Remaining blockers

No blocker remains for the factor-coding correction itself. The protocol article's inaccessible full text remains a provenance limitation: if later produced and explicit about coding/conditioning, adjudication must be reopened. The remaining independent-seed, depth/weighting, conditional-J, task-metric, and resource-accounting analyses still require their committed prospective plans before execution.
