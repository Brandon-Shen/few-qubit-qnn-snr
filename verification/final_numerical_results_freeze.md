# Final numerical-results freeze

**Status:** assembled from frozen components under plan `645521db6511ca049d89e64f810e65a3407a7b52`. Headline manuscript sections were not edited.

## Final classifications

- Corrected primary family: H1, H2, and H3 reject under model-based Holm; H4 does not. H2/H3 bootstrap intervals include zero and do not corroborate their Wald/Holm rejections.
- Independent-seed H1: positive direction retained, magnitude uncertain. Depth profile and weighting remain uncertain.
- H3: **model-dependent directional signal, objective-specific under end-to-end mode**; not robust/confirmed.
- Conditional J: see machine rows and `results/jel_conditional/summary.csv`.
- Prepared states: low target fidelity and near-mid-spectrum normalized energy at initialization; L cannot change state preparation; no optimization conclusion.
- Resources: total implemented B is conserved, but jobs/shots per job differ; D=6 extremes are 48 versus 61 jobs (27.08%).
- Figure 0: archived, deterministically regenerated with `given_R0` naming, and restored to the manuscript path.

## Superseded manuscript numbers

Direct-0/1 pairwise factorial interpretations are superseded by centered H1--H3 values. Any text stating H3 non-rejection, H3 estimate near -0.001, H2 estimate 0.0250 as primary, H1 0.004346 as the centered estimand, H2--H4 bootstrap n=40, J without R=0 conditioning, or task metrics as final/optimized performance requires revision.

## Exact proposed replacement language for human review

- Abstract: “Under centered factorial coding, model-based Holm inference rejected H1--H3 but not H4. Initialization-cluster bootstraps corroborated H1, while the achieved H2 and H3 intervals included zero; these discrepancies are reported rather than resolved by selecting one procedure.”
- H1 Results: “The corrected centered E×L exact-gradient interaction was 0.004043 (95% Wald CI 0.001924 to 0.006162; Holm p=0.000739), with a 2,000-fit cluster-bootstrap interval of 0.000473 to 0.007535. An independent-seed rerun retained the positive direction but differed in magnitude, and post-primary depth summaries were weighting-sensitive.”
- H2 Results: “The centered end-to-end E×L coefficient was 0.014338 (95% Wald CI 0.004255 to 0.024422; Holm p=0.01596), while the 443-fit nested-bootstrap interval (-0.01664 to 0.04356) included zero; the Wald/Holm rejection was not independently corroborated by this bootstrap.”
- H3 Results: “The centered E×R coefficient was -0.011615 (95% Wald CI -0.021697 to -0.001534; Holm p=0.04787), but its 443-fit bootstrap interval (-0.03094 to 0.01026) included zero. The end-to-end signal was confined to L=1, conditional mode reversed direction, and robust/depth diagnostics did not establish a stable interaction.”
- Discussion: “Post-primary analyses indicate that H1’s pooled positive direction is reproducible across seed sets but its magnitude and depth profile are uncertain; H2 and H3 remain procedure-sensitive because their Wald/Holm rejections are not corroborated by nested-bootstrap intervals.”
- Limitations: “All task metrics describe terminal-block states at initialization, not optimized performance. Equal nominal B matches total simulated shots only; circuits, jobs, shots per job, physical gates, calibration, readout, noise, and wall-clock resources are not matched.”
- Conclusion: “The strongest cross-procedure evidence concerns H1. H2 and H3 are model-based rejections with bootstrap intervals spanning zero, and H4 remains unresolved; no trainability, hardware, or resource-advantage claim follows.”
- Figure captions: “Label multiplicative indices as conditional on R=0 and state that they are secondary descriptive ratios, not centered mixed-model coefficients.”
- Supplement: “Report centered coding, all bootstrap counts/failures, objective-specific H3 contrasts, conditional J intervals, initialization-state metric bounds, and implemented job-level accounting.”

## Required manuscript revision locations

Abstract; H1/H2/H3 Results; Discussion; Limitations; Conclusion; confirmatory table/forest caption; multiplicative-index paragraph/caption; task-metric language; measurement/resource Methods; Supplement.

## Remaining limitations

Reset-per-block protocol interpretation; finite-replicate zero-variance selection tied to L; covariance-sensitive H3 moderation; no hardware noise or optimization trajectory; conditional multiplicative indices are weighting-dependent descriptive summaries.

Final commit/tag and full test status are populated by the separate provenance update after validation.
