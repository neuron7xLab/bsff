<!-- SPDX-License-Identifier: CC-BY-4.0 -->
<!-- Copyright (c) 2026 Yaroslav Vasylenko / neuron7xLab -->

# Invariants — the executable constitution

A falsifier that only *claims* to be deterministic, fail-closed, and honest is
just one more assertion. BSFF encodes its axioms as invariants that CI enforces
on every commit (`tests/test_invariants.py`). A principle you cannot break by
accident is a guarantee; one you can is a slogan.

| # | invariant | statement | enforced by |
|---|-----------|-----------|-------------|
| INV-1 | **Determinism** | the same `(input, seed)` yields a byte-identical verdict | run twice, assert equal across `evaluate_claim`, `transfer_entropy_test`, `gaussian_transfer_entropy`, `adjudicate`, `classify` |
| INV-2 | **No promotion to true** | no code path emits `TRUE`/`PROVEN`; the ceiling is *survived falsification under stated conditions* | scan every disposition over a claim battery + dataset verdicts |
| INV-3 | **Fail-closed monotonicity** | degraded evidence can only **demote** a verdict, never upgrade it (leakage → `REFUTED`; mis-specified null → `UNSUPPORTED`; IID null → not `SURVIVED`) | leakage-flag and null-signal cases |
| INV-4 | **Anchor** | a quote absent from its source is **always** quarantined, regardless of how empirical, normative, or definitional it reads | adjudicate absent quotes across tiers |
| INV-5 | **Provenance closure** | every report's `artifact_sha256` recomputes from its own content | recompute `stable_sha256` for `adjudicate` + `adjudicate_batch` |
| INV-6 | **Raw-signal guard** | a non-signal (labels, features, accuracy matrices) is **refused**, not adjudicated | `load_series` on a label array must raise |

## Why this is the architecture, not decoration

Frontier systems do not assert their safety properties; they make them
checkable. These six invariants are the smallest set whose conjunction defines
what BSFF *is*: a deterministic, provenance-bound, fail-closed instrument that
sorts claims by the scrutiny they admit and never declares truth. Each is a
first-principle, not a feature:

- **Determinism** is the precondition for reproducibility — without it, a
  "verdict" is a sample, not a measurement.
- **No-true** is the epistemic floor — falsification can refute or fail to
  refute, never confirm.
- **Fail-closed monotonicity** is the value function — when uncertain, the
  system moves toward *less* claim, never more.
- **Anchor / provenance / raw-guard** are the integrity boundary — the verdict
  is tied to real, unaltered input, or there is no verdict.

If a future change breaks any of these, CI fails. That is the whole point: the
constitution is not in a document, it is in the test runner.
