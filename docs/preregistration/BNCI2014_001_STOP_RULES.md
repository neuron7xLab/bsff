<!-- SPDX-License-Identifier: CC-BY-4.0 -->
# BNCI2014-001 preregistration — stop rules

**Status:** scaffold.

## Hard stops (fail-closed)
- `FAIL_DOWNLOAD`: canonical data unavailable / hash mismatch → STOP, do not substitute mirrors.
- `BLOCKED_API`: instrument/API mismatch → STOP, fix scripts to the frozen instrument, not vice versa.
- `BLOCKED_METHOD`: specificity control (AR-null FPR) exceeds 0.05 → STOP, do not report decoding as validated.

## No-go conditions (integrity)
- Do not change alpha or thresholds after seeing results.
- Do not drop subjects/classes that fail.
- Do not retune the instrument per subject.
- Do not claim clinical/medical/regulatory/BCI-product status.

## Allowed terminal states
`BNCI_VALIDATED` · `BNCI_NOT_VALIDATED` · `BLOCKED_DATA` · `BLOCKED_RUNTIME` ·
`BLOCKED_API` · `BLOCKED_METHOD`. No other state.
