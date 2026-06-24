<!-- SPDX-License-Identifier: CC-BY-4.0 -->
# BNCI method-repair protocol (predeclared)

BNCI is `BNCI_BLOCKED_METHOD`: the S2-C1 SampEn lower-tail rule (p ≤ α/2), calibrated on
4097-sample Bonn, is anti-conservative on **narrowband (8–30 Hz) 501-sample** BNCI epochs
(probe AR-null FPR ≈ 0.375). A synthetic white-noise-spectrum check was clean (FPR 0.0125),
confirming the failure is **spectrum-specific**, not merely length — see
`artifacts/bnci2014_001/SHORT_EPOCH_SPECIFICITY_VALIDATION.json`.

## Do NOT execute BNCI until repair passes
Lock: `artifacts/bnci2014_001/METHOD_REPAIR_LOCK.json` (`PREDECLARED_NOT_VALIDATED`).

## Candidate repairs (pre-registered before validation)
- **R1** empirical threshold calibrated on spectrum-matched 8–30 Hz 501-sample AR nulls.
- **R2** BH-FDR specificity across the epoch family.
- **R3** length-aware statistic (permutation entropy / RQA), re-preregistered.

## Success criterion (frozen)
On **spectrum-matched** (8–30 Hz, 501-sample) **held-out** AR nulls: FPR ≤ 0.05, AND
positive-control SURVIVED ≥ 0.80. α = 0.05 fixed.

## Forbidden
Tuning the threshold after seeing validation/power; changing α; subject/channel cherry-picking;
running the BNCI confirmatory before the repair passes spectrum-matched validation.
