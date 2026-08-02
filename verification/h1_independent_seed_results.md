# Independent-seed H1 robustness result

**Status:** completed post-primary robustness analysis under the plan frozen at `7cdb9a2b9a820799fe1b05491f9498b838f5a15c`. This is not part of the original Holm family and is not an independent-investigator replication.

The independent-seed centered H1 estimate is 0.007726 (SE 0.001089; Wald 95% CI [0.005592, 0.009860]; unadjusted p=1.29e-12). The 2,000-fit cluster bootstrap completed with zero failures and gives a percentile 95% CI [0.003402, 0.011923] (median 0.007733). Both intervals exclude zero in the positive direction.

The original corrected estimate was 0.004043 with Wald 95% CI [0.001924, 0.006162]. The independent-seed estimate has the same sign but lies above that original interval. Under the frozen categories, the result is therefore **direction retained but magnitude uncertain**. It supports directional robustness while flagging seed-root sensitivity in effect size; it is not described as “confirmed.”

Endpoint checks at 100, 250, 400, 1,000, and 2,000 completed fits are retained in `bootstrap_endpoints.csv`; validation and provenance are recorded alongside the coefficient, draws, failure log, source table, and comparison figure in `results/independent_seed_h1/effect_coded/`.
