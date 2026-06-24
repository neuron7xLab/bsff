<!-- SPDX-License-Identifier: CC-BY-4.0 -->
# BNCI2014-001 executable lock

Machine-readable lock: [`BNCI2014_001_EXECUTABLE_LOCK.json`](BNCI2014_001_EXECUTABLE_LOCK.json)
(`status: COMPLETE_EXECUTABLE_LOCK`). Audited by `research/bci_generalization/audit_bnci_lock.py`
→ `BNCI_LOCK_EXECUTABLE` (`artifacts/blockers/bnci/LOCK_AUDIT_REPAIRED.json`).

- **Method (frozen):** `sampen_lower_tail_m2_r015_v1`, p ≤ α/2 = 0.025, MIAAFT null, AR-null
  specificity, BH-FDR. Runner: `research/bci_generalization/run_bnci_confirmatory.py`.
- **Aggregation (frozen):** spatial mean across the 22 EEG channels → one signal per epoch;
  per-epoch verdict; pooled SURVIVED fraction (positive) + AR-null FPR (specificity).
- **Data:** BNCI2014-001 subjects 1–9, 250 Hz, bandpass 8–30 Hz, epoch [0.5, 2.5] s (501 samples).

## Execution status
**WITHHELD — `BNCI_BLOCKED_METHOD`.** The lock is executable, but the S2-C1 finite-N rule
(calibrated on 4097-sample Bonn) is **not predeclared-valid** on 501-sample epochs
(`artifacts/blockers/bnci/METHOD_VALIDITY.json`; probe AR-null FPR ≈ 0.375). The confirmatory was
**not** run; the method must first be re-preregistered with an epoch-length-calibrated specificity
rule and validated on a short-epoch null. No BNCI claim.
