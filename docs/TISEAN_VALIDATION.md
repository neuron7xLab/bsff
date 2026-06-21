<!-- SPDX-License-Identifier: CC-BY-4.0 -->
<!-- Copyright (c) 2026 Yaroslav Vasylenko / neuron7xLab -->

# TISEAN reference validation

## What TISEAN is

TISEAN (Hegger, Kantz & Schreiber, *Chaos* 9, 413-435, 1999) is the de-facto
reference C package for nonlinear time-series analysis. Its `surrogates` tool is
the canonical external implementation of amplitude-adjusted Fourier-transform
surrogate data — the AAFT algorithm (Theiler et al., *Physica D* 58, 1992) and
its iterative refinement IAAFT (Schreiber & Schmitz, *Phys. Rev. Lett.* 77,
1996). Surrogate data of this kind realises the null hypothesis "the series is a
monotonic nonlinear transform of a linear-Gaussian process", which is the null
that BSFF's MIAAFT engine tests against.

## Why BSFF ships an independent numpy reference

TISEAN is a compiled binary that is essentially never present in a hermetic CI
runner, so it cannot serve as an always-on validation oracle. To validate BSFF's
own surrogate engine (`bsff.surrogate_engine.miaaft_surrogate`) against something
*other than itself*, BSFF ships a second, from-scratch numpy implementation of
AAFT and IAAFT in `bsff.reference_surrogate`. This reference:

- shares **no code** with `bsff.surrogate_engine` — it is an independent
  derivation of the published algorithms, so agreement between the two is
  evidence of correctness, not of a shared bug;
- is fully deterministic under a fixed seed and depends only on numpy;
- is **not** TISEAN. It is a numpy reference. The gate detects a real TISEAN
  binary on `PATH` (`shutil.which("surrogates")`) and reports its presence or
  absence honestly. It never claims TISEAN was run when the binary is absent —
  which it will be in CI (`tisean_was_run: false`).

## The reference algorithms

- `aaft_surrogate(x, *, seed)` — one AAFT surrogate: rank-order Gaussianisation,
  Fourier phase randomisation, then rank remap of the original amplitudes. The
  marginal is preserved exactly; the power spectrum approximately (the known
  AAFT bias).
- `iaaft_surrogate(x, *, n_iter=100, seed, return_diagnostics=False)` — one
  IAAFT surrogate: alternating spectral projection (impose target amplitude
  spectrum) and amplitude projection (restore exact marginal by rank remap)
  until the rank order stops changing or the spectral error plateaus. With
  `return_diagnostics=True` it also returns convergence iterations, the
  converged flag, the amplitude-spectrum relative error, and the marginal KS
  distance.

## Metrics compared

`compare_against_reference(x, *, seed, n_iter)` runs both engines on the same
1-D fixture with the same seed and budget and reports, for each engine:

| metric | meaning |
| --- | --- |
| amplitude-spectrum relative error | L2 error between the surrogate and original amplitude spectra, normalised by the original spectrum norm |
| marginal KS distance | two-sample Kolmogorov-Smirnov distance between the surrogate and original empirical CDFs (≈0 for a rank-preserving surrogate) |
| covariance RMSD | RMSD between the lagged autocovariance sequences (lags 0..8) of surrogate and original — the second-order structure both engines must preserve |
| rank-order p-value | one-sided `(exceed + 1)/(n + 1)` surrogate-test p-value using the lag-1 quadratic-correlation statistic |
| convergence iterations | IAAFT iterations actually taken before the rank order froze |

Derived agreement quantities: `spectrum_error_gap` (absolute difference of the
two engines' spectrum errors), `covariance_rmsd_gap`, and
`rank_correlation_p_stability` (absolute difference of the two engines'
p-values).

## Tolerances

The gate (`tools/validate_tisean_reference.py`) asserts:

| tolerance | default | rationale |
| --- | --- | --- |
| `spectrum_gap_tol` | `0.05` | the two engines' relative amplitude-spectrum errors must agree to within 5% |
| `marginal_tol` | `1e-9` | both engines are rank-preserving, so the marginal KS distance must be at machine precision |
| `covariance_gap_tol` | `0.10` | the two engines' autocovariance RMSDs must agree to within 0.1 |

These ceilings are version-stable and generous: on the shipped AR(1) and Hénon
fixtures the measured gaps are at or near `0.0` because, for a univariate input
driven with the same seed, BSFF's common-phase MIAAFT reduces to standard IAAFT
and produces the identical rank-projected surrogate. The tolerances exist to
catch a *regression* in either engine, not to paper over a stochastic mismatch.

## Failure modes the gate catches

- A change in `surrogate_engine` that breaks marginal preservation → non-zero
  `marginal_ks_bsff` exceeds `marginal_tol` → FAIL.
- A spectral-projection regression in either engine → `spectrum_error_gap`
  exceeds `spectrum_gap_tol` → FAIL.
- A second-order (autocovariance) regression → `covariance_rmsd_gap` exceeds
  `covariance_gap_tol` → FAIL.
- A non-converging IAAFT (reported via `reference_converged` /
  `reference_n_iter_actual`) surfaces in the artifact rather than being hidden.

The gate is **fail-closed**: any failed case sets exit code 1.

## How to run the gate

```bash
python tools/validate_tisean_reference.py
```

It writes three artifacts and prints a one-line-per-fixture summary:

- `artifacts/tisean_validation.json` — full machine-readable report,
- `artifacts/tisean_validation.md` — human-readable table,
- `artifacts/tisean_validation.csv` — flat per-fixture metrics.

Exit code `0` = PASS, `1` = any fixture failed.

The pytest suite covers the same paths:

```bash
python -m pytest tests/test_tisean_reference.py -q
```

## Optionally comparing against the real TISEAN binary

If you install the real TISEAN package and put its `surrogates` executable on
`PATH`, the gate's `tisean_reference` field reports the resolved path instead of
`not_available_on_path`. The numpy reference remains the in-CI oracle; the real
binary, when present, is an additional out-of-band cross-check. A typical manual
cross-check writes the fixture to an ASCII column file and runs, e.g.:

```bash
surrogates -i100 -n1 fixture.dat > tisean_surrogate.dat
```

then compares the amplitude spectrum and marginal of `tisean_surrogate.dat`
against the BSFF and numpy-reference surrogates. This step is **not** part of CI
and is never assumed to have run: the artifact always records
`tisean_was_run: false` unless a future, explicitly TISEAN-driven path sets it.
