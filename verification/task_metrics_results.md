# Prepared-state task metrics

**Status:** post-primary descriptive initialization-state metrics; plan `645521db6511ca049d89e64f810e65a3407a7b52`. No optimization was performed.

Generated 4,000 unique terminal-block prepared states; all bounds/complementarity and predeclared exact-gradient checks passed.

- original: configuration-depth mean fidelity spans 0.0338 to 0.0817; mean normalized energy spans 0.4631 to 0.5529.
- independent_seed: configuration-depth mean fidelity spans 0.0322 to 0.0962; mean normalized energy spans 0.4561 to 0.5537.

Across matched configuration-depth cells, the largest absolute seed-set difference is 0.0424 in mean fidelity and 0.0731 in mean normalized energy. Objective-level means are retained in `objective_summary.csv`; L=0 and L=1 means are exactly identical because objective choice changes the evaluated cost but not the prepared state. The ranges overlap strongly across seed sets, so no conspicuous seed-unstable task-metric separation is evident descriptively.

The source table `gradient_metric_comparison.csv` places RMS exact-gradient magnitude beside energy and fidelity without a significance test. It does not establish that larger initialization gradients improve task metrics, and no causal or optimization claim is made.

These are prepared-state-at-initialization descriptions. They do not demonstrate optimization convergence, final performance, trainability, hardware advantage, or savings.
