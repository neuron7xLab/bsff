# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (c) 2026 Yaroslav Vasylenko / neuron7xLab
from __future__ import annotations

from collections.abc import Callable
from typing import Literal

import numpy as np
from numpy.typing import NDArray

FloatArray = NDArray[np.float64]
FallbackMode = Literal["warn", "var_phase", "raise"]


def _as_2d(x: FloatArray) -> FloatArray:
    arr = np.asarray(x, dtype=float)
    if arr.ndim == 1:
        return arr[None, :]
    if arr.ndim != 2:
        raise ValueError("signal must be shaped (channels, samples) or (samples,)")
    return arr


def _rank_match(values: FloatArray, template: FloatArray) -> FloatArray:
    order = np.argsort(values)
    sorted_template = np.sort(template)
    out = np.empty_like(values)
    out[order] = sorted_template
    return out


def _mean_abs_spectrum_error(current: FloatArray, target_amp: FloatArray) -> float:
    current_amp = np.abs(np.fft.rfft(current, axis=1))
    return float(np.mean(np.abs(current_amp - target_amp)))


def _relative_spectrum_error(current: FloatArray, target_amp: FloatArray) -> float:
    current_amp = np.abs(np.fft.rfft(current, axis=1))
    numerator = np.linalg.norm(current_amp - target_amp)
    denominator = np.linalg.norm(target_amp) + 1e-12
    return float(numerator / denominator)


def covariance_rmsd(a: FloatArray, b: FloatArray) -> float:
    ca = np.cov(_as_2d(a))
    cb = np.cov(_as_2d(b))
    return float(np.sqrt(np.mean((ca - cb) ** 2)))


def covariance_relative_rmsd(a: FloatArray, b: FloatArray) -> float:
    x = _as_2d(a)
    baseline = float(np.sqrt(np.mean(np.cov(x) ** 2)))
    return covariance_rmsd(x, _as_2d(b)) / (baseline + 1e-12)


def var_phase_randomized_surrogate(
    signal: FloatArray,
    *,
    seed: int | None = None,
    return_diagnostics: bool = False,
) -> FloatArray | tuple[FloatArray, dict[str, float | str]]:
    """Fallback surrogate preserving lag-0 covariance through whitening/recoloring.

    This is a defensive path for high-dimensional finite-N failures. It preserves
    the channel covariance much more directly than the MIAAFT rank projection, but
    it is weaker as a nonlinear null model and is therefore reported explicitly.
    """
    x = _as_2d(signal)
    if x.shape[1] < 16:
        raise ValueError("signal must contain at least 16 samples")
    rng = np.random.default_rng(seed)
    mean = x.mean(axis=1, keepdims=True)
    centered = x - mean
    cov = np.cov(centered)
    if np.ndim(cov) == 0:
        cov = np.array([[float(cov)]])
    jitter = 1e-9 * np.eye(cov.shape[0])
    transform = np.linalg.cholesky(cov + jitter)
    white = np.linalg.solve(transform, centered)
    white_fft = np.fft.rfft(white, axis=1)
    phase = rng.uniform(0.0, 2.0 * np.pi, size=white_fft.shape)
    phase[:, 0] = 0.0
    if x.shape[1] % 2 == 0:
        phase[:, -1] = 0.0
    white_surr = np.fft.irfft(np.abs(white_fft) * np.exp(1j * phase), n=x.shape[1], axis=1)
    surrogate = transform @ white_surr + mean
    if return_diagnostics:
        diag = {
            "engine": "var_phase_randomized_surrogate",
            "covariance_rmsd": covariance_rmsd(x, surrogate),
            "covariance_relative_rmsd": covariance_relative_rmsd(x, surrogate),
        }
        return (surrogate if np.asarray(signal).ndim == 2 else surrogate[0], diag)
    return surrogate if np.asarray(signal).ndim == 2 else surrogate[0]


