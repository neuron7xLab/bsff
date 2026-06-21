# BSFF-CASE-001 — Results (synthetic, decoder=logvar_lda)

**Verdict: `REFUTED`**

> within-subject decodability does NOT generalize leave-one-subject-out: within=1.000 (p=2.78e-163) collapses to LOSO=0.467 (permutation p=0.96, null mean=0.500). The within/global-validation number hides subject-specific structure.

| metric | value |
|---|---|
| within-subject CV accuracy | 1.000 |
| leave-one-subject-out accuracy | 0.467 |
| **generalization gap (within - LOSO)** | **0.533** |
| label-shuffle within accuracy (control) | 0.476 |
| LOSO permutation p-value | 0.9601 |
| LOSO permutation null mean | 0.500 |
| global-normalization LOSO inflation | 0.000 |
| chance | 0.5 |
| n trials / n subjects | 540 / 9 |

`artifact_sha256`: `336c2611db5fb98b92cc08863e885ec7fc7027d10e7e13cb7e54271be9419c87`
