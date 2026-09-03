# SPEC-015 — Causal Engine
Supported methodological families: DiD, synthetic control, Double ML, causal forest, IV.
Every analysis stores identification assumptions and diagnostics.
If assumptions are not supportable, service returns `NOT_IDENTIFIED` rather than a causal claim.
