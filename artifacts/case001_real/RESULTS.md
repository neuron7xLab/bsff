# BSFF-CASE-001 — Results (physionet, decoder=logvar_lda)

**Verdict: `REFUTED`**

> within-subject decodability does NOT generalize leave-one-subject-out: within=0.553 (p=0.0184) collapses to LOSO=0.454 (permutation p=0.98, null mean=0.497). The within/global-validation number hides subject-specific structure.

| metric | value |
|---|---|
| within-subject CV accuracy | 0.553 |
| leave-one-subject-out accuracy | 0.454 |
| **generalization gap (within − LOSO)** | **0.099** |
| label-shuffle within accuracy (control) | 0.494 |
| LOSO permutation p-value | 0.9801 |
| LOSO permutation null mean | 0.497 |
| global-normalization LOSO inflation | 0.002 |
| chance | 0.5 |
| n trials / n subjects | 405 / 9 |

`artifact_sha256`: `c57bf919e8eb4b8196ff4d50481cfd5f807ecf76b4d4777a2bffadd1c7d83059`
