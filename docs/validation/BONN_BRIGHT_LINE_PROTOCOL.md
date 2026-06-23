<!-- SPDX-License-Identifier: CC-BY-4.0 -->
# Bonn bright-line protocol (pre-declared)

Thresholds and parameters are fixed HERE, before the confirmatory run. They are not
changed after seeing confirmatory results (no threshold hacking; alpha is fixed).

## Data
- Andrzejak et al. 2001 Bonn EEG, DOI `10.1103/PhysRevE.64.061907`.
- Canonical source: **UPF NTSA** (`epileptologie-bonn.de` offline). NOT the UCI
  178-feature variant. Provenance + per-file SHA256: `artifacts/bonn_bright_line/DATASET_MANIFEST.json`.
- Sets: **E** (ictal, positive control), **A**/**B** (healthy, negative control),
  100 segments each, 4097 samples/segment (4096 also accepted), fs = 173.61 Hz.

## Statistic
- `sampen_lower_tail_m2_r015_v1` (see STATISTIC_REGISTRY.md). MIAAFT null,
  lower-tail, convergence-gated, alpha = 0.05.

## Pre-declared thresholds (FIXED)
- **G1 positive control:** `frac(E SURVIVED) ≥ 0.80`.
- **G1 negative sanity:** `frac(A not-SURVIVED) ≥ 0.80` AND `frac(B not-SURVIVED) ≥ 0.80`.
- **G2 specificity:** real-spectrum AR-null `FPR ≤ 0.05` on each of A and B, and combined.
- **BRIGHT_LINE_PASSED = G1_PASS ∧ G2_PASS.**

## Runs (fixed)
- Exploratory: n_segments = 20, n_surrogates = 99.
- Confirmatory: n_segments = 100, n_surrogates = 199.
- Seeds: deterministic, `SEED_BASE = 20260623` (G1, seed = base + index),
  `20260624` (G2). No Python hash() randomization.

## Allowed final states (no others)
`BRIGHT_LINE_PASSED` · `BRIGHT_LINE_NOT_PASSED` · `BLOCKED_DATA` · `BLOCKED_RUNTIME`
· `BLOCKED_API` · `BLOCKED_METHOD`.

## Forbidden claims
No clinical, diagnostic, medical, or regulatory claim. Not final proof of brain
nonlinear dynamics. Not a universal BCI benchmark authority. A negative result is a
valid, publishable operating-characteristic finding.
