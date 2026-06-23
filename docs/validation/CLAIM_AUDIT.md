<!-- SPDX-License-Identifier: CC-BY-4.0 -->
# Claim audit

Every claim maps to evidence and a status. Statuses: **proven** (executed artifact),
**refuted** (executed artifact shows false), **unsupported** (no evidence either way),
**forbidden** (out of scope; never asserted).

| # | claim | status | evidence |
|---|-------|--------|----------|
| 1 | `lagged_quadratic` detects Bonn ictal nonlinearity | **refuted** | ~20% Set-E power; `artifacts/bonn_bright_line/bonn_bright_line_EXPLORATORY.json`, STATISTIC_REGISTRY.md (S0) |
| 2 | SampEn(chaos) < SampEn(noise) | **proven** | `tests/bonn_bright_line/test_statistics_sampen.py` |
| 3 | SampEn lower-tail SURVIVES henon, REFUTES white noise | **proven** | same test file |
| 4 | Non-converged MIAAFT → UNSUPPORTED (fail-closed) | **proven** | same test file |
| 5 | Canonical Bonn data (UPF NTSA, not UCI 178) with per-file SHA256 | **proven** | `DATASET_MANIFEST.json` |
| 6 | G1 Set-E power ≥ 0.80 (SampEn) | see `BRIGHT_LINE_SUMMARY.json` | confirmatory bundle |
| 7 | G1 Set-A/B not-survived ≥ 0.80 | see `BRIGHT_LINE_SUMMARY.json` | confirmatory bundle |
| 8 | G2 real-spectrum AR FPR ≤ 0.05 | see `BRIGHT_LINE_SUMMARY.json` | confirmatory bundles A/B |
| 9 | BRIGHT_LINE_PASSED | see `BRIGHT_LINE_SUMMARY.json` | aggregator over 6–8 |
| — | clinical / medical / regulatory / final brain-dynamics proof / universal BCI authority | **forbidden** | never asserted; see release_check FORBIDDEN list |

Claims 6–9 resolve to the executed confirmatory verdict; this table does not pre-judge them.
