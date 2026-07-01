# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (c) 2026 Yaroslav Vasylenko / neuron7xLab
"""Independent numpy reference implementation of AAFT / IAAFT surrogates.

This module is a *second, from-scratch* implementation of the classical
amplitude-adjusted Fourier-transform surrogate algorithms — the Amplitude
Adjusted Fourier Transform (AAFT, Theiler et al. 1992) and the Iterative AAFT
(IAAFT, Schreiber & Schmitz 1996). It deliberately shares **no code** with
``bsff.surrogate_engine``; its sole purpose is to act as an external reference
baseline against which BSFF's own MIAAFT engine can be validated.

The honesty constraint is explicit: this is a numpy reference, **not** the
TISEAN C package (Hegger, Kantz & Schreiber 1999). ``compare_against_reference``
optionally detects a real TISEAN binary on ``PATH`` but never claims TISEAN was
run when the binary is absent — which it will be in a hermetic CI.

References
----------
Theiler, J., Eubank, S., Longtin, A., Galdrikian, B., & Farmer, J. D. (1992).
    Testing for nonlinearity in time series: the method of surrogate data.
    Physica D, 58, 77-94.
Schreiber, T., & Schmitz, A. (1996). Improved surrogate data for nonlinearity
    tests. Physical Review Letters, 77, 635-638.
Hegger, R., Kantz, H., & Schreiber, T. (1999). Practical implementation of
    nonlinear time series methods: the TISEAN package. Chaos, 9, 413-435.
"""

from __future__ import annotations

import shutil
from typing import Any, cast

import numpy as np
from numpy.typing import NDArray

FloatArray = NDArray[np.float64]


def _as_1d(x: FloatArray) -> FloatArray:
    """Coerce input to a finite 1-D float array (fail closed on NaN/Inf)."""
    arr = np.asarray(x, dtype=float).reshape(-1)
    if arr.size < 8:
        raise ValueError("series must contain at least 8 samples")
    if not np.all(np.isfinite(arr)):
        raise ValueError("series must be finite; got NaN or Inf")
    return arr


def _phase_randomized(x: FloatArray, rng: np.random.Generator) -> FloatArray:
    """Fourier-phase-randomized surrogate preserving the amplitude spectrum.

    The DC term and (for even length) the Nyquist term carry no free phase and
    are held at zero so the inverse transform stays real.
    """
    spectrum = np.fft.rfft(x)
    amplitude = np.abs(spectrum)
    n = x.size
    phase = rng.uniform(0.0, 2.0 * np.pi, size=amplitude.shape)
    phase[0] = 0.0
    if n % 2 == 0:
        phase[-1] = 0.0
    return np.fft.irfft(amplitude * np.exp(1j * phase), n=n).astype(float)


def aaft_surrogate(x: FloatArray, *, seed: int | None = None) -> FloatArray:
    """Generate one AAFT surrogate (Theiler 1992).

    Procedure:

    1. Rescale the data to a Gaussian distribution that follows the rank order of
       the original series.
    2. Phase-randomize the Gaussianized series (preserving its power spectrum).
    3. Re-rank the original amplitudes onto the rank order of the randomized
       Gaussian series.

    The output is an exact permutation of the input amplitudes, so the marginal
    distribution is preserved bit-for-bit; the power spectrum is preserved only
    approximately (this is the known AAFT bias that IAAFT removes).
    """
    data = _as_1d(x)
    rng = np.random.default_rng(seed)
    n = data.size

    # Step 1: rank-ordered Gaussian. Draw a Gaussian sample, sort it, and assign
    # by the rank of the original data so the Gaussian series mirrors the data's
    # ordering structure.
    gaussian = np.sort(rng.standard_normal(n))
    ranks = np.argsort(np.argsort(data))
    gaussianized = gaussian[ranks]

    # Step 2: phase randomize the Gaussian surrogate.
    randomized = _phase_randomized(gaussianized, rng)

    # Step 3: rank-remap the original sorted amplitudes onto the randomized order.
    sorted_data = np.sort(data)
    out = np.empty(n, dtype=float)
    out[np.argsort(randomized)] = sorted_data
    return out


