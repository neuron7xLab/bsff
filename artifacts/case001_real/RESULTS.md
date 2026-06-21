# BSFF-CASE-001 — Results (physionet, decoder=logvar_lda)

**Verdict: `REFUTED`**

> within-subject decodability does NOT generalize: within=0.605 (p=0.002) with a significant generalization gap of 0.151 (paired-permutation p=0.002) while LOSO=0.454 sits in its null (mean 0.499). The within/global-validation number hides subject-specific structure.

| metric | value |
|---|---|
| within-subject CV accuracy | 0.605 |
| leave-one-subject-out accuracy | 0.454 |
| **generalization gap (within - LOSO)** | **0.151** |
| within-subject permutation p | 0.001996 |
| LOSO permutation p | 0.986 |
| **generalization-gap permutation p** | **0.001996** (resolved: True) |
| null-within mean (leak control) | 0.495 |
| global-normalization LOSO inflation | 0.000 |
| block-aware within split | True |
| chance / alpha | 0.5 / 0.05 |
| n trials / n subjects | 405 / 9 |

`artifact_sha256`: `72af611fd0c7f4e87670ed97c7fe5cf9f7488fe92cae25cc0fde573f7fdc3027`
