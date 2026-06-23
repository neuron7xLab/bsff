<!-- SPDX-License-Identifier: CC-BY-4.0 -->
# BSFF — formal verdict (Bonn bright line)

**BRIGHT_LINE_NOT_PASSED** · statistic `sampen_lower_tail_m2_r015_v1` · commit `a867bd4f4d5b` · 2026-06-23T20:00:22Z

| gate | metric | threshold | result |
|------|--------|-----------|--------|
| G1 power | Set E SURVIVED = 0.96 | ≥ 0.80 | PASS |
| G1 specificity | A not-SURVIVED = 0.86 | ≥ 0.80 | PASS |
| G1 specificity | B not-SURVIVED = 0.91 | ≥ 0.80 | PASS |
| G2 specificity | AR FPR A=0.08, B=0.05, combined=0.065 | ≤ 0.05 | FAIL |

**BRIGHT_LINE_PASSED = False** → chain to BNCI2014-001 is **BLOCKED**.

## Proven / refuted / unsupported / forbidden
- **proven:** the executed G1/G2 metrics above (reproducible via `REPRODUCE.md`).
- **refuted (preserved):** `lagged_quadratic` statistic — ~20% Set-E power (insufficient).
- **unsupported:** any nonlinearity claim on data/statistics not in this run.
- **forbidden (never claimed):** no clinical diagnosis, no medical use, no regulatory validation, no final proof of brain nonlinear dynamics, no universal BCI benchmark authority.

## Methodological interpretation
SampEn is a **regularity** statistic. Ictal EEG can be more regular than healthy or noisy
segments, so Set E detection (G1) is plausible. But regularity also arises in spectrum-matched
**linear** processes — exactly what **G2** (the AR-null specificity guard) exists to catch.
Since the combined AR-null FPR (0.065) exceeds alpha (0.05), the current
statistic is **sensitive but not sufficiently specific**, and is not acceptable as a complete
bright-line statistic.

> This result is scientifically useful **because it prevents an unsupported success claim.**

## Reproduction
See `REPRODUCE.md` (copy-pasteable, relative paths). Verify hashes against
`artifacts/release/bonn_bright_line/HASHES.sha256`.

## Next valid research step
Open the **S2** specificity-method branch (`docs/validation/NEXT_METHOD_CONTRACT_S2.md`).
**Do not** proceed to BNCI2014-001 until G2 passes under the same pre-declared protocol.
