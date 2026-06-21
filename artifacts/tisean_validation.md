# TISEAN reference validation

BSFF MIAAFT engine validated against an **independent numpy IAAFT reference** (`bsff.reference_surrogate`).

- seed: `7`
- IAAFT iterations: `100`
- TISEAN binary: `not_available_on_path` (was_run=False)
- overall: **PASS**

| fixture | spectrum gap | marginal KS (bsff/ref) | cov RMSD gap | p-stability | result |
| --- | --- | --- | --- | --- | --- |
| ar1_linear_gaussian | 0.000e+00 | 0.0e+00 / 0.0e+00 | 0.000e+00 | 0.000 | PASS |
| henon_nonlinear | 0.000e+00 | 0.0e+00 / 0.0e+00 | 0.000e+00 | 0.000 | PASS |

