<!-- SPDX-License-Identifier: CC-BY-4.0 -->
# BSFF risk register (NIST AI RMF framing)

Each risk has a fail-closed control and an enforcing gate. A verdict is never accepted while
an open risk's control is bypassed.

| id | risk | control (fail-closed) | enforcing gate |
|----|------|-----------------------|----------------|
| R1 | false-positive instability | seed-averaged FPR + Wilson CI-upper gate | `validate_statistical_claims.py`, S3 |
| R2 | favorable-seed pass | robust gate = CI-upper ≤ 0.05 (not point estimate) | `validate_statistical_claims.py` |
| R3 | null-model researcher DOF | multi-null robustness (AR/IAAFT/phase-rand) | `MULTI_NULL_ROBUSTNESS_PROTOCOL.md` |
| R4 | epoch-length transfer failure | method-validity gate; BNCI BLOCKED_METHOD | `METHOD_VALIDITY.json`, lock audit |
| R5 | stale CURRENT_TRUTH | regenerate + main_commit; sync gate | `generate_current_truth.py --check` |
| R6 | overclaim in README/docs | forbidden + statistical-claims scanners | `validate_forbidden_claims.py`, `validate_statistical_claims.py` |
| R7 | dataset substitution | manifest + per-file SHA256; raw not tracked | `evidence verify`, DATA_POLICY |
| R8 | raw-rank shortcut | verdict via convergence-gated test, not raw | `test_statistics_sampen.py` |
| R9 | nonconverged surrogate | >10% nonconverged → UNSUPPORTED | `statistics_sampen.py` |
| R10 | CI green without scientific validity | robustness state must be present + honest | `validate_statistical_claims.py` |

Current open/red risks: **R1, R2** (G2 specificity not robust — see CURRENT_TRUTH), **R3** (multi-null
not yet run), **R4** (BNCI method-blocked). The canonical state reflects these; no claim exceeds them.
