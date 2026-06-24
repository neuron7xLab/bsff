<!-- SPDX-License-Identifier: CC-BY-4.0 -->
# Bonn bright-line STATUS

**S1 (historical) snapshot.** Current canonical state is `BONN_S2_BRIGHT_LINE_PASSED` —
see [`artifacts/release/CURRENT_TRUTH.json`](../../artifacts/release/CURRENT_TRUTH.json)
and [`FORMAL_VERDICT.md`](../../FORMAL_VERDICT.md). The lines below record the S1 result only.

- Bonn bright line (S1, historical): **BRIGHT_LINE_NOT_PASSED** (commit `54942349d1d2`).
- G1: E=0.96, A_not=0.86, B_not=0.91 (≥0.80).
- G2: AR FPR A=0.08, B=0.05, combined=0.065 (≤0.05), G2_PASS=False.
- BNCI2014-001 chain at S1: **BLOCKED** (historical; UNLOCKED after S2).
- Evidence: `artifacts/bonn_bright_line/BRIGHT_LINE_SUMMARY.json`, `docs/validation/BRIGHT_LINE_VERDICT.md`.
- Reproduce: `REPRODUCE.md`. Tests: `artifacts/release/TESTS.json`.
