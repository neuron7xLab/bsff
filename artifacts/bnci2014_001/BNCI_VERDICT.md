<!-- SPDX-License-Identifier: CC-BY-4.0 -->
# BNCI2014-001 confirmatory — verdict

**BNCI_BLOCKED_METHOD** (commit `0e2d836f74dc`).

Lock audit: **BNCI_LOCK_EXECUTABLE** (B1 resolved). Method-validity gate (B2): the S2-C1 finite-N
rule (calibrated on 4097-sample Bonn) is **not predeclared-valid** on 501-sample BNCI epochs — a probe
showed AR-null FPR ~0.375 (≫ 0.05). Running to a foreknown specificity failure, or re-tuning to pass,
are both forbidden. Full confirmatory **not executed**; no BNCI claim.

Data acquisition is GREEN (subject 1: 250 Hz, 22 EEG). `BONN_S2_BRIGHT_LINE_PASSED` unchanged.

Next: pre-register an epoch-length-calibrated specificity rule, validate on a short-epoch null,
then execute under fresh authorization. Not clinical/regulatory/device.
