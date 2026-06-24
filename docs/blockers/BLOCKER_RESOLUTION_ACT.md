<!-- SPDX-License-Identifier: CC-BY-4.0 -->
# Blocker resolution act

| id | blocker | resolution |
|----|---------|-----------|
| B1 | BNCI lock incomplete | **RESOLVED** — `BNCI_LOCK_EXECUTABLE` (runner + aggregation + commands) |
| B2 | Short-epoch specificity risk | **BLOCKED (method)** — `BNCI_BLOCKED_METHOD`; S2-C1 not valid on 501-sample epochs (probe FPR 0.375); not run, not tuned |
| B3 | PyPI deployment | **RESOLVED** — TestPyPI + PyPI Trusted-Publishing workflows + runbook |
| B4 | Truth provenance staleness | **RESOLVED** — CURRENT_TRUTH regenerated; `main_commit` current; pypi+bnci states recorded |
| B5 | CI/artifact verification | **RESOLVED** — release-gate summary; CI conclusions on PR |

`BONN_S2_BRIGHT_LINE_PASSED` preserved. No BNCI claim. No clinical/regulatory/device claim.
BNCI confirmatory was **not executed** (method-blocked); full execution awaits an epoch-length-calibrated,
re-preregistered specificity rule.
