<!-- SPDX-License-Identifier: CC-BY-4.0 -->

# BSFF Claim Registry

This document is the human-readable companion to [`claims.yaml`](claims.yaml).

The registry exists to prevent scientific drift: every important claim must have a bounded
scope, forbidden overclaims, required data, null models, metrics, uncertainty method,
failure condition, reproduction command, evidence artifacts, and status.

## Status levels

| Status | Meaning |
|---|---|
| `unverified` | Registered but not yet supported by executable evidence. |
| `internally_verified` | Verified by committed tests, artifacts, or internal reproduction. |
| `externally_reproduced` | Reproduced by an independent reviewer using only public materials. |
| `peer_reviewed` | Accepted by a peer-reviewed software or scientific venue. |

## Current canonical claims

### BSFF-CLAIM-001 — bounded falsification semantics

BSFF adjudicates bounded BCI/EEG signal claims by attempting falsification under stated
attacks and emitting one of the supported verdict states.

This claim is explicitly not a clinical, regulatory, therapeutic, or universal BCI claim.

### BSFF-CLAIM-002 — Bonn S2 internal evidence

The committed Bonn S2 bright-line evidence is internally hash-backed and reports robust
specificity under the declared release evidence package.

This claim is not external replication and does not imply BNCI execution.

### BSFF-CLAIM-003 — out-of-scope quarantine

BSFF quarantines unsupported clinical, regulatory, therapeutic, or universal authority
language instead of converting it into a positive scientific conclusion.

### BSFF-CLAIM-004 — rank-boundary honesty

BSFF is not yet R6/R7. External hostile reproduction, multi-dataset replication, and a
stable v1.0 API are still required before those labels become justified.

## Enforcement intent

The first enforcement layer is intentionally small and CI-friendly:

```bash
pytest tests/test_claim_registry.py
```

Future hardening should bind README and paper prose directly to claim IDs and fail CI when
new scientific claims are introduced without registry coverage.
