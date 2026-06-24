<!-- SPDX-License-Identifier: CC-BY-4.0 -->
# Verdict semantics

BSFF emits **bounded** verdicts. A verdict is a statement about *whether a claim survived a
falsification attempt under stated attacks* — never a bare "significant" and never a clinical
or regulatory conclusion.

## Per-claim verdicts (one signal/claim)
| verdict | meaning | when |
|---------|---------|------|
| **SURVIVED** | the claim resisted the falsification attempt | the statistic exceeds its convergence-gated surrogate null at the policy threshold, and (under the policy) is corroborated |
| **REFUTED** | the claim did not resist | the statistic is consistent with the null; the surrogates converged |
| **UNSUPPORTED** | no honest verdict possible | the surrogate null did not converge, or evidence is insufficient — **fail-closed**, never silently treated as REFUTED or SURVIVED |

A SURVIVED is *not* proof the claim is true — it means this attack failed to break it. The
worth of a SURVIVED is exactly the strength of the attack (null model + corroboration + controls).

## Benchmark / pipeline states (`bsff evidence`, `bsff benchmark`, `bsff reproduce`)
| state | meaning |
|-------|---------|
| **PASS** | the executed artifacts prove the gate (e.g. G1 power ∧ G2 specificity) |
| **FAIL** | a gate is unmet by the executed artifacts (e.g. combined AR-null FPR > 0.05) |
| **BLOCKED_DATA** | required data is not present; nothing is faked |
| **BLOCKED_RUNTIME** | required repo/runtime surface is absent (not run from a clone) |
| **BLOCKED_API** / **BLOCKED_METHOD** | an interface or method precondition is unmet |

No other state may be emitted. A non-zero exit always accompanies a non-PASS state.

## Bright-line verdicts (the Bonn benchmark)
- `BRIGHT_LINE_NOT_PASSED` (S1, historical): power held, specificity failed (FPR 0.065).
- `BONN_S2_BRIGHT_LINE_PASSED` (current canonical): power ∧ specificity, FPR 0.02 ≤ 0.05.
Canonical machine-readable state: `artifacts/release/CURRENT_TRUTH.json`.

## What a verdict never asserts
Clinical diagnosis · medical/therapeutic use · regulatory or device-grade status · final
proof of brain nonlinear dynamics · universal BCI benchmark authority. These are enumerated
as `forbidden_claims` in CURRENT_TRUTH.json and enforced by `tools/validate_truth_contract.py`.
