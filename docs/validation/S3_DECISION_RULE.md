<!-- SPDX-License-Identifier: CC-BY-4.0 -->
# S3 decision rule — formal specificity test (PI-grade)

The bright-line G2 gate is framed as a **one-sided hypothesis test of the true AR-null FPR**,
not a point-estimate comparison (the weakness the falsification exposed in S2).

## Hypotheses
- H0 (must be rejected to PASS): **true FPR ≥ 0.05** — the instrument is not specific enough.
- H1 (PASS): true FPR < 0.05, with 97.5% one-sided confidence.

## Decision rule (pre-registered, frozen)
PASS G2 iff the **Wilson 95% CI upper bound** of the pooled seed-averaged AR-null FPR is **≤ 0.05**.
This is equivalent to a one-sided test rejecting H0 at α = 0.025. It is strictly stronger than the
S2 rule (point estimate ≤ 0.05), which a favorable seed can satisfy while the true FPR exceeds 0.05.

## Design precision (`S3_DESIGN_POWER.json`)
At N = 1000 AR-null tests, the Wilson 95% CI half-width at p ≈ 0.035 is ~0.011, so the gate passes
only if the observed FPR ≤ ~0.035 (CI-upper 0.048) and fails at FPR ≥ 0.04 (CI-upper 0.054). The
calibration point estimate (0.0354) sits at the resolution boundary — the design is adequately
powered to resolve a robust pass from a marginal/non-robust outcome.

## G1
Seed-averaged Set-E SURVIVED fraction ≥ 0.80 (power was already robust under falsification).

## Forbidden
No α/threshold/statistic change after results; no seed dropping; no favorable-seed selection.
