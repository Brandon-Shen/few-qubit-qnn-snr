# Conditional J_EL bootstrap results

**Status:** post-primary descriptive; plan `645521db6511ca049d89e64f810e65a3407a7b52`. These ratios are not centered-H1 equivalents.

- original J_EL_given_R0: 1.241760 (+24.2% vs 1), bootstrap median 1.238674, percentile 95% CI [1.082210, 1.414864], 2000 completed, 0 failed.
- original J_EL_given_R1: 1.126633 (+12.7% vs 1), bootstrap median 1.124329, percentile 95% CI [0.991331, 1.285152], 2000 completed, 0 failed.
- independent_seed J_EL_given_R0: 1.163219 (+16.3% vs 1), bootstrap median 1.160949, percentile 95% CI [1.007100, 1.352596], 2000 completed, 0 failed.
- independent_seed J_EL_given_R1: 1.242137 (+24.2% vs 1), bootstrap median 1.238157, percentile 95% CI [1.049874, 1.449258], 2000 completed, 0 failed.

R0 uses configurations 5/1/(2/3); R1 uses 8/4/(6/7). RMS pools unique exact-gradient parameter rows before aggregation, so deeper depths receive greater parameter/observation weight. No optimization, trainability, or shot-saving claim follows.
