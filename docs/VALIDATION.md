<!-- SPDX-License-Identifier: CC-BY-4.0 -->
<!-- Copyright (c) 2026 Yaroslav Vasylenko / neuron7xLab -->

# BSFF validation

This document is the consolidated ledger of what BSFF has been validated to do,
tiered by the strength of the evidence. Every entry is reproducible from a shipped
tool or test; none is an assertion of trust. The governing honesty rule: BSFF is
**instrument-validated on synthetic ground truth and against an independent
algorithm reference** — it is **not** clinically, regulatorily, or
external-suite validated, and a verdict on a synthetic fixture is a calibration,
not a finding about real neural data.

## Evidence tiers

| Tier | Meaning |
|---|---|
| **A — measured, in-CI** | A test or gate runs on every CI run; the result is reproduced automatically. |
| **B — measured, committed artifact** | A heavier calibration is run on demand and its full-resolution artifact is committed; a reduced version is re-measured in CI. |
| **C — reference cross-check** | Validation against an *independent* implementation of the same published algorithm, not against BSFF itself. |
| **D — offline path, synthetic fixture** | A complete real-data path that runs end-to-end on a synthetic, deterministic fixture; real data is dropped into the same socket. |

## 1. Synthetic calibration — two-sided correctness (Tier A)

The precondition for trusting any verdict is that the engine is *correct when the
answer is known*. `bsff.datasets.GROUND_TRUTH` holds datasets whose verdict is
fixed by construction; adjudicating them must reproduce the label.

| dataset | structure | expected | measured |
|---|---|---|---|
| `nonlinear_effect` | Hénon-map chaos | `SURVIVED` | `SURVIVED` (p≈0.01) |
| `nonlinear_null` | AR(1) noise | not `SURVIVED` | `REFUTED` (p≈0.38) |
| `coupling_effect` | linear X→Y | `source->target` | `source->target` (p≈0.01) |
| `coupling_null` | independent AR(1) | `none` | `none` (p≈0.51) |

A genuine effect survives; a matched null is killed. Full description in
[`DATASETS.md`](DATASETS.md).

## 2. Validation corpus (Tier A)

A deterministic, multichannel EEG/BCI-shaped corpus exercises the falsification
gates at scale. It is generated and verified by shipped tools, not committed as an
opaque blob:

- [`tools/generate_validation_corpus.py`](../tools/generate_validation_corpus.py)
  and `generate_validation_corpus_v0_2_0.py` — deterministic generators (numpy,
  fixed seeds, sha256-stamped).
- [`tools/validate_validation_corpus.py`](../tools/validate_validation_corpus.py)
  — fail-closed checker; CI re-derives the corpus and verifies the hashes.

The corpus is explicitly *not* a clinical dataset — it is a synthetic engineering
oracle, small enough for hosting and large enough to stress the multichannel
paths.

## 3. Operating-characteristic calibration (Tier B)

The measured false-positive / detection profile of the instrument, comparing the
frequentist-only rule against the shipped frequentist-AND-Bayesian conjunction
rule (α = 0.05, 99 surrogates, 60 seeds):

| class | target | frequentist survive | conjunction survive | conjunction 95% CI |
|---|---|---|---|---|
| `henon` | power | 1.000 | **1.000** | [0.959, 1.000] |
| `logistic` | power | 1.000 | **1.000** | [0.959, 1.000] |
| `ar1_phi0.75` | FPR | 0.117 | **0.033** | [0.007, 0.103] |
| `ar1_phi0.50` | FPR | 0.067 | **0.017** | [0.002, 0.075] |
| `white` | FPR | 0.033 | **0.000** | [0.000, 0.041] |

Power is unchanged; specificity is restored to ≤ α on every null class. The
full-resolution artifact is committed at `artifacts/operating_characteristic.json`
and a reduced battery is re-measured every CI run by
`tests/test_operating_characteristic.py`. Method, rationale and citations:
[`OPERATING_CHARACTERISTIC.md`](OPERATING_CHARACTERISTIC.md) and
[`FALSE_POSITIVE_CONTROL.md`](FALSE_POSITIVE_CONTROL.md).

To reproduce:

```bash
python tools/calibrate_operating_characteristic.py          # full (≈70 s)
python tools/calibrate_operating_characteristic.py --quick  # fast smoke
```

## 4. TISEAN reference validation (Tier C)

To validate BSFF's surrogate engine against something *other than itself*, BSFF
ships a second, from-scratch numpy implementation of AAFT/IAAFT in
`bsff.reference_surrogate` that shares **no code** with the production engine.
Agreement between the two independent derivations is evidence of correctness, not
of a shared bug.

[`tools/validate_tisean_reference.py`](../tools/validate_tisean_reference.py)
compares both engines on the same fixtures and asserts version-stable tolerances
(amplitude-spectrum gap ≤ 0.05, marginal KS ≤ 1e-9, autocovariance RMSD gap ≤
0.10); on the shipped AR(1) and Hénon fixtures the measured gaps are at or near
0.0. The gate is fail-closed.

**Honesty:** the numpy reference is *not* TISEAN. The real TISEAN binary is an
optional out-of-band cross-check; when it is absent (as in CI) the artifact
records `tisean_was_run: false`. Full method, tolerances, and failure modes:
[`TISEAN_VALIDATION.md`](TISEAN_VALIDATION.md).

## 5. Real-EEG / BIDS path (Tier D)

A complete, deterministic, fail-closed path from a BIDS-EEG layout to a
machine-readable verdict via `bsff.bids.run_bids_case`, exercising four expected
cases (valid signal → `SURVIVED`; feature-table input → refused; label leakage →
`REFUTED`; non-stationary trace → verdict + KPSS caveat), reproduced offline by
`python examples/real_eeg_bids/run.py` and gated by
[`tools/validate_real_eeg_case.py`](../tools/validate_real_eeg_case.py).

**Honesty:** the shipped BIDS fixture is a **synthetic, EEG-shaped fixture**
(deterministic Hénon traces), not a real human recording. A `SURVIVED` here is
**not** evidence about real EEG; it only confirms the path and guards run. The
loader points at any real BIDS-EEG tree unchanged. Full method, guards, and the
substitution recipe: [`REAL_EEG_VALIDATION.md`](REAL_EEG_VALIDATION.md).

## What is NOT validated

- **No clinical or regulatory validation.** BSFF is a falsifier, not a diagnostic
  or regulated device.
- **No external-suite validation.** The numpy reference is an internal
  independent cross-check, not an accredited external surrogate suite; the real
  TISEAN binary is not run in CI.
- **No real published dataset ships.** All corpora and the BIDS example are
  synthetic, deterministic fixtures.
- **Out-of-scope statistics.** Nonlinear directed coupling (k-NN transfer
  entropy) and non-time-series designs (two-group, cohort) need their own
  validated tests before any claim that needs them can be adjudicated.

## See also

- [`METHODOLOGY.md`](METHODOLOGY.md) — the method these gates validate.
- [`OPERATING_CHARACTERISTIC.md`](OPERATING_CHARACTERISTIC.md) / [`FALSE_POSITIVE_CONTROL.md`](FALSE_POSITIVE_CONTROL.md) — FPR control.
- [`DATASETS.md`](DATASETS.md) — ground truth + real-data socket.
- [`TISEAN_VALIDATION.md`](TISEAN_VALIDATION.md) — reference cross-check.
- [`REAL_EEG_VALIDATION.md`](REAL_EEG_VALIDATION.md) — BIDS path.
- [`../STATUS.md`](../STATUS.md) — current version / test count / readiness.
