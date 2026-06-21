<!-- SPDX-License-Identifier: CC-BY-4.0 -->
<!-- Copyright (c) 2026 Yaroslav Vasylenko / neuron7xLab -->

# BSFF: a fail-closed falsification engine for signal and publication claims

**Yaroslav Vasylenko / neuron7xLab — v0.4.0**

## Abstract

BSFF is an instrument that adjudicates claims about signals and the claims of
publications, and returns a machine-readable, provenance-bound verdict. Its
design inverts the usual burden: a claim is treated as unsupported until it
survives an explicit falsification attempt, and no path can promote a claim to
"true" — the strongest disposition an empirical claim can earn is *survived
falsification under stated conditions*. Seven axioms (determinism, no-promotion,
fail-closed monotonicity, verbatim anchoring, provenance closure, raw-signal
guarding, seed-stability) are encoded as invariants the test runner enforces on
every commit. The instrument is calibrated against labelled ground truth, and is
demonstrated on real open data: a within-subject motor-imagery accuracy that does
not survive leave-one-subject-out evaluation. Every claim in this document is
tied to a command and a hash.

## 1. The problem

Claims about decoding intention, emotion, or cognitive state from neural signals
are produced faster than they are stress-tested, and large language models have
made plausible-sounding claims nearly free to generate. The scarce resource is no
longer assertion; it is refutation. BSFF automates one honest refutation pass.

## 2. Design principles

1. **Falsification-first.** The engine attacks a claim; it never confirms one.
2. **Fail-closed.** Under uncertainty the verdict moves toward *less* claim, never
   more (a mis-specified null, a leakage flag, or an unstable seed can only
   demote).
3. **No promotion to truth.** Survival is information, not coronation.
4. **Provenance or nothing.** A verdict is tied to real, unaltered input via a
   recomputable hash, or there is no verdict.

## 3. Architecture

One chain, fail-closed at every link (see `PIPELINE.md`):

```
raw signal (EDF/BDF/CSV/NPY) ─► normalize ─► raw-signal guard ─┐
publication claim (verbatim quote) ─► anchor ─► classify tier ─┤
                                                               ▼
   route { empirical → surrogate battery | causal → conditional transfer entropy
         | logical → argument structure  | else → quarantine }
                                                               ▼
                  verdict ─► hash-chained ledger ─► report (+ seed-stability)
```

## 4. The constitution (seven machine-checked invariants)

The axioms are not asserted in prose; they are enforced in `tests/test_invariants.py`
(see `INVARIANTS.md`): determinism (byte-identical at fixed seed), no-true,
fail-closed monotonicity, anchor (an absent quote is always quarantined),
provenance closure (the artifact hash recomputes), raw-signal guard (a non-signal
is refused), and seed-stability (a verdict that flips across the surrogate seed is
never certified). A change that breaks any one turns CI red. A property you cannot
break by accident is a guarantee; one you can is a slogan.

## 5. Calibration (measured, not asserted)

Against labelled ground truth (`operating_characteristic`,
`te_operating_characteristic`, and the v0.2.0 validation corpus):

| regime | expectation | measured |
|--------|-------------|----------|
| Hénon / logistic chaos | survive a linear-Gaussian null | SURVIVED |
| AR(1) / IID nulls | do not survive | REFUTED / not SURVIVED |
| linear X→Y coupling | directional detection | source→target |
| common-drive confound | pairwise fooled, conditional repaired | pairwise fires; conditional collapses |

The residual at small sample sizes is documented, not hidden.

## 6. Real result

On real open data — BNCI2014_001 (subjects 1–2), `LeftRightImagery`, `CSP6+LDA`,
via the benchmark's own evaluators:

| evaluation | accuracy |
|------------|----------|
| WithinSession | 0.807 (subject 1 ≈ 0.93–0.96) |
| CrossSubject (LOSO) | 0.603 — subject 1: 0.701, subject 2: 0.518 ≈ chance |
| **generalization gap** | **+0.204** (chance 0.500) |

The within-subject accuracy does not survive leave-one-subject-out: it drops by
~20 points overall and to chance for subject 2. This is a reproducible,
hash-backed demonstration that a within-subject figure does not generalize across
subjects — the demarcation the instrument exists to make. It is not an accusation
against any author; it is a measurement (`research/bci_generalization/`).

## 7. Reproducibility

Every artifact carries a sha256 and a command. The validation corpus regenerates
byte-identically from its committed generator; ledgers are hash-chained and
`bsff ledger-verify`-checked; the real result and its hash are committed. Two
subjects is a minimal LOSO; the full benchmark runs via the same harness with
more compute.

## 8. Limitations

The signal engines are linear/spectral; nonlinear directed coupling (k-NN
transfer entropy) and non-time-series designs are out of scope and would need
their own calibrated tests. The instrument is **not externally validated against
TISEAN** and carries **not regulatory validation**. It does **not** prove BCI
claims; it makes one auditable, reproducible pass and does not replace peer
review.

## 9. What "above academia" means here

Not louder claims — stricter ones. Where a paper asserts a result, BSFF ties it
to a falsification attempt, a fail-closed verdict, a recomputable hash, and a
seed-stability check, all enforced by a test runner. The contribution is not a
number; it is a method that refuses to overstate, by construction.
