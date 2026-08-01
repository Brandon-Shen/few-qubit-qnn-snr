# Task 5 -- stale-reference audit

Every location matching the search terms specified for Task 5 (n=40, "40
iterations", "low-iteration", the old H2/H3/H4 final bootstrap intervals,
the planned-but-unperformed D=1/zero-variance checks, stale captions, "Tasks
1-4 pending" language), found by direct grep against
`paper/main.tex.bak_pre_task5_20260730` (the pre-integration backup) and
resolved in `paper/main.tex`. Historical/chronological occurrences (the
superseded pooled-mode n=8/100/400 runs in Appendix A.3/A.5/A.6) are listed
separately at the bottom and were deliberately **not** altered.

| # | Location (pre-integration) | Stale content | Resolution |
|---|---|---|---|
| 1 | Abstract | "H2 completed 40 iterations and did not independently corroborate the Wald/Holm rejection" | Updated to n=443, framed as a stable pattern across a ~10x extension rather than an artifact of few iterations |
| 2 | \S H2 (\texorpdfstring{H2}{}) | Full paragraph reporting n=40 median/CI as a "low-iteration diagnostic" | Replaced with n=443 final results; explicit required-interpretation language ("supported by the prespecified Wald/Holm procedure ... not corroborated by the nested percentile bootstrap") |
| 3 | \S H3 | No bootstrap sentence existed in prose (table-only) | Added n=443 median/CI sentence, framed as consistent with (not proof of) non-rejection |
| 4 | \S H4, "Bootstrap" bullet | n=40, interval $[-0.02177,0.00666]$, "inconclusive diagnostic" | Replaced with n=443 final interval; reframed as "genuinely inconclusive... rather than a result awaiting simple confirmation from additional bootstrap iterations" |
| 5 | Table `tab:confirmatory-summary` | H2/H3/H4 bootstrap column shows `(40)`; H2 corroboration "Not established"; caption calls the H2--H4 intervals "low-iteration diagnostics ... not given equal inferential weight" | All three coefficients updated to n=443 intervals; H2 corroboration explicitly "No"; H3/H4 marked "Not applicable$^\dagger$" with a footnote against equivalence; caption rewritten to state the bootstrap does not corroborate H2 "stably... rather than narrowing with more iterations" |
| 6 | Figure `fig:confirmatory-forest` caption | "completed $n=40$ ... limited resolution ... not treated as equally stable confidence intervals" | Rewritten for n=443; states the Wald/bootstrap disagreement is "reported rather than resolved by selecting one method" |
| 7 | \S 5.1 Summary | "achieved end-to-end bootstrap did not independently corroborate H2" (no n) | Added explicit n=443 and "stably rather than as an artifact of too few iterations" |
| 8 | \S 5.1 Summary, H4 sentence | "the low-iteration bootstrap remains inconclusive" | "the $n=443$ bootstrap remains genuinely inconclusive rather than a result awaiting more resampling" |
| 9 | \S 5.4 Limitations | "excluding zero-variance cells could induce selection... A professional-journal submission should therefore include the planned $D=1$-exclusion and exclusion-rate sensitivity checks"; "completed only $n=40$ iterations, far below the targeted 2000... should not be interpreted as a stable characterization" | Full paragraph rewrite: reports the completed D=1/zero-variance findings (including the flagged $L=0$-only pattern and the $\beta_{EL}$ SE-unit shifts), the n=443 final bootstrap result (now explicitly called stable for H2 non-corroboration), residual heteroscedasticity, and the no-hardware-noise limitation |
| 10 | \S Conclusion | "the achieved $n=40$ end-to-end bootstrap does not independently corroborate H2" | Updated to $n=443$, "stably across a roughly tenfold extension"; added a sentence flagging the $L=0$-only zero-variance pattern as an unresolved selection concern |
| 11 | Appendix A.13 | "The adopted end-to-end bootstrap completed $n=40$ iterations, below the targeted scale... both are reported as low-iteration diagnostics" | Original sentence preserved verbatim (historical chronology, "at the time of this item"), with an added sentence: "This $n=40$ run was subsequently extended to a final $n=443$; it is not the final achieved result... see item A.18." |
| 12 | \S Methods, "Mixed-effects models" | `% REQUIRED SOFTWARE REPORTING BEFORE SUBMISSION` comment (unresolved TODO) | Replaced with a concise resolved paragraph (language/package versions, optimizer, ML/REML, convergence/singularity policy, pointer to full Software Availability section) |
| 13 | \S 4.1 (before H1) | `% DATA-DEPENDENT ROBUSTNESS CHECK REQUIRED...` comment (unresolved TODO) | Replaced with the real `\subsection{Zero-variance exclusion and block-count sensitivity}` (Parts A and B, Figures 6-7) |
| 14 | End matter | `\section*{Data Availability}` / `\section*{Code Availability}` were generic aspirational placeholders with no real content | Filled with real, specific content (file categories, hash pointers, test count); DOI/URL remain explicit bracketed placeholders (not invented); added a new `Software Availability and Reproducibility Information` section |
| 15 | \S Robustness and implementation checks | Intro paragraph only referenced A.1--A.14 | Expanded to reference new items A.15--A.19 and added full paragraphs + Figures 8-9 for convergence/optimizer, residual diagnostics, and leave-one-initialization-out influence |

## Historical occurrences deliberately left unchanged (verified byte-identical)

| Location | Content | Why unchanged |
|---|---|---|
| Appendix A.3 | "For H1, 400 of the planned 2,000 iterations completed... For H2--H4, only eight iterations completed before a memory ceiling was identified" | Describes the very first reduced-iteration bootstrap attempt; genuine chronology, not the adopted end-to-end result |
| Appendix A.5 | "At 100 iterations, the H2 percentile interval was wider than the eight-iteration interval..." | Pooled-mode, superseded; historical record of the memory-redesign validation |
| Appendix A.6 | "Four shards reached 100/100 iterations with zero failed fits, pooling to $n=400$..." | Pooled-mode n=400 run, explicitly marked superseded already; not the adopted end-to-end-only estimand |

## One issue found, out of Task 5's scope, not fixed at the time -- since resolved

`\includegraphics{figures/fig0_el_primary.pdf}` (label `fig:el-primary`, in
the H2 subsection) referenced a file that **did not exist anywhere in the
repository** at the time of Task 5 (confirmed via
`paper/scripts/structural_check.py`, the only remaining problem it reported
both before and after this integration pass). This figure was not part of
Tasks 1--4's outputs and is not one of fig6--fig10; it appears to have been
added directly to `main.tex` in a prior editing session without ever
generating the corresponding file. **Not fixed in Task 5**: fixing it would
have required either inventing figure content (not permitted) or removing
a manuscript figure/caption outside that task's scope, so it was flagged
prominently in the integration report instead.

**Status update**: in a follow-up task, this figure was reconstructed
reproducibly from frozen machine-readable data -- see
`verification/fig0_el_primary_regeneration.md`. `paper/scripts/structural_check.py`
no longer reports it as missing, and no numeric value from the old
(nonexistent) file was used; `I_EL`/`J_EL` were recomputed independently
two ways from `results/production_confirmatory/pointwise_gradient_statistics.parquet`
(end-to-end-mode only) and `results/production_confirmatory/raw/exact.parquet` and cross-checked
to `atol=1e-9`.
