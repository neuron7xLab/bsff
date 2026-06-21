<!-- SPDX-License-Identifier: CC-BY-4.0 -->
<!-- Copyright (c) 2026 Yaroslav Vasylenko / neuron7xLab -->

# Validation tiers — what is proven, and at what strength

Every validation claim in BSFF carries a tier. The tier is the honest ceiling of
what the evidence supports; nothing may be described above its tier (the truth
contract forbids the phrases that would).

| tier | meaning | status in this repo | gating |
|------|---------|---------------------|--------|
| **0 — unit correctness** | functions do what their tests say | enforced | required every PR |
| **1 — synthetic ground truth** | controls + operating characteristic on known-label fixtures | enforced (controls 5/5, OC at 60 seeds) | required every PR |
| **2 — independent numpy reference** | surrogate fidelity vs an independent implementation | enforced (marginal exact, spectrum/cov within tolerance) | required every PR |
| **3 — external TISEAN binary parity** | match against the TISEAN reference C package | **NOT MET** — binary absent | scheduled/manual; artifact verdict required |
| **4 — public real-EEG reproduction** | a published dataset re-run | **PARTIAL** — n=9 PhysioNet LOSO (single dataset, weak within-subject); not shipped in the package | nightly/weekly, not in wheel |
| **5 — independent third-party replication** | someone else reproduces it | **NOT MET** | external badge only after real replication |

## Rules

- Tiers **0–2** are required for every PR (the CI `test` + `slow-tests` jobs).
- Tier **3** is not claimed: the TISEAN gate is structural only while the binary
  is absent; it is `NEEDS_EXTERNAL_CHECK` in `CLAIM_AUDIT.md`, never "passed".
- Tier **4** is the n=9 PhysioNet finding (`docs/FINDING_N9.md`) — explicitly a
  measurement on one dataset family, not "real EEG validation complete".
- Tier **5** does not exist yet and no badge claims it.

## Forbidden cross-tier language

Tier 2 is **not** "external validation". A synthetic BIDS fixture is **not** "real
EEG validation". The TISEAN gate is **not** "passed" when the binary is absent.
These are enforced by `tools/validate_truth_contract.py`; this document is the
human-readable map of the same boundary, and the decision gate
(`DECISION.md`) keeps V6 (tiers 3–5) open precisely because of it.
