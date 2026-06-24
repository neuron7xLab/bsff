<!-- SPDX-License-Identifier: CC-BY-4.0 -->
# S2 specificity protocol (frozen)

## Current blocker
G2 failed: combined AR-null FPR = **0.065 > 0.05** (Set A 0.08, Set B 0.05) with the
S1 statistic `sampen_lower_tail_m2_r015_v1`. G1 power is sufficient (E 0.96, A_not 0.86,
B_not 0.91). The statistic is sensitive but not specific.

## Objective
Pass G2 (combined AR-null FPR ≤ 0.05) **without destroying G1**.

## Frozen success criteria (fixed before any S2 run; do not change after results)
- **G1:** E SURVIVED ≥ 0.80 AND A not-SURVIVED ≥ 0.80 AND B not-SURVIVED ≥ 0.80.
- **G2:** combined AR-null FPR ≤ 0.05 (required). Per-set FPR_A ≤ 0.05 and FPR_B ≤ 0.05 preferred.
- alpha = 0.05 (fixed).
- **S2_BRIGHT_LINE_PASSED = S2_G1_PASS AND S2_G2_PASS.**

## Forbidden (integrity)
- changing alpha; changing thresholds after results;
- removing Set A because it fails; segment cherry-picking;
- post-hoc statistic selection; declaring success on exploratory only;
- proceeding to BNCI before G2 passes.

## Runs
- Exploratory: n_segments = 30, n_surrogates = 199, on all candidates.
- Selection: freeze exactly one candidate (or NONE) in `S2_SELECTION_LOCK.json` before confirmatory.
- Confirmatory: n_segments = 100, n_surrogates = 199, on the frozen candidate only (999 is
  compute-infeasible: MIAAFT on 4097-sample segments ~ hours; 199 gives p-resolution 0.005,
  adequate for alpha=0.05 — same basis as the S1 confirmatory). This is a compute parameter,
  not a threshold; alpha and pass criteria are unchanged.

## Deterministic seeds
`SEED_BASE = 20260623` (G1), `20260624` (G2). No Python hash() randomization.
