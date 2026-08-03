# Centered H3 interaction robustness results

**Status:** post-primary explanatory/sensitivity analysis; plan commit `7cdb9a2b9a820799fe1b05491f9498b838f5a15c`. Nothing here changes the corrected H1--H4 family.

The corrected end-to-end H3 average (`E_c:R_c=-0.011615`, Wald 95% CI `[-0.021697,-0.001534]`) is not a similar interaction under both objectives. At global infidelity (`L=0`) the simple E×R interaction is `-0.000958` (SE `0.007293`, CI `[-0.015251,0.013336]`, p=`0.896`). At normalized energy (`L=1`) it is `-0.022273` (SE `0.007256`, CI `[-0.036493,-0.008052]`, p=`0.00214`). Their equal average exactly reproduces corrected H3.

The final 1,000-draw bootstrap intervals include zero for all three: L=0 `[-0.029117,0.024560]`, L=1 `[-0.049490,0.007197]`, and averaged `[-0.031375,0.009563]`. The original 443 draws are the preserved historical prefix.

Restricting to active-residual depths D={3,4,6} gives a more negative averaged interaction, `-0.014788` (SE `0.004945`, CI `[-0.024480,-0.005095]`, p=`0.00279`). Again L=0 is near zero (`-0.002126`, CI `[-0.015856,0.011603]`), while L=1 is negative (`-0.027449`, CI `[-0.041134,-0.013764]`). No active-subset nested bootstrap was planned, so the full-sweep interval is not reused.

The categorical mixed model finds no joint depth moderation (chi-square(4)=`3.080`, p=`0.545`). Depth-specific averaged estimates are positive/near-zero at D=1 and 2, negative at D=3,4,6; only the model-based D=3 interval excludes zero. Initialization-clustered OLS likewise finds no joint moderation (chi-square(4)=`2.083`, p=`0.721`), and every cluster-robust depth interval includes zero.

Estimator mode is contradictory. Conditional mode gives a positive averaged interaction `0.006978` (SE `0.005981`, CI `[-0.004745,0.018701]`, p=`0.243`), with both objective-specific estimates near `+0.007` and intervals including zero. Its direction therefore disagrees with the adopted end-to-end result and the intervals overlap.

All 50 centered leave-one-initialization-out fits converged. The averaged estimate remained negative in all 50 (`-0.014433` to `-0.008562`) and had raw p<0.05 in 41/50. The L=1 simple interaction remained negative in all 50; L=0 crossed sign in 16/50 and stayed near zero.

**Recommended interpretation:** model-dependent directional signal whose end-to-end pattern is objective-specific to the energy-objective condition. It is not a robust interaction: the nested bootstrap includes zero, conditional mode reverses direction, and cluster-robust depth intervals include zero. Manuscript wording should state that the corrected Wald/Holm family rejects H3, but corroborating resampling and estimator-mode evidence does not establish a stable residual interaction.