def miaaft_surrogate(
    signal: FloatArray,
    *,
    n_iter: int | None = None,
    max_iter: int | None = 200,
    tol: float = 1e-4,
    seed: int | None = None,
    return_diagnostics: bool = False,
    fallback: FallbackMode = "warn",
) -> FloatArray | tuple[FloatArray, dict[str, float | int | bool | str]]:
    """Generate one multivariate IAAFT-style surrogate.

    The common-phase projection preserves inter-channel phase differences before
    the per-channel rank projection. Finite-N rank matching prevents exact joint
    enforcement of all marginal, auto-spectral, and cross-spectral constraints, so
    convergence is monitored and surfaced instead of buried under heroic prose.
    """
    x = _as_2d(signal)
    if x.shape[1] < 16:
        raise ValueError("signal must contain at least 16 samples")
    if tol <= 0:
        raise ValueError("tol must be positive")
    if n_iter is not None and n_iter <= 0:
        raise ValueError("n_iter must be positive when provided")
    if max_iter is not None and max_iter <= 0:
        raise ValueError("max_iter must be positive when provided")

    # Backward compatibility: historical callers passed n_iter. New production
    # callers should use max_iter + tol so the artifact records convergence.
    iteration_budget = int(
        n_iter if n_iter is not None else max_iter if max_iter is not None else 200
    )

    rng = np.random.default_rng(seed)
    n_channels, n_samples = x.shape
    original_fft = np.fft.rfft(x, axis=1)
    target_amp = np.abs(original_fft)
    target_phase = np.angle(original_fft)

    current = np.vstack([rng.permutation(x[ch]) for ch in range(n_channels)]).astype(float)
    prev_err = np.inf
    last_err = np.inf
    last_delta = np.inf
    converged = False

    for i in range(iteration_budget):
        current_fft = np.fft.rfft(current, axis=1)
        current_phase = np.angle(current_fft)
        delta = current_phase - target_phase
        alpha = np.arctan2(np.sum(np.sin(delta), axis=0), np.sum(np.cos(delta), axis=0))
        new_phase = target_phase + alpha[None, :]
        new_phase[:, 0] = 0.0
        if n_samples % 2 == 0:
            new_phase[:, -1] = 0.0
        spectrally_projected = np.fft.irfft(
            target_amp * np.exp(1j * new_phase), n=n_samples, axis=1
        )
        current = np.vstack(
            [_rank_match(spectrally_projected[ch], x[ch]) for ch in range(n_channels)]
        )
        last_err = _mean_abs_spectrum_error(current, target_amp)
        last_delta = abs(prev_err - last_err)
        if i > 0 and last_delta < tol:
            converged = True
            break
        prev_err = last_err
    else:
        i = iteration_budget - 1

    warning = ""
    output = current
    if not converged:
        warning = f"MIAAFT did not plateau within {iteration_budget} iterations at tol={tol:g}."
        if fallback == "raise":
            raise RuntimeError(warning)
        if fallback == "var_phase":
            fallback_output, fallback_diag = var_phase_randomized_surrogate(
                x,
                seed=seed,
                return_diagnostics=True,
            )
            output = _as_2d(fallback_output)
            warning += f" Fallback used: {fallback_diag['engine']}."

    if not return_diagnostics:
        return output if np.asarray(signal).ndim == 2 else output[0]

    diag: dict[str, float | int | bool | str] = {
        "engine": "miaaft_common_phase",
        "covariance_rmsd": covariance_rmsd(x, output),
        "covariance_relative_rmsd": covariance_relative_rmsd(x, output),
        "mean_abs_spectrum_error": last_err,
        "relative_spectrum_error": _relative_spectrum_error(output, target_amp),
        "convergence_delta": float(last_delta),
        "n_iter_actual": int(i + 1),
        "max_iter": int(iteration_budget),
        "tol": float(tol),
        "converged": bool(converged),
        "warning": warning,
    }
    return (output if np.asarray(signal).ndim == 2 else output[0], diag)


def lagged_quadratic_statistic(series: FloatArray) -> float:
    """Simple nonlinear discriminating statistic for smoke tests."""
    z = np.asarray(series, dtype=float).reshape(-1)
    if z.size < 8:
        raise ValueError("series too short")
    a = z[:-1] ** 2
    b = z[1:]
    if np.std(a) < 1e-12 or np.std(b) < 1e-12:
        return 0.0
    return float(abs(np.corrcoef(a, b)[0, 1]))


def rank_order_surrogate_test(
    signal: FloatArray,
    statistic: Callable[[FloatArray], float] = lagged_quadratic_statistic,
    *,
    n_surrogates: int = 19,
    alpha: float = 0.05,
    seed: int = 123,
) -> dict[str, object]:
    """One-sided non-parametric rank-order surrogate test."""
    minimum = int(1 / alpha) - 1
    if n_surrogates < minimum:
        raise ValueError(f"n_surrogates must be >= {minimum} for alpha={alpha}")
    rng = np.random.default_rng(seed)
    original_stat = float(statistic(np.asarray(signal, dtype=float)))
    surrogate_stats = []
    for _ in range(n_surrogates):
        s = miaaft_surrogate(
            np.asarray(signal, dtype=float),
            n_iter=30,
            tol=1e-4,
            seed=int(rng.integers(0, 2**32 - 1)),
        )
        surrogate_stats.append(float(statistic(np.asarray(s, dtype=float))))
    surrogate_stats_arr = np.array(surrogate_stats, dtype=float)
    exceed = int(np.sum(surrogate_stats_arr >= original_stat))
    p_value = (exceed + 1) / (n_surrogates + 1)
    rejected = bool(p_value <= alpha)
    return {
        "original_statistic": original_stat,
        "surrogate_statistics": surrogate_stats_arr.tolist(),
        "p_value": float(p_value),
        "alpha": alpha,
        "rejected": rejected,
    }
