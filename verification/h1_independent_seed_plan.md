# Independent-seed H1 plan

**Status:** post-primary rerun; frozen before viewing the centered independent-seed H1 result. It is not added to the original Holm family and is not described as an independent-investigator replication.

## Question and inputs

Assess whether the corrected centered H1 direction and magnitude are retained under the verified non-overlapping seed root. Input: `results/h2_replication_v1/_pipeline_output_stage1/raw/exact.parquet`; comparator: `results/primary_corrected/effect_coded/corrected_confirmatory_hypotheses.csv`; seed provenance: `configs/confirmatory.yaml`, `configs/h2_replication_v1_stage1.yaml`, and both run manifests.

Require statevector-exact mode only; 8 configurations; depths `{1,2,3,4,6}`; 50 initializations; `E,L,R` matching `CONFIGURATION_TABLE`; finite exact gradients; and exactly one row per `(initialization_id,configuration_id,depth,parameter_id)`. Reject budget/replicate duplication, seed-root/derived-initialization-seed overlap, missing matched parameters, or changed depth scaling.

## Model and inference

Add `E_c=E-.5`, `L_c=L-.5`, `R_c=R-.5`; response `asinh(abs(exact_gradient))`. Fit the frozen corrected H1 formula and random effects: initialization intercept plus `(initialization,depth,parameter)` variance-component intercept, REML, optimizer fallback `lbfgs,bfgs,cg,powell,nm`. Report `E_c:L_c`, covariance-based SE, normal-reference two-sided p, Wald CI, optimizer, convergence/singularity, variance estimates, warnings, rows, clusters, and parameter counts by depth. No multiplicity adjustment.

## Bootstrap

Resample 50 complete initialization clusters with replacement, uniquely relabel every sampled copy, retain every configuration/depth/matched parameter, and perform no within-cell resampling. Deterministic seed `155001`, keyed by `(seed,iteration)`. Target exactly 2,000 completed fits; 5,000 is not planned in this pass because the original 2,000-fit runtime establishes 2,000 as the practical target. Checkpoint after every 50 attempts and summarize endpoints at 100, 250, 400, 1,000, and 2,000 completed fits. Resume by iteration identity; record attempted/completed/failed, warnings, and reasons. Percentile 95% interval is frozen.

Outputs: `results/independent_seed_h1/effect_coded/` containing validation JSON/MD, coefficient CSV/JSON, model summary, direct and centered draws, checkpoint/endpoint files, failure log, comparison table, and comparison figure/source CSV. Metadata records this plan commit, analysis commit, input checksums, and commands.

## Interpretation and stops

Categories: “direction and magnitude retained” if signs agree and the rerun estimate lies within the original Wald CI; “direction retained but magnitude uncertain” if signs agree but that condition fails; “direction not retained” if signs differ; “too imprecise to assess” if the rerun Wald and bootstrap intervals are both too broad to distinguish either direction. Do not use “confirmed.” Stop for any validation/provenance failure, changed model eligibility/coding, irreproducible seed separation, or nonconvergence requiring an unplanned model change.
