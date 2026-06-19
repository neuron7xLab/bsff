<!-- SPDX-License-Identifier: CC-BY-4.0 -->

# BSFF falsification protocol

## Principle

BSFF starts from the hostile assumption that a BCI claim may be inflated by leakage, autocorrelation, underpowered statistics, broken null models, or narrative decoration. Charming, really. The pipeline accepts only evidence that survives executable attacks.

## Phase 1 gates

1. Schema validation: `ClaimSpec.validate()`.
2. Stationarity warning gate: KPSS per channel.
3. Leakage gate: block-design temporal autocorrelation detector.
4. Surrogate gate: common-phase MIAAFT rank-order null attack.
5. Calibration gate: deterministic MIAAFT budget selection.
6. Artifact gate: JSON verdict + SHA-256 manifest.
7. Truth gate: README and docs must disclose limits.

## Verdicts

- `SURVIVED`: configured attacks did not break the claim.
- `REFUTED`: leakage or null evidence broke the claim.
- `UNSUPPORTED`: evidence is too weak or ambiguous for a stronger verdict.

## Phase 2 additions

- Independent TISEAN/reference comparison.
- Larger surrogate budgets.
- Bayesian evidence path.
- Feature-selection leakage detector against real preprocessing pipelines.
