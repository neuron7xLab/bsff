<!-- SPDX-License-Identifier: CC-BY-4.0 -->
# BNCI2014-001 preregistration — analysis plan

**Status:** scaffold. Freeze all numbers here before any BNCI run.

## Units
- Per subject (9), per session (train/eval), per motor-imagery class (4).

## Primary analysis (to freeze)
1. Epoch extraction with a fixed window relative to cue (e.g. 0.5–2.5 s), fixed band-pass.
2. Per-channel/per-epoch nonlinearity adjudication with the frozen S2 instrument
   (SampEn lower-tail, p ≤ 0.025, MIAAFT, convergence-gated).
3. Specificity control: spectrum-matched AR null per subject → FPR ≤ 0.05.
4. Decoding metric (e.g. cross-validated accuracy / kappa) reported with a null model.

## Pre-declared thresholds (PLACEHOLDER — must be set before execution)
- positive-control criterion: TBD-before-run
- specificity: AR-null FPR ≤ 0.05 (inherited)
- alpha = 0.05 (fixed)

## Seeds & determinism
Deterministic seeds; no Python hash() randomization; byte-frozen RESULTS on replay.

## Multiple comparisons
Family-wise / FDR control across subjects × classes, declared before run.

No result is produced by this file.
