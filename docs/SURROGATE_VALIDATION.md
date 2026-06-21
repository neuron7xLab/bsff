<!-- SPDX-License-Identifier: CC-BY-4.0 -->
<!-- Copyright (c) 2026 Yaroslav Vasylenko / neuron7xLab -->

# Surrogate fidelity — does the null actually preserve what it must?

A surrogate test is only as trustworthy as its surrogates. IAAFT/MIAAFT defines a
linear-Gaussian null by holding three properties of the original signal while
destroying everything else. If the generator does not actually hold them, every
verdict downstream is built on sand. This validation measures them on a labelled
battery (`tools/validate_surrogate_fidelity.py`, `bsff.surrogate_engine`).

## The three defining properties

| property | what IAAFT must do | measured |
|----------|--------------------|----------|
| **marginal distribution** | preserved **exactly** (the surrogate is a reordering of the original amplitudes) | `0` (sorted values identical) |
| **power spectrum** | matched to a small residual | relative error **≈ 0.3–1.1%** |
| **channel covariance** | preserved (linear structure) | relative RMSD **≤ 0.09%** |
| **convergence** | reached within the iteration budget | converged in **24–38** iters |

## The honest number that matters

The spectrum residual is **~1%, not zero** — and that is correct, not a defect.
IAAFT cannot simultaneously give a perfect spectrum *and* an exact marginal; it
converges to a small spectral residual while keeping the marginal exact. A
validation that demanded a `~1e-6` spectrum error would be testing a fantasy, not
the algorithm. The tolerances here are calibrated to what IAAFT actually
achieves: marginal exact, spectrum < 5%, covariance < 5%.

## Run

```bash
python tools/validate_surrogate_fidelity.py        # writes artifacts/surrogate_fidelity.json
pytest tests/test_surrogate_fidelity.py
```

## Scope and the standing disclosure

This is **intrinsic-property** validation: it verifies the generator satisfies
the IAAFT definition. It is not a byte-comparison against the TISEAN reference C
implementation, which would need that package built and is complementary future
work. The repository's limit disclosure — *not externally validated against
TISEAN* — therefore stands; what this adds is a measured guarantee that the
surrogates are real IAAFT surrogates, enforced in CI.
