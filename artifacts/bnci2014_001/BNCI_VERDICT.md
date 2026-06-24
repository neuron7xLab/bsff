<!-- SPDX-License-Identifier: CC-BY-4.0 -->
# BNCI2014-001 confirmatory — verdict

**BNCI_BLOCKED_LOCK_INCOMPLETE** (commit `09c6fb0d44fd`).

Authorization to execute was granted. The lock audit (`LOCK_AUDIT.json`) found execution-critical
gaps, so the confirmatory was **not** run — the PRIMARY LAW forbids inventing the missing
specification to force a result.

## Gaps (all execution-critical)
1. `exact_commands[0]` points to `run_experiment.py`, which implements **CSP cross-session
   decoding** (a decoding gap), **not** the locked `sampen_lower_tail` + MIAAFT + AR-null FPR
   method. No runner for the locked method exists.
2. `exact_commands[1]` = `python tools/... aggregate` — literal `...` placeholder.
3. The per-class SURVIVED-fraction criterion does not specify how 22 channels reduce to a
   per-epoch verdict — execution-critical (affects result and feasibility).

## What is NOT the blocker
Data acquisition is **GREEN** (`DATA_SMOKE_SUBJECT1.json`: subject 1, 250 Hz, 22 EEG). moabb 1.5.0
installed; `bsff evidence verify` PASS; `bsff selftest` rc=0.

## Canonical state (unchanged)
`BONN_S2_BRIGHT_LINE_PASSED`. `BNCI_chain = UNLOCKED_FOR_PREREGISTRATION_ONLY`. **No BNCI claim.**

## Next
Re-preregister a complete, executable lock (implement the locked-method BNCI runner + specify
deterministic channel/epoch aggregation), commit it, then execute under fresh authorization.
