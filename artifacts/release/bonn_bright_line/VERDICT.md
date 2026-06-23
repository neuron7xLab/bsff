<!-- SPDX-License-Identifier: CC-BY-4.0 -->
# BSFF — formal verdict (Bonn bright line)

**BRIGHT_LINE_NOT_PASSED** · statistic `sampen_lower_tail_m2_r015_v1` · commit `647aa8b9af24` · 2026-06-23T18:23:30Z

| gate | metric | threshold | result |
|------|--------|-----------|--------|
| G1 power | Set E SURVIVED = 0.96 | ≥ 0.80 | PASS |
| G1 specificity | A not-SURVIVED = 0.86 | ≥ 0.80 | PASS |
| G1 specificity | B not-SURVIVED = 0.91 | ≥ 0.80 | PASS |
| G2 specificity | combined AR FPR = 0.065 | ≤ 0.05 | FAIL |

**BRIGHT_LINE_PASSED = False** → chain to BNCI2014-001 is **BLOCKED**.

## Proven / refuted / unsupported / forbidden
- **proven:** the executed G1/G2 metrics above (reproducible via `REPRODUCE.md`).
- **refuted (preserved):** `lagged_quadratic` statistic — ~20% Set-E power (insufficient).
- **unsupported:** any nonlinearity claim on data/statistics not in this run.
- **forbidden (never claimed):** no clinical diagnosis, no medical use, no regulatory validation, no final proof of brain nonlinear dynamics, no universal BCI benchmark authority.
