<!-- SPDX-License-Identifier: CC-BY-4.0 -->
# Short-epoch specificity rule

The specificity guard for short epochs MUST be validated on **spectrum-matched** nulls:

1. Build AR(p) nulls from the **band-passed (8–30 Hz)** real epochs (preserving the narrowband spectrum).
2. Split into CALIBRATION and HELD-OUT sets (deterministic seeds, no overlap).
3. Predeclare the rule (R1/R2/R3) and its parameters **before** seeing held-out results.
4. Accept only if held-out FPR ≤ 0.05 AND a short-epoch positive control retains power ≥ 0.80.

Encoded length/spectrum guard: the S2-C1 finite-N rule is **not** valid below ~4096 samples or on
narrowband signals without this validation; the runner must refuse such regimes unless a passing
`METHOD_REPAIR_LOCK` is present.