def iaaft_surrogate(
    x: FloatArray,
    *,
    n_iter: int = 100,
    seed: int | None = None,
    tol: float = 1e-8,
    return_diagnostics: bool = False,
) -> FloatArray | tuple[FloatArray, dict[str, Any]]:
    """Generate one IAAFT surrogate (Schreiber & Schmitz 1996).

    Starting from a random permutation of the data, the algorithm alternates two
    projections until convergence:

    * **Spectral projection** — replace the surrogate's amplitude spectrum with
      the target amplitude spectrum, keeping the surrogate's current phases.
    * **Amplitude projection** — rank-remap the original sorted amplitudes onto
      the spectrally projected series, restoring the exact marginal.

    Neither projection can satisfy both constraints exactly at finite N, so the
    iteration is monitored: it stops when the rank order stops changing or when
    the spectral error plateaus below ``tol``.
    """
    data = _as_1d(x)
    rng = np.random.default_rng(seed)
    n = data.size

    target_spectrum = np.fft.rfft(data)
    target_amp = np.abs(target_spectrum)
    sorted_data = np.sort(data)

    surrogate = rng.permutation(data).astype(float)
    prev_order = np.argsort(surrogate)
    last_err = np.inf
    converged = False
    iters = 0

    for i in range(int(n_iter)):
        iters = i + 1
        # Spectral projection: impose target amplitude, keep current phases.
        spectrum = np.fft.rfft(surrogate)
        phase = np.angle(spectrum)
        phase[0] = 0.0
        if n % 2 == 0:
            phase[-1] = 0.0
        projected = np.fft.irfft(target_amp * np.exp(1j * phase), n=n)
        # Amplitude projection: restore the exact marginal by rank remap.
        order = np.argsort(projected)
        surrogate = np.empty(n, dtype=float)
        surrogate[order] = sorted_data

        last_err = amplitude_spectrum_rel_error(data, surrogate)
        if np.array_equal(order, prev_order):
            converged = True
            break
        prev_order = order
        if last_err < tol:
            converged = True
            break

    if not return_diagnostics:
        return surrogate
    diag: dict[str, Any] = {
        "engine": "reference_iaaft",
        "n_iter_actual": int(iters),
        "n_iter_budget": int(n_iter),
        "converged": bool(converged),
        "amplitude_spectrum_rel_error": float(last_err),
        "marginal_ks": float(marginal_ks_distance(data, surrogate)),
    }
    return surrogate, diag


# --------------------------------------------------------------------------- #
# Agreement / fidelity metrics. Independent of bsff.surrogate_engine.
# --------------------------------------------------------------------------- #


def amplitude_spectrum_rel_error(x: FloatArray, surrogate: FloatArray) -> float:
    """Relative L2 error between the amplitude spectra of ``x`` and ``surrogate``."""
    ax = np.abs(np.fft.rfft(_as_1d(x)))
    asurr = np.abs(np.fft.rfft(_as_1d(surrogate)))
    return float(np.linalg.norm(asurr - ax) / (np.linalg.norm(ax) + 1e-12))


def marginal_ks_distance(x: FloatArray, surrogate: FloatArray) -> float:
    """Two-sample Kolmogorov-Smirnov distance between two empirical marginals.

    Computed from scratch (no scipy dependency) as the maximum absolute gap
    between the two empirical CDFs evaluated on the pooled, sorted support. For a
    rank-preserving surrogate this is zero up to floating point.
    """
    a = np.sort(_as_1d(x))
    b = np.sort(_as_1d(surrogate))
    pooled = np.sort(np.concatenate([a, b]))
    cdf_a = np.searchsorted(a, pooled, side="right") / a.size
    cdf_b = np.searchsorted(b, pooled, side="right") / b.size
    return float(np.max(np.abs(cdf_a - cdf_b)))


def covariance_preservation_rmsd(
    x: FloatArray, surrogate: FloatArray, *, max_lag: int = 8
) -> float:
    """RMSD between the lagged autocovariance sequences of ``x`` and surrogate.

    For univariate series there is no inter-channel covariance, so the relevant
    second-order structure is the autocovariance at lags 0..``max_lag``. A correct
    spectrum-preserving surrogate keeps this sequence close to the original.
    """
    a = _as_1d(x)
    b = _as_1d(surrogate)
    max_lag = int(min(max_lag, a.size - 1))

    def _autocov(z: FloatArray) -> FloatArray:
        zc = z - z.mean()
        return np.array([float(np.mean(zc[: z.size - k] * zc[k:])) for k in range(max_lag + 1)])

    ca = _autocov(a)
    cb = _autocov(b)
    return float(np.sqrt(np.mean((ca - cb) ** 2)))


def detect_tisean() -> str:
    """Return the path to a real TISEAN ``surrogates`` binary, or a sentinel.

    Never fabricates availability: if the binary is not on ``PATH`` (the CI case)
    the string ``"not_available_on_path"`` is returned and no TISEAN claim may be
    made downstream.
    """
    found = shutil.which("surrogates") or shutil.which("endtoend")
    return found or "not_available_on_path"


