<!-- SPDX-License-Identifier: CC-BY-4.0 -->
# Forbidden claims

Enforced by `tools/validate_forbidden_claims.py` (CI). These are never asserted by BSFF.

## Forbidden forever
- clinical diagnosis; clinically proven/validated/approved
- medical decision support; medical device/use
- seizure-detection product/device
- regulatory validation / regulatory-grade / FDA
- universal BCI (benchmark) authority
- proof of brain nonlinear dynamics

## State-contingent (forbidden until the artifact exists)
- **"BNCI validated"** — allowed only if `bnci_execution_state == BNCI_CONFIRMATORY_PASSED`.
- **"multi-dataset / cross-dataset validated / replicated"** — allowed only if replication
  `CONFIRMATORY_VERDICT.json` artifacts exist under `artifacts/replication/`.

Report: `artifacts/release/CLAIM_SAFETY_REPORT.json`. Current canonical state:
`artifacts/release/CURRENT_TRUTH.json`.
