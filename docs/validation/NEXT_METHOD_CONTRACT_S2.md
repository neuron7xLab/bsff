<!-- SPDX-License-Identifier: CC-BY-4.0 -->
# Next-method contract — S2 (specificity)

S2 is **not** part of PR #75 / this artifact's success. It is the next research branch,
opened **because** the current artifact found a real G2 specificity failure. It does not
rewrite the current verdict (`BRIGHT_LINE_NOT_PASSED`).

## Objective
Reduce real-spectrum AR-null FPR to **≤ 0.05** while preserving:
- Bonn Set E SURVIVED ≥ 0.80, and
- Sets A and B not-SURVIVED ≥ 0.80.

## Forbidden (integrity)
- changing alpha; changing thresholds after seeing results;
- selecting only favorable segments; dropping Set A because it fails; redefining G2;
- declaring success on exploratory data only.

## Allowed candidate approaches (pre-register before running)
- finite-N MIAAFT / AAFT bias correction (Kugiumtzis 1999);
- corroboration gate requiring two independent statistics to agree;
- FDR or family-wise correction across segments;
- stricter MIAAFT convergence criteria;
- SampEn parameter registry with a pre-declared grid + held-out confirmatory split;
- alternative nonlinear statistic with an independent positive-control rationale:
  recurrence quantification (fixed params), nonlinear prediction error (fixed embedding),
  permutation entropy (fixed order/delay), time-reversal asymmetry.

## Required S2 protocol
1. Pre-declare candidates + thresholds (commit before running).
2. Exploratory on a development subset.
3. Freeze exactly one candidate.
4. Confirmatory on full A/B/E **and** G2.
5. Preserve failures in the statistic registry.
6. Accept only if **both** G1 and G2 pass.
