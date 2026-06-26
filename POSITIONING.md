<!-- SPDX-License-Identifier: CC-BY-4.0 -->
<!-- Copyright (c) 2026 Yaroslav Vasylenko / neuron7xLab -->

# POSITIONING — the coordinate BSFF occupies

This document fixes BSFF's coordinate in the tool space. It is not marketing; it
is a falsifiable claim about *what BSFF is and is not*, written to the same
standard as every other claim in this repository — if a row here is wrong, it is
a defect, not a slogan.

## The one-sentence coordinate

> **BSFF is the falsification gate for neural-decoding claims: a deterministic,
> fail-closed CI step that sits between a signal result and the claim it
> licenses, and returns a provenance-bound verdict instead of trust.**

A *result* is not a *claim*. "The decoder hit 0.8 accuracy" is a result; "this
EEG carries nonlinear structure / this BCI generalizes" is the claim it is used
to license. Everywhere else that gap is crossed by author assertion and peer
review. BSFF makes it a machine-checked, reproducible gate.

## Why this coordinate is empty

The space around BSFF is occupied — but no neighbour stands on this exact point.

| Neighbour | What it does | What it does **not** do (the gap BSFF fills) |
|---|---|---|
| **TISEAN, nolds, pyunicorn** | Compute surrogates / nonlinearity measures | Adjudicate a *claim*; fail closed; bind a verdict to provenance; measure their own false-positive rate |
| **MNE-Python, NeuroKit2, MOABB** | Process EEG, build/benchmark decoders | Attack the claim a decoder licenses; refuse out-of-scope claims; emit a bounded verdict |
| **statsmodels / SciPy / pingouin** | Return a *p*-value or Bayes factor | Combine frequentist + Bayesian into a single fail-closed disposition with a calibrated operating characteristic |
| **cleanlab, deepchecks, evidently** | Data/label/drift checks for tabular ML | Target time-series neural-decoding claims and surrogate-null falsification |
| **SLSA, sigstore/cosign, DataLad** | Bind *software/data artifacts* to provenance | Bind a *scientific verdict* to the evidence that produced it |

The unique intersection is **adversarial claim-adjudication × neural-decoding
signals × machine-checkable, fail-closed provenance**. Each neighbour holds one
or two of those axes; none holds all three.

## The five load-bearing differentiators

1. **Claim-level, not data-level.** Input is a falsifiable `ClaimSpec` + a signal;
   output is a verdict — `SURVIVED` / `REFUTED` / `UNSUPPORTED` / `QUARANTINED`.
2. **Fail-closed by construction.** Every gap (non-converged null, missing
   evidence, NaN, out-of-scope, non-stationary, uncorroborated rejection) demotes
   the verdict toward the conservative pole. The instrument distrusts itself.
3. **Provenance-bound determinism.** A verdict is hash-bound to its evidence
   graph; the same inputs reproduce the same verdict and the same hash.
4. **A measured operating characteristic.** Specificity/power are *measured*
   (FPR 0.028, cluster-robust CI [0.016, 0.040]), CI-gated, and re-derivable — not
   asserted.
5. **Falsification-first epistemics.** BSFF never confirms. The strongest
   disposition it offers is *survived falsification under stated conditions*.

## The analogy that places the coordinate

> What `cosign verify` / SLSA are to a **build artifact**, BSFF is to a
> **scientific claim**: the gate that refuses to take the artifact on trust and
> binds it to checkable evidence.

Reproducibility tools verify *that you ran the code*. Statistics libraries
compute *a number*. BSFF verifies *whether the claim survives attack* — and is
designed to fail closed when it cannot tell.

## Where the coordinate does NOT extend (scope walls)

Stating the boundary is part of fixing the point. BSFF is **not** a clinical,
diagnostic, or regulatory instrument; not a generic signal-processing library;
not a decoder; not a proof engine (it refutes or fails to refute, never proves);
and its external validation is currently single-dataset (real Bonn EEG S2/S3,
plus an n=9 PhysioNet LOSO measurement) — a measured instrument, not a
population-level authority. See [`LIMITATIONS_HARD.md`](LIMITATIONS_HARD.md).

## How to falsify this positioning

This coordinate is wrong if any of the following is shown:

- a named tool returns a **fail-closed, provenance-bound verdict** on a BCI/EEG
  *claim* (not a *p*-value or a surrogate set) — then the coordinate is occupied;
- BSFF's verdicts are not reproducible from inputs (provenance binding fails);
- the measured operating characteristic cannot be re-derived from committed
  artifacts (the "measured, not asserted" differentiator collapses).

Until then, the point is held. See [`CLAIM_AUDIT.md`](CLAIM_AUDIT.md) and
[`REVIEWER_PACKET.md`](REVIEWER_PACKET.md) for the evidence behind each row.
