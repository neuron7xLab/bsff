<!-- SPDX-License-Identifier: CC-BY-4.0 -->
<!-- Copyright (c) 2026 Yaroslav Vasylenko / neuron7xLab -->

# False-positive control

BSFF's strongest verdict — `SURVIVED` — is the one most worth attacking, because
a false `SURVIVED` is a claim that *passed* a falsifier it should have failed.
This document explains the mechanism that bounds that error. The mechanism
**already ships** in the engine
([`src/bsff/verdict_engine.py`](../src/bsff/verdict_engine.py) and the pipeline
twin in [`src/bsff/pipeline.py`](../src/bsff/pipeline.py)); the numbers below come
from the operating-characteristic calibration tool, not from assertion.

## The problem: an anti-conservative p-value

BSFF's frequentist test is a rank-order surrogate test against a MIAAFT
(multivariate iterative amplitude-adjusted Fourier-transform) null. The null
hypothesis is "the series is a monotonic nonlinear transform of a
linear-Gaussian process". A genuine nonlinear effect should clear it; a linear
autocorrelated null should not.

For **strongly autocorrelated linear-Gaussian processes** the rank-order
surrogate p-value is **anti-conservative**: at finite series length the
IAAFT/MIAAFT surrogate does not perfectly reproduce the higher-order spectral
properties that the lag-quadratic statistic reads, so a *near-zero* nonlinear
effect clears `α` more often than the nominal rate. This is a documented
surrogate bias, not a coding defect (Kugiumtzis 2002, *Surrogate data test for
nonlinearity including nonmonotonic transforms*, Phys. Rev. E 62, R25).

Crucially, **tightening the surrogate fidelity gate does not remove it.** The
offending surrogates are high-fidelity (relative spectral error < 0.03), so they
*pass* the convergence/fidelity gate while still biasing the test. A second,
orthogonal check is required.

## The fix: a fail-closed conjunction gate

The engine demands corroboration in a different currency. After a frequentist
rejection it computes a JZS effect-size Bayes factor (`BF10`) comparing the
observed statistic to the surrogate spread, and requires

```
SURVIVED  ⟺  (p ≤ α  AND  null converged)  AND  BF10 ≥ corroboration_min
```

A rejection that is **not** corroborated (`BF10 < corroboration_min`) is demoted
to `UNSUPPORTED`. The gate is **fail-closed in both senses**:

- it can only ever *demote* a `SURVIVED` to `UNSUPPORTED`, never promote;
- it is inert unless Bayesian evidence is enabled — which the `standard` and
  `strict` policies do by default, so the empirical strict path always runs it.

The rejected-path twin also exists: when the frequentist test does **not** reject
and Bayesian evidence is on, the verdict is `REFUTED` only if `BF01 > 3` (explicit
evidence for the null), otherwise `UNSUPPORTED`. Both directions refuse to mint
certainty the evidence has not earned.

The conjunction is implemented twice and identically — in
`verdict_engine.evaluate_claim` (single-claim engine) and in
`FalsificationPipeline._collapse_verdict` (composable pipeline) — so neither
entry point can yield a `SURVIVED` the other would have blocked.

### Why an effect-size Bayes factor separates the regimes

An IAAFT-bias artifact has a *tiny* effect by construction: the statistic barely
exceeds the surrogate distribution. The Bayes factor asks "is the effect large
relative to the surrogate spread?" rather than "did it clear a rank threshold?",
so an artifact cannot clear `BF10 ≥ 3` even when it sneaks past the p-value.
Genuine nonlinear structure, by contrast, produces an enormous Bayes factor. A
single threshold cleanly partitions the two regimes with a wide margin.

## Calibration points

Measured by
[`tools/calibrate_operating_characteristic.py`](../tools/calibrate_operating_characteristic.py)
(α = 0.05, 99 surrogates, 60 seeds) and committed to
`artifacts/operating_characteristic.json`. Full table and method in
[`OPERATING_CHARACTERISTIC.md`](OPERATING_CHARACTERISTIC.md).

| class | target | frequentist survive | conjunction survive | conjunction 95% CI |
|---|---|---|---|---|
| `henon` (deterministic chaos) | power | 1.000 | **1.000** | [0.959, 1.000] |
| `logistic` (deterministic chaos) | power | 1.000 | **1.000** | [0.959, 1.000] |
| `ar1_phi0.75` (strong AR(1)) | FPR | 0.117 | **0.033** | [0.007, 0.103] |
| `ar1_phi0.50` (moderate AR(1)) | FPR | 0.067 | **0.017** | [0.002, 0.075] |
| `white` (IID Gaussian) | FPR | 0.033 | **0.000** | [0.000, 0.041] |

Reading the table:

- **Power is unchanged** (1.000) on both deterministic-chaos classes — the gate
  costs zero detection.
- **The strong-AR(1) false-positive rate** is the headline failure the gate
  fixes: the frequentist-only rule false-positives at **0.117**, nearly
  2.3× nominal `α`; the conjunction rule restores it to **0.033 ≤ α**.
- The moderate-AR(1) (0.067 → 0.017) and white-noise (0.033 → 0.000) classes
  confirm the gate is conservative across the null family, not tuned to one φ.
- The separation that makes this work: genuine structure yields `BF10` on the
  order of 10³⁵, whereas every false frequentist rejection on a null class
  carries `BF10 < 1.5` — well under the threshold of 3 (10 under `strict`).

To recompute locally:

```bash
python tools/calibrate_operating_characteristic.py          # full (≈70 s)
python tools/calibrate_operating_characteristic.py --quick  # fast smoke
```

A reduced battery is re-measured on every CI run by
`tests/test_operating_characteristic.py`.

## The rule: `SURVIVED` is forbidden when FPR calibration is violated

The operating principle the gate encodes:

> A frequentist rejection alone is **not** sufficient evidence for `SURVIVED`.
> When the false-positive calibration of the rank-order test is known to be
> violated (the autocorrelated-null regime), a rejection that lacks effect-size
> corroboration is demoted to `UNSUPPORTED`. `SURVIVED` is reserved for claims
> that clear *both* currencies.

Two corollaries:

1. **A non-converged null can never yield `SURVIVED` or `REFUTED`.** If any
   surrogate fails the convergence/fidelity gate the verdict is demoted to
   `UNSUPPORTED` before the Bayesian step even runs — a mis-specified null makes
   the p-value invalid, so both strong verdicts would be unearned.
2. **The thresholds only tighten.** `bayesian_corroboration_min` is validated to
   be ≥ 1.0 (a gate cannot loosen); the `strict` policy raises it from 3 to 10.

## Scope and honesty

This is an **instrument calibration** of a statistical test on synthetic
fixtures with known ground truth. It bounds the engine's false-positive and
detection behaviour for the shipped statistic and null model. It is **not** a
validation against an external surrogate suite, and it is **not** evidence about
any specific neural recording. It exists so that a real verdict can be read with
a known error profile.

## See also

- [`OPERATING_CHARACTERISTIC.md`](OPERATING_CHARACTERISTIC.md) — full measured table and method.
- [`METHODOLOGY.md`](METHODOLOGY.md) — where this gate sits in the pipeline.
- [`FALSIFICATION_PROTOCOL.md`](FALSIFICATION_PROTOCOL.md) — the gate sequence.
- [`VALIDATION.md`](VALIDATION.md) — the full evidence tier table.
