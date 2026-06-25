<!-- SPDX-License-Identifier: CC-BY-4.0 -->
# Hostile-review checklist

Run each; the repo must withstand all without the author.

- [ ] `bsff evidence verify` → state PASS, canonical state shown.
- [ ] `python tools/validate_statistical_claims.py` → PASS (no point-estimate-as-pass).
- [ ] `python tools/validate_forbidden_claims.py` → PASS (no clinical/over-claim).
- [ ] `sha256sum -c artifacts/release/bonn_bright_line/HASHES.sha256` → all OK.
- [ ] `CURRENT_TRUTH.latest_validation_state` is `BONN_NOMINAL_S2_PASS_BUT_G2_NOT_ROBUST` (not an unqualified pass).
- [ ] `robust_gate_passed` is `false` while `s2_wilson_ci_upper` (0.056) > 0.05.
- [ ] No doc headlines a robust pass while `robust_gate_passed != true`.
- [ ] `git ls-files | grep bonn_data` is empty (no raw data).
- [ ] Falsification artifacts present: `S2_FALSIFICATION_REPORT.json`, `S2_SPECIFICITY_CALIBRATION.json`.
- [ ] BNCI is `BNCI_BLOCKED_METHOD`; replication `NOT_DONE`; no claim beyond.

See `docs/ADVERSARIAL_REVIEW.md`, `docs/reviewer_packet/KNOWN_FAILURES.md`.
