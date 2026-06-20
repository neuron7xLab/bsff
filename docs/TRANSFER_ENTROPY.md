<!-- SPDX-License-Identifier: CC-BY-4.0 -->
<!-- Copyright (c) 2026 Yaroslav Vasylenko / neuron7xLab -->

# Transfer Entropy — directed coupling, fail-closed

> A directed-information test that knows how it fails. It detects linear directed
> coupling, refuses to read a raw value as evidence, and measures — rather than
> assumes — what it does when a common driver is present.

## What it estimates

Transfer entropy (Schreiber 2000) is the predictive information a source series
carries about a target's next value *beyond the target's own past*. For jointly
Gaussian processes it reduces to a log-ratio of OLS residual variances and
coincides with linear Granger causality:

```
TE(X -> Y) = 0.5 * ln( RSS(Y | Y_past) / RSS(Y | Y_past, X_past) )
```

This estimator is deterministic, fast, and its bias is characterisable. It is
also biased **positive**: adding the source's history to a nested OLS can only
shrink the residual, so `TE >= 0` always and `TE > 0` even under no coupling.
A raw transfer entropy is therefore never evidence on its own.

## The test

The verdict comes from a surrogate null: the source series is circularly shifted
many times — which destroys its directed timing relative to the target while
preserving its marginal and autocorrelation — and the observed TE is compared to
that null. Both directions are tested. A coupling is only called when its
p-value clears `alpha` **and** its TE exceeds the reverse direction's, so shared
structure is not read as bidirectional causation by default.

## Measured operating characteristic

The instrument is calibrated against labelled ground truth, not asserted correct
(`tools/calibrate_transfer_entropy.py`, `bsff.te_operating_characteristic`):

| regime | what it is | expected | measured (n=512, k=2, cond_lag=3) |
|--------|-----------|----------|-----------------------------------|
| independent | two independent AR(1) | FPR ≈ α | **0.00** |
| causal | linear X→Y | power → 1, direction X→Y | **1.00**, reverse 0.00–0.08 |
| common-drive **pairwise** | shared latent, no direct link | *fooled* | **1.00** (false) |
| common-drive **conditional** | same, conditioning on the latent | back toward α | **0.00** |

### The headline boundary (not hidden)

**Pairwise transfer entropy cannot distinguish a direct coupling from a common
drive** — under a shared latent it reports X→Y at a false-positive rate of ~1.0.
This is a property of the quantity, not a bug. Conditioning on the confounder
repairs it, but the repair is sample- and lag-dependent:

| n_samples | k, cond_lag | conditional FPR |
|-----------|-------------|-----------------|
| 512 | 1, 2 | 0.10 |
| 1024 | 1, 2 | 0.05 |
| 1024 | 2, 3 | 0.017 |
| 512 | 2, 3 | 0.00 |

Minimal conditioning history on short series leaves a residual above α; adequate
history (k=2, cond_lag=3) is conservative even at n=512. Use enough history, and
never read a pairwise result as causal when a common driver is plausible.

## Usage

```python
from bsff.transfer_entropy import transfer_entropy_test

result = transfer_entropy_test(source, target, k=2, n_surrogates=199, alpha=0.05)
result.direction      # "source->target" | "target->source" | "bidirectional" | "none"

# control for a suspected common driver z
conditional = transfer_entropy_test(source, target, conditions=[z], k=2, cond_lag=3)
```

## Non-goals

- It does not detect **nonlinear** directed coupling; this is the *linear*
  (Gaussian) estimator. Nonlinear transfer entropy (e.g. k-NN / KSG) is out of
  scope here and would need its own calibration.
- It does not discover confounders for you: conditioning only controls for the
  series you supply. An unobserved common driver remains a confound.
- It is an instrument calibration of a statistical test, not a claim about any
  particular system.