def compare_against_reference(
    x: FloatArray,
    *,
    seed: int = 0,
    n_iter: int = 100,
    spectrum_gap_tol: float = 0.05,
    marginal_tol: float = 1e-9,
    covariance_gap_tol: float = 0.10,
) -> dict[str, Any]:
    """Run BSFF MIAAFT and this reference IAAFT on the same input and compare.

    Both engines are driven with the same seed and iteration budget on the same
    1-D fixture. The returned dict reports, side by side, the amplitude-spectrum
    error, marginal KS distance, and autocovariance RMSD for each engine, the
    spectrum-error *gap* between them, the stability of the rank-order surrogate
    p-value under each engine, and a boolean ``agrees`` summarising the tolerance
    checks. TISEAN availability is reported honestly and never assumed.

    Tolerances
    ----------
    spectrum_gap_tol
        Max allowed absolute difference between the two engines' relative
        amplitude-spectrum errors.
    marginal_tol
        Max allowed KS distance for each engine (rank-preserving surrogates
        should be at machine precision).
    covariance_gap_tol
        Max allowed absolute difference between the two engines' autocovariance
        RMSDs.
    """
    # Local import keeps this module importable even if surrogate_engine changes;
    # the comparison entry point is the only place that touches the BSFF engine.
    from bsff.surrogate_engine import miaaft_surrogate, rank_order_surrogate_test

    data = _as_1d(x)

    bsff_surr = np.asarray(miaaft_surrogate(data, n_iter=n_iter, seed=seed), dtype=float).reshape(
        -1
    )
    ref_surr, ref_diag = iaaft_surrogate(data, n_iter=n_iter, seed=seed, return_diagnostics=True)
    ref_surr = np.asarray(ref_surr, dtype=float).reshape(-1)

    spectrum_bsff = amplitude_spectrum_rel_error(data, bsff_surr)
    spectrum_ref = amplitude_spectrum_rel_error(data, ref_surr)
    marginal_bsff = marginal_ks_distance(data, bsff_surr)
    marginal_ref = marginal_ks_distance(data, ref_surr)
    cov_bsff = covariance_preservation_rmsd(data, bsff_surr)
    cov_ref = covariance_preservation_rmsd(data, ref_surr)

    spectrum_gap = abs(spectrum_bsff - spectrum_ref)
    covariance_gap = abs(cov_bsff - cov_ref)

    # Rank-order p-value stability: run BSFF's own test (the reference IAAFT is
    # used as the inner generator below to show the verdict path is engine-robust).
    bsff_test = rank_order_surrogate_test(data, n_surrogates=19, seed=seed, max_iter=n_iter)
    p_bsff = float(cast(float, bsff_test["p_value"]))
    p_ref = _reference_rank_order_p(data, n_surrogates=19, seed=seed, n_iter=n_iter)
    p_stability = abs(p_bsff - p_ref)

    agrees = bool(
        spectrum_gap <= spectrum_gap_tol
        and marginal_bsff <= marginal_tol
        and marginal_ref <= marginal_tol
        and covariance_gap <= covariance_gap_tol
    )

    return {
        "schema": "bsff.reference_surrogate.v1",
        "n_samples": int(data.size),
        "seed": int(seed),
        "n_iter": int(n_iter),
        "amplitude_spectrum_error_bsff": spectrum_bsff,
        "amplitude_spectrum_error_reference": spectrum_ref,
        "spectrum_error_gap": spectrum_gap,
        "marginal_ks_bsff": marginal_bsff,
        "marginal_ks_reference": marginal_ref,
        "covariance_rmsd_bsff": cov_bsff,
        "covariance_rmsd_reference": cov_ref,
        "covariance_rmsd_gap": covariance_gap,
        "rank_order_p_bsff": p_bsff,
        "rank_order_p_reference": p_ref,
        "rank_correlation_p_stability": p_stability,
        "reference_converged": bool(ref_diag["converged"]),
        "reference_n_iter_actual": int(ref_diag["n_iter_actual"]),
        "tisean_reference": detect_tisean(),
        "tisean_was_run": False,
        "tolerances": {
            "spectrum_gap_tol": spectrum_gap_tol,
            "marginal_tol": marginal_tol,
            "covariance_gap_tol": covariance_gap_tol,
        },
        "agrees": agrees,
    }


def _reference_rank_order_p(x: FloatArray, *, n_surrogates: int, seed: int, n_iter: int) -> float:
    """Rank-order surrogate p-value using the reference IAAFT as the generator.

    Mirrors the one-sided ``(exceed + 1) / (n + 1)`` estimator used by BSFF so the
    two p-values are directly comparable; the discriminating statistic is the same
    lag-1 quadratic correlation BSFF uses by default.
    """
    data = _as_1d(x)
    rng = np.random.default_rng(seed)

    def _stat(z: FloatArray) -> float:
        a = z[:-1] ** 2
        b = z[1:]
        if np.std(a) < 1e-12 or np.std(b) < 1e-12:
            return 0.0
        return float(abs(np.corrcoef(a, b)[0, 1]))

    original = _stat(data)
    exceed = 0
    for _ in range(n_surrogates):
        s = iaaft_surrogate(data, n_iter=n_iter, seed=int(rng.integers(0, 2**32 - 1)))
        if _stat(np.asarray(s, dtype=float)) >= original:
            exceed += 1
    return float((exceed + 1) / (n_surrogates + 1))
