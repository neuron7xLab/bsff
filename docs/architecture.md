<!-- SPDX-License-Identifier: CC-BY-4.0 -->

# BSFF v0.1 Architecture

## Core object

A BCI claim becomes executable only after it is encoded as `ClaimSpec`:

```text
claim_id
signal_type
task_type
sampling_rate_hz
n_channels
n_samples
statistic
split_policy
null_model
alpha
surrogate_count
stationarity_gate
```

No `ClaimSpec`, no falsification. Human prose is not an API, despite humanity's heroic commitment to pretending otherwise.

## Pipeline

```text
ClaimSpec
  ↓
LeakageProbe
  ↓ if clean
SurrogateEngine
  ↓
RankOrderTest
  ↓
VerdictJSON
```

## MVP falsification attacks

1. **Leakage attack**: flags block-design temporal leakage.
2. **Surrogate attack**: compares an original nonlinear statistic to MIAAFT surrogates.
3. **Verdict attack**: emits `REFUTED`, `UNSUPPORTED`, or `SURVIVED` without proof-language.

## Phase 1 hard gates

- AR(1) null must not be rejected in smoke tests.
- Hénon nonlinear fixture must be rejected in smoke tests.
- Multichannel surrogate must preserve cross-covariance within tolerance.
- Block-design fixture must be flagged.

## Phase 2

- TISEAN/reference comparator.
- Stationarity and end-matching gate.
- Fold-internal feature-selection leakage detector.
- Global normalization leakage detector.
- Label-permutation stability test.
- Bayesian evidence layer.

## Phase 3

- BIDS-App container.
- DataLad provenance.
- GPU/JAX batched FFT path.
- Extended nightly 999-surrogate run.
