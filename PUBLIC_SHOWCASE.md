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

## A real measurement (n=2 — a demonstration, not proof)
On real open BCI data (BNCI2014_001 motor imagery), a standard pipeline scored
**0.81 within-subject** but only **0.60 when tested on a held-out subject** — and
for one subject it dropped to **chance (0.52)**. The gap is **+0.204**.

**Read this honestly:** it is **two subjects of one dataset**, with **no
confidence interval and no significance test**. It is a real, reproducible,
hash-backed *measurement* that shows the within-vs-cross gap is real and
demonstrable — it is **not** statistical proof that "BCI does not generalize."
That general claim is `UNPROVEN` (see `CLAIM_AUDIT.md`). What is proven is the
*method*: the harness produces the gap reproducibly; a full multi-subject
benchmark (network-bound) is what would turn a demonstration into evidence.

### What "+0.204 LOSO gap" means (at n=2)
A model that looks ~81% accurate when it trains and tests on the *same people*
fell to ~60% (and to coin-flip for one person) on a held-out subject. At n=2 this
illustrates the mechanism — within-subject accuracy can reflect recognizing the
training subjects, not decoding intent — but it does not, by itself, settle the
published claim. Leave-one-subject-out (LOSO) is the honest test; here it is run,
recorded, and hashed at minimal n.

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
