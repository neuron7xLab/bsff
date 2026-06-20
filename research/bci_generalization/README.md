<!-- SPDX-License-Identifier: CC-BY-4.0 -->
<!-- Copyright (c) 2026 Yaroslav Vasylenko / neuron7xLab -->

# BCI generalization — the within-vs-cross falsification

The point of strike, not "another EEG analysis": take the canonical motor-imagery
pipeline (CSP + LDA), recover its **within-subject** accuracy on an open MOABB
dataset, then evaluate the *same pipeline* leakage-free across subjects. The gap
is the verdict.

## Why this is the right target

Most MI-BCI accuracy is reported **within-session** (k-fold over one subject's
trials). That number is real *as a within-subject number* — MOABB reports it
honestly — but it is routinely read as evidence of a working decoder. It is not:
CSP spatial filters are subject-specific and the data carry covariate shift, so
the same pipeline under **leave-one-subject-out (LOSO)** typically drops, often
toward chance. Demonstrating that drop, reproducibly, is a falsification of the
*generalization* the high number implies — with code, data version, and a hash,
not philosophy.

A precise note (sharper than the usual framing): the LOSO gap and within-session
*temporal* leakage are two distinct effects. This harness isolates the **cross-
subject** one, the cleaner and stronger demonstration; it does not claim the
benchmark itself is dishonest.

## Method

One pipeline, one dataset, two evaluations from MOABB's own machinery:

| evaluation | split | what it measures |
|------------|-------|------------------|
| `WithinSessionEvaluation` | k-fold within each subject/session | the reported-style high accuracy |
| `CrossSubjectEvaluation` | leave-one-subject-out | honest generalization |

`LeftRightImagery` (2-class, chance = 0.5), `CSP(n=6, ledoit_wolf) + LDA`. The
result records both means, the gap, per-subject cross scores, and a sha256.

## Run

```bash
pip install 'bsff[moabb]'        # heavy + network
python research/bci_generalization/run_experiment.py \
  --dataset BNCI2014_001 --subjects 1 2 3 --components 6 --out result.json
```

## Result

Run on real open data (`result.json` carries the hash). Expected and observed
shape: **within-session high, cross-subject markedly lower** — the generalization
gap. The full multi-subject benchmark is network-bound; a partial subject subset
already exhibits the gap. Drop your `result.json` here when produced; the verdict
is the gap and its hash, reproducible by anyone with the same MOABB version.

## Honest boundary

This falsifies the **generalization implied by a within-subject number**, on a
specific dataset and pipeline. It is not a claim that any author committed fraud,
nor a universal statement about all BCI. It is one reproducible, hash-backed
demonstration that an accuracy figure does not survive honest cross-subject
evaluation — which is exactly the demarcation BSFF exists to make.
