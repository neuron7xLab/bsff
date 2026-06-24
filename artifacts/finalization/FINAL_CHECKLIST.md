<!-- SPDX-License-Identifier: CC-BY-4.0 -->
# BSFF v0.4.0 — final checklist

Final state: **REVIEWER_GRADE_PUBLIC_RESEARCH_SOFTWARE** · overall **PASS** · commit `f3fcd3697ed5`.

| seal | result |
|------|--------|
| Truth provenance (main_commit == HEAD at regen) | PASS |
| validate_current_truth / forbidden_claims / artifact_schema | PASS |
| bsff selftest / evidence verify / reproduce bonn-s2 | PASS |
| build (wheel + sdist) / twine check | PASS |
| docker build / docker selftest (volume) | PASS |
| docker evidence verify | needs git in image (host-only); non-blocking |

**Validated:** Bonn S2 bright-line. **Not validated:** BNCI, Cho2017, Lee2019, multi-dataset replication.
**Forbidden (CI-enforced):** clinical · medical · regulatory · universal BCI authority · final proof of
brain nonlinear dynamics · "BNCI validated"/"replicated" without artifacts.

Ready as **public falsification software**; **not** multi-dataset scientific validation.
