<!-- SPDX-License-Identifier: CC-BY-4.0 -->

# Surrogate engine failure-mode catalog

A falsification engine is only trustworthy if its own failure modes are
enumerated and gated. This catalog lists the adversarial inputs the engine is
contractually required to handle, the required behaviour, and where it is
enforced.

| # | Input class | Required behaviour | Enforced by |
|---|---|---|---|
| F1 | `NaN` anywhere in signal | **Reject** — `ValueError("...finite...")` | `surrogate_engine._as_2d`; `tests/test_surrogate_chaos.py` |
| F2 | `+Inf` / `-Inf` in signal | **Reject** — `ValueError` | same |
| F3 | Fewer than 16 samples | **Reject** — `ValueError("...16...")` | `miaaft_surrogate`; chaos tests |
| F4 | Non-convergence within budget | **Declare** — `converged=False`, warn / fallback / raise | `tests/test_surrogate_fallback.py` |
| F5 | Singular channel covariance (duplicate channels) | **Survive** — Cholesky jitter keeps output finite | `var_phase_randomized_surrogate`; chaos tests |
| F6 | Zero-variance / constant channel | **Survive** — finite output, no division blow-up | chaos tests |
| F7 | Arbitrary finite input | **Preserve** per-channel marginal bit-exactly | `tests/test_surrogate_cross_validation.py` |
| F8 | Repeated runs, fixed seed | **Deterministic** — identical output | chaos tests |

## Rationale

The cardinal sin for this engine is *fail-open*: silently emitting a surrogate
computed from `NaN`/`Inf` data. Such a surrogate yields a p-value that looks
decisive but is meaningless, laundering garbage into a verdict. Every non-finite
path is therefore gated closed (F1–F2). Degenerate-but-finite inputs (F5–F6) are
survived rather than rejected, because real EEG routinely contains flat or
collinear channels that are not themselves errors.

The exact invariant (F7) is gated at machine epsilon; the statistical invariants
(ensemble covariance, amplitude spectrum) are gated at empirically measured
tolerances by `tools/cross_validate_surrogate.py`, never at a fabricated
precision that a stochastic surrogate could not meet.
