<!-- SPDX-License-Identifier: CC-BY-4.0 -->
<!-- Copyright (c) 2026 Yaroslav Vasylenko / neuron7xLab -->

# BSFF methodology

BSFF is a falsification-first instrument for signal claims. It does not try to
*confirm* a claim; it subjects the claim to a fixed sequence of executable
attacks and reports whether the claim survived them. This document describes the
scientific method the engine implements, stage by stage, in the order they run.

The reference implementations are
[`src/bsff/verdict_engine.py`](../src/bsff/verdict_engine.py) (single-claim
engine) and [`src/bsff/pipeline.py`](../src/bsff/pipeline.py) (the composable
pipeline). The two implement identical falsification semantics.

## Design stance

Every claim enters under the hostile assumption that it may be inflated by
leakage, autocorrelation, an underpowered statistic, a broken null model, or
narrative decoration. The pipeline accepts only evidence that survives the
attacks. When evidence is ambiguous, the engine **fails closed**: it emits the
weakest defensible verdict rather than fabricating certainty.

## The pipeline, in order

```
claim spec
   │  schema validation
   ▼
stationarity gate ──▶ leakage detection ──▶ surrogate null ──▶ convergence /
                                                                fidelity gate
                                                                     │
   frequentist rank-order test ──▶ Bayesian corroboration ──▶ deterministic
                                                              verdict
```

### 1. Claim specification

A claim is a `ClaimSpec` (signal type, task type, sampling rate, channel/sample
counts, the statistic to test, surrogate count, `α`, stationarity mode). The
spec is validated before any computation runs; an ill-formed spec aborts rather
than being silently coerced.

### 2. Stationarity gate

Each channel is checked for stationarity (KPSS). Under the default empirical
policy a failure is a **warning** that attaches a caveat ("interpret the
surrogate verdict as preprocessing-sensitive"); under the `strict` policy the
stationarity mode is `fail_closed` and a non-stationary channel halts the run.
The surrogate null assumes a (transformed) stationary linear-Gaussian process,
so a trend silently invalidates it — the gate makes that visible.

### 3. Leakage detection

A block-design temporal-autocorrelation detector inspects the labelling /
block structure. If leakage is flagged the engine **short-circuits**: it returns
`REFUTED` immediately and never runs the surrogate test. A falsifier that can see
the answer through leakage has already failed, and no amount of downstream
statistics can repair that. (BIDS ingestion adds two more leakage guards — hidden
label columns and feature-table columns are refused at load; see
[`REAL_EEG_VALIDATION.md`](REAL_EEG_VALIDATION.md).)

### 4. Surrogate null

The core attack: a rank-order surrogate test against a MIAAFT (multivariate
iterative amplitude-adjusted Fourier-transform) null. Surrogates preserve the
marginal distribution and the (multivariate) power spectrum of the original while
destroying any nonlinear structure, realising the null "the series is a monotonic
nonlinear transform of a linear-Gaussian process". The observed statistic is
ranked against the surrogate distribution to produce a one-sided p-value.

### 5. Convergence / fidelity gate (fail-closed)

Every surrogate's IAAFT convergence and spectral/covariance fidelity is measured
at verdict time; the MIAAFT iteration budget is set by the active policy, not a
fixed constant. If **any** surrogate fails the convergence/fidelity gate the
verdict is demoted to `UNSUPPORTED` — a mis-specified null makes both `SURVIVED`
and `REFUTED` unearned. This gate runs *before* the verdict is read, so an
invalid null can never produce a strong verdict.

### 6. Frequentist test

If the null converged, the rank-order p-value yields a provisional verdict:
`SURVIVED` if `p ≤ α` (rejected the null), otherwise `REFUTED`. This provisional
verdict is **not final** under the empirical policies — it must pass step 7.

### 7. Bayesian corroboration (conjunction gate)

When Bayesian evidence is enabled (the `standard` and `strict` policies), a
frequentist rejection must be corroborated by a JZS effect-size Bayes factor:
`SURVIVED` requires `BF10 ≥ corroboration_min` (default 3, `strict` 10). A
rejection that lacks corroboration is demoted to `UNSUPPORTED`. Symmetrically, a
non-rejection becomes `REFUTED` only if `BF01 > 3` (explicit evidence for the
null), otherwise `UNSUPPORTED`.

This exists because the rank-order p-value is anti-conservative for strongly
autocorrelated linear-Gaussian nulls (finite-N IAAFT bias). The gate is
fail-closed — it only ever demotes. Its measured effect (power held at 1.000,
false-positive rate restored to ≤ α) and full rationale are in
[`FALSE_POSITIVE_CONTROL.md`](FALSE_POSITIVE_CONTROL.md) and
[`OPERATING_CHARACTERISTIC.md`](OPERATING_CHARACTERISTIC.md).

### 8. Deterministic verdict

The engine collapses the stage evidence into exactly one of three verdicts:

| Verdict | Meaning |
|---|---|
| `SURVIVED` | The configured attacks did not break the claim (and, under empirical policy, the rejection was corroborated). |
| `REFUTED` | Leakage or null evidence broke the claim. |
| `UNSUPPORTED` | Evidence is too weak, ambiguous, or rests on an invalid null — the engine refuses to take a side. |

The verdict, its p-value, surrogate range, leakage flags, stage evidence, and all
caveats are serialised to a JSON artifact with a SHA-256 manifest that is
recomputed and verified on load. Same inputs + same seed ⇒ same verdict and same
hash.

## Policies

Three profiles trade speed for rigour. All are fail-closed; they only tighten
gates, never loosen them.

| Policy | Surrogates | Bayesian | Stationarity | Corroboration `BF10` | Use |
|---|---|---|---|---|---|
| `smoke` | 19 | off | warn | — | fast CI guard |
| `standard` | 99 | on | warn | ≥ 3 | release validation |
| `strict` | 999 | on | fail-closed | ≥ 10 | publication-grade |

## Honest boundaries

- The shipped statistics are **linear / spectral**. Nonlinear directed coupling
  (k-NN transfer entropy) and non-time-series designs (two-group, cohort) are out
  of scope and would need their own validated tests.
- A `SURVIVED` verdict means only that the claim was not refuted by the
  configured attacks on the data given — it is **not** proof of a BCI claim, and
  this is **not** regulatory validation.

## See also

- [`FALSIFICATION_PROTOCOL.md`](FALSIFICATION_PROTOCOL.md) — the gate checklist.
- [`FALSE_POSITIVE_CONTROL.md`](FALSE_POSITIVE_CONTROL.md) — the conjunction gate in depth.
- [`OPERATING_CHARACTERISTIC.md`](OPERATING_CHARACTERISTIC.md) — measured power / FPR.
- [`VALIDATION.md`](VALIDATION.md) — the evidence ledger.
- [`DATASETS.md`](DATASETS.md) — ground truth and the real-data socket.
- [`PIPELINE.md`](PIPELINE.md) — the composable-stage architecture.
