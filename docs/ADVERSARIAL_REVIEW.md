<!-- SPDX-License-Identifier: CC-BY-4.0 -->
# Adversarial review playbook

This page is for a **hostile** reviewer who assumes the result is fake and tries to break it.
Each attack names the check that already defends against it, so the reviewer can confirm the
defense is real rather than take the author's word.

## 1. "The hashes don't match the artifacts."
`sha256sum -c artifacts/release/bonn_bright_line/HASHES.sha256` and `bsff evidence verify`
(check `hash_verification`). Any tampered artifact fails closed.

## 2. "They moved the threshold after seeing results."
Thresholds are pre-declared and committed **before** each confirmatory:
`docs/validation/BONN_BRIGHT_LINE_PROTOCOL.md` and `S2_SPECIFICITY_PROTOCOL.md`. The S2
selection lock (`S2_SELECTION_LOCK.json`) was committed *before* the confirmatory ran — see
its git history. alpha = 0.05 is fixed; `tools/...` never mutate it.

## 3. "They dropped Set A because it failed."
Set A is a required negative-sanity control in G1 and a required FPR control in G2. The
verdict logic (`tests/bonn_bright_line/test_s2_no_threshold_hacking.py`,
`test_s2_g1_g2_logic.py`) proves a G2 failure blocks the bright line regardless of G1.

## 4. "α/2 is just threshold gaming."
The **gate** threshold (FPR ≤ 0.05, α = 0.05) is unchanged. S2-C1 uses a more conservative
*detection* threshold (p ≤ 0.025) — a stricter test, registered as a candidate *before* the
run. A p ≤ 0.025 test yields ~2.5% FPR by construction; that it is below 0.05 is the point,
not a trick. See `STATISTIC_REGISTRY.md` and `FORMAL_VERDICT.md` §3.

## 5. "The raw-rank-order shortcut inflates power."
The verdict comes from the convergence-gated surrogate test, not a raw rank-order rejection;
the raw rejection is recorded separately for transparency. A non-converged null → UNSUPPORTED
(`test_statistics_sampen.py::test_nonconverged_null_is_unsupported`).

## 6. "Non-converged surrogates were counted as passes."
MIAAFT convergence is gated; > 10% non-converged → UNSUPPORTED, never SURVIVED.

## 7. "The docs say PASSED but the artifacts say otherwise (stale claims)."
`tools/validate_current_truth.py` (CI gate) fails if any public surface contradicts
`CURRENT_TRUTH.json`. Run `bsff evidence verify` → `docs_truth_coherent`.

## 8. "They swapped in a different dataset (UCI/Kaggle)."
`DATASET_MANIFEST.json` pins UPF NTSA provenance + per-file SHA256; `docs/DATA_POLICY.md`
forbids the UCI-178 / Kaggle derivatives; `bsff evidence verify` checks raw data is not tracked.

## 9. "It only works on the author's machine / hidden state."
`docs/QUICKSTART.md`: clone → install → `bsff evidence verify` → `bsff reproduce bonn-s2`.
No private paths; the CLI is repo-aware and emits `BLOCKED_RUNTIME` if the surface is absent.

## 10. "BNCI is being claimed as validated."
It is not. `BNCI_chain_state = UNLOCKED_FOR_PREREGISTRATION_ONLY`; `docs/preregistration/` is a
frozen plan with no executed BNCI artifacts. The truth gate forbids a "BNCI validated" claim.

## What is genuinely open (not defended, by design)
External replication, multi-dataset generalization, and paper-grade review are **UNSUPPORTED**
in `CURRENT_TRUTH.json` — claimed by no one. A hostile reviewer should attack the *scope of the
claim*, which is deliberately narrow: one benchmark, one instrument, reproducible.
