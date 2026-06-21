# BSFF-CASE-001 — Results (synthetic, decoder=logvar_lda)

**Verdict: `REFUTED`**

> within-subject decodability does NOT generalize: within=1.000 (p=0.002) with a significant generalization gap of 0.533 (paired-permutation p=0.002) while LOSO=0.467 sits in its null (mean 0.500). The within/global-validation number hides subject-specific structure.

| metric | value |
|---|---|
| within-subject CV accuracy | 1.000 |
| leave-one-subject-out accuracy | 0.467 |
| **generalization gap (within - LOSO)** | **0.533** |
| within-subject permutation p | 0.001996 |
| LOSO permutation p | 0.9601 |
| **generalization-gap permutation p** | **0.001996** (resolved: True) |
| null-within mean (leak control) | 0.499 |
| global-normalization LOSO inflation | 0.000 |
| block-aware within split | False |
| chance / alpha | 0.5 / 0.05 |
| n trials / n subjects | 540 / 9 |
| seed-stability agreement | 1.00 over 5 seeds |

`artifact_sha256`: `7b8741f45bc8867414c51c059dccb6d91692c78d9de55552ccf0500b6962d85a`
