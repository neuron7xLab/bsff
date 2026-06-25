<!-- SPDX-License-Identifier: CC-BY-4.0 -->
# Claim audit

Every claim is classified into exactly one status:
**PROVEN_BY_ARTIFACT** · **REFUTED_BY_ARTIFACT** · **UNSUPPORTED** · **UNVERIFIED** · **FORBIDDEN**.

## PROVEN_BY_ARTIFACT
| claim | evidence |
|-------|----------|
| Bonn dataset acquired and hashed (UPF NTSA, not UCI 178) | `artifacts/bonn_bright_line/DATASET_MANIFEST.json` |
| `lagged_quadratic` had insufficient Set-E power (~20%) | `STATISTIC_REGISTRY.md` S0; `bonn_bright_line_EXPLORATORY.json` |
| SampEn improved G1 positive-control power on Set E (0.96) | `bonn_CONFIRMATORY_VERDICT.json`; `BRIGHT_LINE_SUMMARY.json` |
| SampEn passed G1 thresholds on A (0.86), B (0.91), E (0.96) | `bonn_CONFIRMATORY_VERDICT.json` |
| G2 AR-null specificity guard FAILED (combined FPR 0.065 > 0.05) | `ar_negative_CONFIRMATORY_{A,B}.json` |
| The bright line did NOT pass | `BRIGHT_LINE_SUMMARY.json` (`final_state=BRIGHT_LINE_NOT_PASSED`) |
| BNCI2014-001 chain was BLOCKED at S1 (historical; UNLOCKED after S2 — see S2 update below) | `BRIGHT_LINE_SUMMARY.json` |
| SampEn(chaos) < SampEn(noise); lower-tail SURVIVES henon, REFUTES white | `tests/bonn_bright_line/test_statistics_sampen.py` |
| Non-converged MIAAFT → UNSUPPORTED (fail-closed) | same test file |

## REFUTED_BY_ARTIFACT
| claim | evidence |
|-------|----------|
| The current SampEn config is sufficient to pass the full G1+G2 bright line | combined FPR 0.065 > 0.05 |
| Bright-line validation is complete | `final_state=BRIGHT_LINE_NOT_PASSED` |

## UNSUPPORTED
- BSFF is generally validated across all BCI datasets.
- BSFF is externally replicated / has independent third-party confirmation.
- BSFF is paper-grade complete.

## UNVERIFIED
- Any prior agent summary not backed by a Tier-1 artifact or Tier-2 document.

## FORBIDDEN (never asserted; enforced by `release_check.py`)
clinical diagnosis · medical/therapeutic use · regulatory or device-grade status ·
seizure-detection product · final proof of brain nonlinear dynamics · universal BCI truth oracle.

## S2 update (PROVEN_BY_ARTIFACT)
| claim | evidence |
|-------|----------|
| A finite-N-corrected SampEn (p≤α/2) passes G2 specificity (combined FPR 0.020 ≤ 0.05) | `s2_CONFIRMATORY_VERDICT.json` |
| The same candidate preserves G1 (E 0.96, A_not 0.92, B_not 0.92 ≥ 0.80) | `s2_CONFIRMATORY_VERDICT.json` |
| S2 bright line PASSED under the frozen protocol; BNCI2014-001 chain UNLOCKED | `S2_BRIGHT_LINE_SUMMARY.json` |

Still **UNSUPPORTED**: external replication, multi-dataset generalization, paper-grade completeness.
Still **FORBIDDEN**: clinical/medical/regulatory/device claims; final proof of brain dynamics; universal BCI authority.

## BNCI execution (recorded)
**No BNCI claim exists — BNCI is preregistration-only and was not executed.**

| claim | status | evidence |
|-------|--------|----------|
| BNCI2014-001 confirmatory was attempted under granted authorization | PROVEN_BY_ARTIFACT | `artifacts/bnci2014_001/LOCK_AUDIT.json` |
| BNCI data is acquirable (subject 1, 250 Hz, 22 EEG) — not the blocker | PROVEN_BY_ARTIFACT | `artifacts/bnci2014_001/DATA_SMOKE_SUBJECT1.json` |
| BNCI confirmatory completed / passed | REFUTED_BY_ARTIFACT | not executed — `BNCI_BLOCKED_LOCK_INCOMPLETE` (`BNCI_SUMMARY.json`) |
| The locked command implements the locked method | REFUTED_BY_ARTIFACT | run_experiment.py = CSP decoding, not sampen/MIAAFT/AR-null (`LOCK_AUDIT.json`) |

