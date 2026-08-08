# Manuscript claim audit results

**Status:** scientific claims pass; supplied PDFs require layout correction and recompilation.

The frozen-value checker verified 28 required article tokens against `results/final_submission_v1/manifest.json` and found no missing required value, changed component hash, ambiguous unconditioned J notation, or prohibited superseded primary value. Extracted text from both supplied PDFs contains the corrected H1--H4 family, independent-seed H1, H1 depth/weighting results, H3 explanatory values, all conditional J values, prepared-state ranges, and resource counts.

Every inference disagreement is preserved: H2 and H3 are described as model-based Wald/Holm rejections whose 443-fit bootstrap intervals include zero; H3 is explicitly “not a robust or confirmed residual interaction”; H4 is unresolved and not evidence of absence. The original $R=1$ J interval is described as including one. Task metrics are terminal-block prepared-state metrics at initialization. Total-shot equality is limited to implemented simulator shots, not physical resources, optimization, hardware, or wall-clock advantage.

Superseded `0.004346`, `0.024996`, historical H4 Holm `0.115`, and historical 400-fit H1 text are absent from the main article and occur only in the supplement's explicitly titled “Historical correction and audit record.” The value `-0.000958` remains appropriately as the frozen post-primary H3 simple interaction at $L=0$, not as primary centered H3. Searches for “optimized performance” and “robust or confirmed” return only explicit negations.

Updated locations: structured abstract; centered-coding, bootstrap, measurement, resource, H1 weighting, H3, J, and task-metric Methods; all Results sections; confirmatory table and figures; Discussion; Limitations; Conclusion; declarations; and all Online Resource 1 sections/tables/captions.

Remaining non-scientific concerns: supplied main page 14 and supplement page 2 clip wide tables; included Matplotlib figures contain Type 3 fonts; supplement PDF metadata title/author are blank; official `sn-jnl.cls` and `sn-basic.bst` are absent from the exported repository project. Minimal `\resizebox{\textwidth}{!}` source corrections have been made for the clipped tables, so the supplied PDFs are now outdated and a new Overleaf compile is required.
