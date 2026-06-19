<!-- SPDX-License-Identifier: CC-BY-4.0 -->

# BSFF falsification protocol

## Principle

BSFF starts from the hostile assumption that a BCI claim may be inflated by leakage, autocorrelation, underpowered statistics, broken null models, or narrative decoration. Charming, really. The pipeline accepts only evidence that survives executable attacks.

## Phase 1 gates

1. Schema validation: `ClaimSpec.validate()`.
2. Stationarity warning gate: KPSS per channel.
3. Leakage gate: block-design temporal autocorrelation detector.
4. Surrogate gate: common-phase MIAAFT rank-order null attack.
5. Convergence gate: every surrogate's convergence and spectral/covariance fidelity is measured at verdict time. The MIAAFT budget is driven by the active policy, not a fixed constant, and a non-converged or low-fidelity null **fails closed** — the verdict is demoted to `UNSUPPORTED` because a mis-specified null makes both `SURVIVED` and `REFUTED` unearned.
6. Calibration gate: deterministic MIAAFT budget selection.
7. Artifact gate: JSON verdict + SHA-256 manifest, recomputed and verified on load.
8. Truth gate: README and docs must disclose limits; forbidden affirmative over-claims are matched case-insensitively.

## Verdicts

- `SURVIVED`: configured attacks did not break the claim.
- `REFUTED`: leakage or null evidence broke the claim.
- `UNSUPPORTED`: evidence is too weak or ambiguous for a stronger verdict.

## Phase 2 additions

- Independent TISEAN/reference comparison.
- Larger surrogate budgets.
- Bayesian evidence path.
- Feature-selection leakage detector against real preprocessing pipelines.
