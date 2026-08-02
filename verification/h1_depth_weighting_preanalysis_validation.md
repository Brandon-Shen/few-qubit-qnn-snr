# H1 depth/weighting pre-analysis validation

**Boundary:** structural validation only, completed before the categorical depth model was fit. No depth-specific interaction estimate was calculated or inspected.

Both authoritative exact-gradient tables contain 25,600 `statevector_exact` rows, budget 0 only, eight configurations, depths 1/2/3/4/6, 50 initialization clusters, and no duplicate `(initialization_id,configuration_id,depth,parameter_id)` keys. Rows by depth are 1,600/3,200/4,800/6,400/9,600; matched parameter counts per initialization are 4/8/12/16/24. Every `(initialization,depth,parameter)` has all eight configurations, all gradients and transformed responses are finite, and the centered factor support is prospectively required to be exactly `{-0.5,+0.5}`.

The run manifests identify seed roots 20260726 and 3872531887. Their 50 derived initialization-seed values have empty intersection. Input checksums differ and match the frozen independent-seed provenance. The original and independent-seed tables are therefore eligible for separate fitting and independence-based comparison of derived estimates.
