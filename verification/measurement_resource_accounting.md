# Measurement and resource accounting

**Status:** implementation audit/descriptive accounting; plan `645521db6511ca049d89e64f810e65a3407a7b52`.

The global target-infidelity estimator does not construct an inverse target-state circuit. It draws a binomial count directly from the exact statevector overlap probability and records one abstract `overlap` objective setting; target-preparation/inverse gates and physical costs are not represented. “One basis” is accurate only as one observable setting in this simulator abstraction.

TFIM energy uses two settings: one Z-basis multinomial jointly estimates three ZZ terms and one X-basis multinomial jointly estimates four X terms. End-to-end additionally samples D-1 forward-feature Z jobs and re-encodes noisy features; conditional mode holds those features exact and excludes their variance. Modes are separate.

All 320 design rows conserve requested B exactly, have nonnegative deterministic allocations and zero zero-shot production jobs. The zero-variance join contains 1833 cells with complete resource matches. At D=6 the manuscript extremes are 48 jobs (conditional/global) versus 61 (end-to-end/local), a 27.08% increase, reproducing the approximately 27% claim.

Only total implemented shot budget is matched—not shots per circuit, circuits/jobs, physical gates, calibration, readout, noise, or wall-clock time.
