<!-- SPDX-License-Identifier: CC-BY-4.0 -->
<!-- Copyright (c) 2026 Yaroslav Vasylenko / neuron7xLab -->

# BSFF — what it is, in plain terms

**BSFF does not trust a claim. It tries to break it.**

## What it is
A tool that takes a claim about a signal (or a publication's claim) and returns a
machine-readable verdict with a cryptographic hash. It is built so that nothing
it outputs can be a decorative lie: every verdict is reproducible, fail-closed,
and tied to its exact input.

## What it does not allow
- It never says a claim is **true**. The best a claim can earn is *survived a
  serious attempt to break it*.
- It refuses **non-signals**: feed it a results table or accuracy matrix and it
  rejects the input rather than testing your preprocessing.
- It refuses **fabrication**: a quote that does not appear in its source is
  quarantined, never judged.
- It refuses **lucky seeds**: a verdict that changes when the randomness changes
  is marked `UNSTABLE`, not certified.

## A real result already on the board
On real open BCI data (BNCI2014_001 motor imagery), a standard pipeline scored
**0.81 within-subject** but only **0.60 when tested on a held-out subject** — and
for one subject it dropped to **chance (0.52)**. The gap is **+0.204**.

### What "+0.204 LOSO gap" means
A model that looks ~81% accurate when it trains and tests on the *same people*
falls to ~60% (and to coin-flip for one person) when it must work on *someone it
has never seen*. The high number was not a working decoder; it was the model
recognizing the training subjects. Leave-one-subject-out (LOSO) is the honest
test, and the claim does not survive it.

## Why this is demarcation, not "anti-science"
BSFF does not attack science. It attacks **claims that have not been honestly
tested**. Reproducing a result and then re-running it without data leakage is
exactly what peer review is supposed to do — here it is automated, hash-backed,
and fail-closed. A claim that survives is stronger for it.

## The first public trophy
The first published artifact will be a single, reproducible falsification: a
named, citable accuracy figure that collapses under honest cross-subject
evaluation, shipped with code, data version, commands, and hashes that anyone can
re-run. Not an opinion — a verdict with a receipt.
