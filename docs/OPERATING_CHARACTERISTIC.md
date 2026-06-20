<!-- SPDX-License-Identifier: CC-BY-4.0 -->

# BSFF operating characteristic

This document records what the falsification instrument *measurably does* against
ground truth, not what it is hoped to do. The measurement is reproducible:

```bash
python tools/calibrate_operating_characteristic.py        # full (≈70 s)
python tools/calibrate_operating_characteristic.py --quick
```

and the full-resolution result is committed at
`artifacts/operating_characteristic.json`. A reduced battery is recomputed on
every CI run by `tests/test_operating_characteristic.py`.

## The battery

Five labelled generators. The label is the instrument *target* — whether genuine
nonlinear structure (which a linear-Gaussian surrogate null cannot reproduce) is
present — not an assumption about the data:

| class | generator | nonlinear structure? |
|---|---|---|
| `henon` | deterministic Hénon-map chaos | yes — should SURVIVE |
| `logistic` | deterministic logistic-map chaos | yes — should SURVIVE |
| `ar1_phi0.75` | strongly autocorrelated linear-Gaussian AR(1) | no — should not survive |
| `ar1_phi0.50` | moderately autocorrelated linear-Gaussian AR(1) | no — should not survive |
| `white` | IID Gaussian white noise | no — should not survive |

Two decision rules are scored from the *same* evidence per realization:

- **frequentist** — SURVIVED iff the rank-order surrogate test rejects
  (`p ≤ α`) and the null converged.
- **conjunction** (the shipped rule) — additionally requires an effect-size
  Bayes factor `BF10 ≥ corroboration_min` before a rejection earns SURVIVED.

## Measured result (α = 0.05, 99 surrogates, 60 seeds)

| class | target | frequentist survive | conjunction survive | conjunction 95% CI |
|---|---|---|---|---|
| `henon` | power | 1.000 | **1.000** | [0.959, 1.000] |
| `logistic` | power | 1.000 | **1.000** | [0.959, 1.000] |
| `ar1_phi0.75` | FPR | 0.117 | **0.033** | [0.007, 0.103] |
| `ar1_phi0.50` | FPR | 0.067 | **0.017** | [0.002, 0.075] |
| `white` | FPR | 0.033 | **0.000** | [0.000, 0.041] |

**Power is unchanged (1.000) and specificity is restored to ≤ α on every null
class.** The Bayes factor cleanly separates the two regimes: genuine nonlinear
structure yields `BF10` on the order of 10³⁵, whereas every false frequentist
rejection on a null class carries `BF10 < 1.5`. A single threshold therefore
partitions them with a wide margin.

## Why the conjunction gate exists

The rank-order surrogate p-value is **anti-conservative for strongly
autocorrelated linear-Gaussian processes**. With a finite series length the
amplitude-adjusted Fourier-transform / IAAFT surrogate does not perfectly
reproduce the higher-order spectral properties the quadratic statistic reads, so
a near-zero nonlinear effect clears `α` more often than the nominal rate. This is
a documented surrogate bias, not a coding defect — see Kugiumtzis (2002),
*Surrogate data test for nonlinearity including nonmonotonic transforms*, Phys.
Rev. E 62, R25. Tightening the surrogate fidelity gate does **not** remove it:
the offending surrogates are high-fidelity (relative spectral error < 0.03), so
they pass the convergence gate while still biasing the test.

The fix is to demand corroboration in a second, orthogonal currency. An
effect-size Bayes factor asks not "did the statistic clear a rank threshold?" but
"is the effect large relative to the surrogate spread?". An IAAFT-bias artifact
has a tiny effect by construction, so it cannot clear `BF10 ≥ 3` even when it
sneaks past the p-value. The gate is **fail-closed**: it can only ever demote a
SURVIVED to UNSUPPORTED, never the reverse, and it is inert unless Bayesian
evidence is enabled (the `standard` and `strict` policies; `strict` raises the
threshold to 10).

## Scope

This is an instrument calibration of a statistical test on synthetic fixtures
with known ground truth. It is **not** a validation against an external surrogate
suite, and it is **not** evidence about any specific neural recording. It bounds
the engine's false-positive and detection behaviour for the shipped statistic and
null model so that a real verdict can be read with a known error profile.
