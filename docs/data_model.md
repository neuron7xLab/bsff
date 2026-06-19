<!-- SPDX-License-Identifier: CC-BY-4.0 -->

# BSFF Data Model

## ClaimSpec

The claim is the root object. It defines the signal, task, statistic, null model, significance level, and minimum surrogate count.

## LeakageResult

```json
{
  "detector": "block_design_temporal_autocorrelation",
  "flagged": true,
  "mean_block_label_purity": 1.0,
  "label_transition_rate": 0.06,
  "n_blocks": 12
}
```

## SurrogateDiagnostics

```json
{
  "covariance_rmsd": 0.0,
  "mean_abs_spectrum_error": 0.0
}
```

## VerdictJSON

```json
{
  "claim_id": "demo",
  "verdict": "REFUTED | UNSUPPORTED | SURVIVED",
  "p_value": 0.05,
  "original_statistic": 0.0,
  "surrogate_min": 0.0,
  "surrogate_max": 0.0,
  "leakage_flags": {},
  "evidence": {},
  "caveats": []
}
```
