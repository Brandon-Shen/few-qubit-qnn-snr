# Final H2--H4 nested bootstrap

**Status:** exactly 1,000 unique valid fits included under the revised stopping instruction.

Completed successfully before stop: 1178; included: 1,000; excluded post-target successes: 178; failed: 0; rejected: 0.

The original 443 draws are unchanged and form the historical prefix. Excluded valid draws are retained under `results/superseded/h2h4_bootstrap_post_1000_excluded/`.

Endpoint Monte Carlo intervals below are binomial/order-statistic rank intervals and are not scientific confidence intervals.

```csv
coefficient,n_attempted,n_successful,n_failed,n_rejected,n_successful_excluded_after_target_revision,fit_failure_rate_pct,median,ci_lo,ci_hi,width,includes_zero,ci_lo_mc95_lo,ci_lo_mc95_hi,ci_lo_mc95_rank_lo,ci_lo_mc95_rank_hi,ci_hi_mc95_lo,ci_hi_mc95_hi,ci_hi_mc95_rank_lo,ci_hi_mc95_rank_hi
E_c:L_c,1178,1000,0,0,178,0.0,0.0152798583269372,-0.0162397203608088,0.0459922300736221,0.062231950434431,True,-0.0210920460818323,-0.0137134534128972,16,36,0.0439130021972518,0.0486668743191291,965,985
E_c:R_c,1178,1000,0,0,178,0.0,-0.0114180428855887,-0.0313752307678077,0.0095625151608029,0.0409377459286107,True,-0.03425057407758,-0.0299732449158972,16,36,0.0075109469120111,0.0118880733299266,965,985
L_c:R_c:depth_z,1178,1000,0,0,178,0.0,-0.0104259638974791,-0.0259640525878784,0.0058630307372051,0.0318270833250836,True,-0.0284458658248686,-0.0247165097732325,16,36,0.0044819580201976,0.0071291211313173,965,985
```
