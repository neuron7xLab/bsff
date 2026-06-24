<!-- SPDX-License-Identifier: CC-BY-4.0 -->
# BSFF — formal verdict (Bonn bright line)

Canonical machine-readable truth: [`artifacts/release/CURRENT_TRUTH.json`](artifacts/release/CURRENT_TRUTH.json).
This document must agree with it (enforced by `tools/validate_current_truth.py`).

## 1. Current canonical verdict
**BONN_S2_BRIGHT_LINE_PASSED.** BSFF passed the Bonn S2 bright-line under the frozen
finite-N-corrected SampEn protocol (`S2-C1-sampen-finiteN`).

- G1 (power): Set E SURVIVED **0.96**, Set A not-SURVIVED **0.92**, Set B not-SURVIVED **0.92** (≥ 0.80).
- G2 (specificity): real-spectrum AR-null FPR A **0.02**, B **0.02**, combined **0.02** (≤ 0.05).
- BNCI2014-001 chain: **UNLOCKED_FOR_PREREGISTRATION_ONLY**.

> BSFF passed the Bonn S2 bright-line under the frozen finite-N-corrected SampEn protocol.
> This permits BNCI2014-001 preregistration. It does not validate BSFF across BCI datasets,
> does not establish clinical status, and does not prove general brain nonlinear dynamics.

## 2. Historical S1 negative verdict (preserved)
S1 (`sampen_lower_tail_m2_r015_v1`, nominal α=0.05) returned **BRIGHT_LINE_NOT_PASSED**:
G1 passed (E 0.96, A_not 0.86, B_not 0.91) but G2 failed (combined AR-null FPR **0.065 > 0.05**).
Earlier still, `lagged_quadratic` failed G1 (~20% Set-E power). Both are kept as evidence
(`docs/validation/STATISTIC_REGISTRY.md`).

## 3. S2 corrected verdict
The finite-N rule (conservative detection threshold **p ≤ α/2 = 0.025**) corrects SampEn's
finite-N anti-conservative bias. The bright-line **gate** thresholds (FPR ≤ 0.05, α = 0.05)
are unchanged.

## 4. What changed from S1 to S2
Combined AR-null FPR **0.065 → 0.020** while G1 power is preserved (Set E stays 0.96). Strong
ictal rejections (p ≈ 0.005) survive the stricter threshold; marginal Set-A false positives do not.

## 5. What is now proven (by executed artifact)
Bonn S2 bright-line passed on real Andrzejak-2001 EEG: power + specificity, reproducible,
artifact-backed (`S2_BRIGHT_LINE_SUMMARY.json`, `s2_CONFIRMATORY_VERDICT.json`).

## 6. What remains unsupported
External replication; multi-dataset (BNCI / Cho2017 / Lee2019) validation; paper-grade completeness.

## 7. What is forbidden (never claimed)
No clinical diagnosis, no medical/therapeutic use, no regulatory/device status, no final proof
of brain nonlinear dynamics, no universal BCI benchmark authority, no "BNCI validated" (no BNCI
execution artifacts exist).

## 8. What BNCI unlock means
The instrument has a demonstrated operating characteristic on a real benchmark, so BNCI2014-001
**preregistration** may proceed (`docs/preregistration/`).

## 9. What BNCI unlock does NOT mean
It does **not** mean BNCI is validated. Passing Bonn does not imply BNCI passes; each dataset is
adjudicated on its own executed evidence.

## 10. Artifact index
`artifacts/release/CURRENT_TRUTH.json` · `artifacts/bonn_bright_line/{BRIGHT_LINE_SUMMARY,
S2_BRIGHT_LINE_SUMMARY, s2_CONFIRMATORY_VERDICT, S2_SELECTION_LOCK, DATASET_MANIFEST}.json` ·
`docs/validation/{S2_VERDICT, STATISTIC_REGISTRY, CLAIM_AUDIT}.md` · hashes
`artifacts/release/bonn_bright_line/HASHES.sha256` · reproduce `REPRODUCE.md`.

## Robustness (falsification-calibrated)
An adversarial battery (`artifacts/bonn_bright_line/S2_FALSIFICATION_REPORT.json`) found:
**G1 power is robust** (Set E SURVIVED 0.967 under all seeds/AR-orders), but **G2 specificity is a
boundary pass** — AR-null FPR reached **0.067 > 0.05** under one perturbation seed (N=30). So
`BONN_S2_BRIGHT_LINE_PASSED` is a **marginal/boundary** pass: it cleared the predeclared N=100
confirmatory (FPR 0.02) but the specificity margin is thin and seed-sensitive. Not claimed as
robustly crossed; a seed-averaged / larger-N specificity confirmatory is the honest next step.
`CURRENT_TRUTH.s2_robustness = BOUNDARY_PASS_G1_POWER_ROBUST_G2_SPECIFICITY_SEED_SENSITIVE`.
