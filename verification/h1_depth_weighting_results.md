# H1 depth heterogeneity and weighting results

**Status:** completed post-primary exploratory/robustness analysis under plan `d528566acb2488380b5efd42d91b9e81fc739aaf`. The raw datasets were fit separately. These results are not part of, and do not alter, the original H1--H4 Holm family.

## Depth-specific centered E×L contrasts

Original data:

- D=1: -0.005251 (SE 0.004315; 95% CI [-0.013708, 0.003206]; raw p=0.2237; within-dataset Holm p=0.4473)
- D=2: -0.003579 (SE 0.003051; 95% CI [-0.009560, 0.002401]; raw p=0.2407; within-dataset Holm p=0.4473)
- D=3: 0.012588 (SE 0.002491; 95% CI [0.007706, 0.017471]; raw p=4.347e-07; within-dataset Holm p=2.174e-06)
- D=4: 0.004664 (SE 0.002157; 95% CI [0.000435, 0.008892]; raw p=0.03064; within-dataset Holm p=0.1225)
- D=6: 0.003446 (SE 0.001762; 95% CI [-0.000007, 0.006898]; raw p=0.05046; within-dataset Holm p=0.1514)

Independent-seed data:

- D=1: 0.001862 (SE 0.004345; 95% CI [-0.006653, 0.010378]; raw p=0.6682; within-dataset Holm p=0.6682)
- D=2: 0.003120 (SE 0.003072; 95% CI [-0.002901, 0.009141]; raw p=0.3099; within-dataset Holm p=0.6197)
- D=3: 0.006250 (SE 0.002508; 95% CI [0.001334, 0.011166]; raw p=0.01272; within-dataset Holm p=0.03815)
- D=4: 0.007885 (SE 0.002172; 95% CI [0.003627, 0.012143]; raw p=0.0002836; within-dataset Holm p=0.001134)
- D=6: 0.010870 (SE 0.001774; 95% CI [0.007393, 0.014346]; raw p=8.885e-10; within-dataset Holm p=4.443e-09)

The point-estimate direction is positive in both datasets at 3 of 5 depths (D=3, 4, and 6), giving the frozen category **retained at most depths**. At D=1 and D=2, the original point estimates are negative and imprecise while the independent-seed estimates are positive and imprecise. Thus “direction retained at all depths” is not justified.

## Weighting and adopted pooled estimands

- Original equal-depth: 0.002374 (95% CI [-0.000164, 0.004911]).
- Independent-seed equal-depth: 0.005997 (95% CI [0.003443, 0.008552]).
- Original observation/parameter weighted: 0.004043 (95% CI [0.001929, 0.006157]).
- Independent-seed observation/parameter weighted: 0.007726 (95% CI [0.005597, 0.009854]).
- Frozen adopted pooled: original 0.004043; independent seed 0.007726.

Observation and matched-parameter weights are identical: `(0.0625, 0.125, 0.1875, 0.25, 0.375)` for D=1/2/3/4/6. The categorical observation-weighted point estimates equal the adopted pooled estimates to numerical precision in this balanced design. Their SEs differ slightly because the categorical and adopted pooled models estimate different fixed-effect/covariance structures. Relative to the frozen materiality unit of one original-H1 SE, both datasets are **same direction but magnitude weighting-sensitive**; no weighting changes the point-estimate sign.

## Original-versus-independent-seed differences

The equal-depth difference is 0.003624 (95% CI [0.000023, 0.007224]). The observation/parameter-weighted difference is 0.003683 (95% CI [0.000682, 0.006683]). The frozen adopted-pooled difference is 0.003683 (95% CI [0.000675, 0.006690]).

D=6 supplies the largest absolute observation-weighted contribution (45.9%) and its difference interval excludes zero, but it does not reach the frozen 50% single-depth threshold; D=1--2 together supply only 21.2%. The frozen localization result is therefore **no clear localization**.

## Moderation tests

- Original: mixed-model Wald χ²(4)=22.844, p=0.000136; initialization-clustered robust χ²(4)=6.008, p=0.1985.
- Independent seed: mixed-model Wald χ²(4)=7.563, p=0.109; initialization-clustered robust χ²(4)=1.810, p=0.7706.

Mixed-model and robust point contrasts agree to machine precision, but their covariance-based moderation conclusions disagree for the original dataset. Both fail to reject moderation homogeneity for the independent-seed dataset. Evidence for original-data moderation is therefore covariance-sensitive.

## Frozen interpretation

The overall classification **direction retained but magnitude uncertain** remains appropriate. A more precise restrained description is: **the pooled positive direction is retained, depthwise positive direction agrees at three of five depths, magnitude is weighting-sensitive, and the cross-seed magnitude difference has no clear localization under the prospectively frozen rule**.

## Exact recommended future manuscript language

1. “In a post-primary categorical-depth robustness analysis, the centered E×L interaction was positive in both seed datasets at D=3, 4, and 6, whereas the original estimates at D=1 and D=2 were negative and imprecise and the independent-seed estimates were positive and imprecise.”
2. “Equal-depth averaging reduced the interaction relative to observation/parameter weighting in both datasets, but did not change its point-estimate sign; observation and matched-parameter weights were identical because row counts were balanced apart from the planned depth-dependent parameter count.”
3. “The seed-minus-original difference was largest and distinguishable from zero at D=6, but under the prospectively frozen contribution rule the pooled magnitude difference had no clear single-depth or shallow-depth localization.”
4. “Model-based inference detected depth moderation in the original dataset but the initialization-clustered robust test did not; neither test detected moderation in the independent-seed dataset, so moderation evidence was covariance-sensitive.”
5. “These post-primary results retain the overall description ‘direction retained but magnitude uncertain,’ while adding that depthwise direction agreed at three of five depths and magnitude was weighting-sensitive.”

No manuscript file was edited. Machine-readable contrasts, covariance matrices, comparisons, validation, figures, and caveats are under `results/h1_depth_weighting/`.