## Replication + method-repair (roadmap, recorded)
| claim | status | evidence |
|-------|--------|----------|
| Multi-dataset replication (Cho2017/Lee2019) is done | REFUTED_BY_ARTIFACT | NOT_DONE — only preregistration scaffolds (`artifacts/replication/*/LOCK.json`) |
| BNCI method repair has passed its short-epoch check | UNSUPPORTED (not yet) | `METHOD_REPAIR_LOCK.json` = PREDECLARED_NOT_VALIDATED; short-epoch validation INCONCLUSIVE for narrowband |
| Forbidden claims are enforced in CI | PROVEN_BY_ARTIFACT | `tools/validate_forbidden_claims.py` (CI) + `CLAIM_SAFETY_REPORT.json` |

## S2 falsification (calibrated)
| claim | status | evidence |
|-------|--------|----------|
| S2 G1 power is robust to seed | PROVEN_BY_ARTIFACT | Set E SURVIVED 0.967 all seeds (`S2_FALSIFICATION_REPORT.json`) |
| S2 G2 specificity is robustly below 0.05 | REFUTED_BY_ARTIFACT | seed_base=7 -> AR-null FPR 0.067 > 0.05; margin thin/seed-sensitive |
| S2 bright line is a boundary/marginal pass (not robustly crossed) | PROVEN_BY_ARTIFACT | falsification battery; calibrated claim |

## S2 specificity calibration (decisive)
| claim | status | evidence |
|-------|--------|----------|
| S2 G2 specificity is robustly below 0.05 | REFUTED_BY_ARTIFACT | seed-avg FPR 0.0354, Wilson 95% CI [0.022, 0.056] crosses 0.05; 2/6 seeds >0.05 (`S2_SPECIFICITY_CALIBRATION.json`) |
| Bonn S2 bright line is robustly crossed | REFUTED_BY_ARTIFACT | marginal/favorable-seed pass only; G2 not robust |
| Bonn S2 G1 power is robust | PROVEN_BY_ARTIFACT | Set E SURVIVED 0.96-0.967 across all seeds |

## Canonical-state honesty (PI-grade)
| claim | status | evidence |
|-------|--------|----------|
| Bonn S2 robust bright-line passed | REFUTED_BY_ARTIFACT | robust_gate_passed=false; CI upper 0.056 > 0.05 (`CURRENT_TRUTH.json`) |
| Bonn S2 nominal single-seed pass exists | PROVEN_BY_ARTIFACT | predeclared confirmatory (FPR 0.02), `bonn_s2_nominal_state=PASSED_SINGLE_SEED` |
| "Bonn validated" without a robustness qualifier | FORBIDDEN | enforced by `tools/validate_statistical_claims.py` (CI) |

## S3 seed-averaged confirmatory (reproduced fact)
| claim | status | evidence |
|-------|--------|----------|
| Seed-averaged AR-null specificity is robust (FPR 0.028, Wilson CI [0.019,0.040] upper ≤ 0.05) | PROVEN_BY_ARTIFACT | `S3_CONFIRMATORY_VERDICT.json` (N=1000, 10 seeds, frozen lock, re-run reproduced per-seed counts byte-for-byte) |
| The S2 not-robust calibration is superseded by the larger pre-registered S3 | PROVEN_BY_ARTIFACT | N=480 (0.0354) vs N=1000 (0.028); seed-set/N sensitive near boundary; larger test passes |
| Bonn S2 is robust across null models | UNSUPPORTED (not yet) | multi-null (IAAFT/phase-randomized) NOT_DONE; `multi_null_robustness_state=NOT_DONE` |
| Bonn S2 bright line is fully robustly passed | UNVERIFIED | requires multi-null; `robust_gate_passed=null` |

## Multi-null robustness (final gate — PASSED)
| claim | status | evidence |
|-------|--------|----------|
| Specificity is robust across null models (AR/IAAFT/phase-randomized) | PROVEN_BY_ARTIFACT | `MULTI_NULL_ROBUSTNESS.json`: AR 0.026 [0.018,0.038], IAAFT 0.032 [0.023,0.045], phaserand 0.034 [0.024,0.047]; all CI-upper ≤ 0.05 |
| Bonn S2 bright line is robustly passed (seed AND null-model) | PROVEN_BY_ARTIFACT | S3 (seed) + multi-null; `robust_gate_passed=true`, `BONN_S2_BRIGHT_LINE_ROBUSTLY_PASSED` |
| Robustness was earned through falsification, not assumed | PROVEN_BY_ARTIFACT | calibration flagged not-robust → larger pre-registered S3 + multi-null confirmed |
