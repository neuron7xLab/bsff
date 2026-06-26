# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (c) 2026 Yaroslav Vasylenko / neuron7xLab
"""Deep (non-linear) leakage probes: phase synchrony and cross-frequency coupling.

The stationarity (KPSS) and mutual-information probes catch linear and
information-theoretic leakage. They do not catch a model that exploits a
*phase* relationship — e.g. decoding that is really locked to a stimulus marker
or a filter ringing artifact (phase-locking), or that rides spurious
phase-amplitude coupling injected by preprocessing.

These probes measure two canonical non-linear dependencies and decide
significance against circular-shift surrogates, not against an arbitrary
threshold:

* Phase-Locking Value (Lachaux et al., 1999) between a signal and a reference.
* Tort Modulation Index (Tort et al., 2010) for phase-amplitude coupling.

A circular time-shift of the reference / amplitude envelope preserves each
series' own spectrum and marginal while destroying the cross-timing, giving a
principled null for "this coupling is no stronger than chance".
"""

from __future__ import annotations

import numpy as np
from numpy.typing import NDArray
from scipy.signal import butter, hilbert, sosfiltfilt

from .surrogate_engine import min_surrogates_for_alpha

Band = tuple[float, float]
FloatArray = NDArray[np.float64]


def _validate_1d(x: NDArray[np.float64], min_samples: int = 64) -> FloatArray:
    arr = np.asarray(x, dtype=float)
    if arr.ndim == 2 and 1 in arr.shape:
        arr = arr.reshape(-1)
    if arr.ndim != 1:
        raise ValueError("signal must be 1-D (or a single-channel 2-D array)")
    if arr.size < min_samples:
        raise ValueError(f"signal must contain at least {min_samples} samples")
    if not np.all(np.isfinite(arr)):
        raise ValueError("signal must be finite; got NaN or Inf")
    return arr


def _bandpass(x: FloatArray, fs: float, band: Band, order: int = 4) -> FloatArray:
    lo, hi = band
    nyq = 0.5 * fs
    if not (0 < lo < hi < nyq):
        raise ValueError(f"band must satisfy 0 < lo < hi < fs/2; got {band} at fs={fs}")
    sos = butter(order, [lo / nyq, hi / nyq], btype="band", output="sos")
    return np.asarray(sosfiltfilt(sos, x), dtype=float)


def phase_locking_value(x: FloatArray, y: FloatArray, *, fs: float, band: Band) -> float:
    """Phase-locking value in [0, 1] between two signals within a band."""
    xa = _validate_1d(x)
    ya = _validate_1d(y)
    if xa.size != ya.size:
        raise ValueError("x and y must have the same length")
    px = np.angle(hilbert(_bandpass(xa, fs, band)))
    py = np.angle(hilbert(_bandpass(ya, fs, band)))
    return float(np.abs(np.mean(np.exp(1j * (px - py)))))


def modulation_index(
    x: FloatArray, *, fs: float, phase_band: Band, amp_band: Band, n_bins: int = 18
) -> float:
    """Tort phase-amplitude coupling modulation index in [0, 1]."""
    xa = _validate_1d(x)
    if n_bins < 4:
        raise ValueError("n_bins must be >= 4")
    phase = np.angle(hilbert(_bandpass(xa, fs, phase_band)))
    amp = np.abs(hilbert(_bandpass(xa, fs, amp_band)))
    # No measurable oscillatory power in the amplitude band (e.g. a constant/DC signal
    # whose band-limited envelope is only filter ringing at the numerical-noise floor)
    # means the Tort MI is undefined; report zero coupling rather than a spurious value.
    scale = float(np.abs(xa).max())
    if scale == 0.0 or float(amp.max()) <= np.sqrt(np.finfo(float).eps) * scale:
        return 0.0
    edges = np.linspace(-np.pi, np.pi, n_bins + 1)
    idx = np.clip(np.digitize(phase, edges) - 1, 0, n_bins - 1)
    mean_amp = np.array([amp[idx == b].mean() if np.any(idx == b) else 0.0 for b in range(n_bins)])
    total = float(mean_amp.sum())
    if total <= 0.0:
        return 0.0
    # p MUST be a normalized probability distribution (sum == 1) before its entropy is
    # taken; the previous code clipped p AFTER an un-normalized division, so when the
    # amplitudes underflowed the additive epsilon the "distribution" no longer summed to
    # one, collapsing the entropy and yielding a spurious MI of 1.0 (maximal coupling)
    # for signals with zero coupling. Normalize, then add epsilon only inside the log.
    p = mean_amp / total
    entropy = -np.sum(p * np.log(p + 1e-12))
    return float((np.log(n_bins) - entropy) / np.log(n_bins))


def _surrogate_pvalue(observed: float, null: list[float], *, n: int) -> float:
    arr = np.asarray(null, dtype=float)
    return float((np.sum(arr >= observed) + 1) / (n + 1))


def detect_phase_locking_leakage(
    signal: FloatArray,
    reference: FloatArray,
    *,
    fs: float,
    band: Band,
    n_surrogates: int = 200,
    alpha: float = 0.05,
    seed: int = 42,
) -> dict[str, object]:
    """Flag leakage if signal is phase-locked to a reference beyond chance."""
    if not (0 < alpha < 1):
        raise ValueError("alpha must be in (0, 1)")
    minimum = min_surrogates_for_alpha(alpha)
    if n_surrogates < minimum:
        raise ValueError(f"n_surrogates must be >= {minimum} for alpha={alpha}")
    xa = _validate_1d(signal)
    ya = _validate_1d(reference)
    if xa.size != ya.size:
        raise ValueError("signal and reference must have the same length")
    observed = phase_locking_value(xa, ya, fs=fs, band=band)
    rng = np.random.default_rng(seed)
    null = []
    for _ in range(n_surrogates):
        shift = int(rng.integers(1, ya.size))
        null.append(phase_locking_value(xa, np.roll(ya, shift), fs=fs, band=band))
    p_value = _surrogate_pvalue(observed, null, n=n_surrogates)
    return {
        "detector": "phase_locking_value",
        "flagged": bool(p_value < alpha),
        "plv": observed,
        "surrogate_plv_mean": float(np.mean(null)),
        "p_value": p_value,
        "alpha": float(alpha),
        "band_hz": [float(band[0]), float(band[1])],
        "n_surrogates": int(n_surrogates),
    }


def detect_cross_frequency_leakage(
    signal: FloatArray,
    *,
    fs: float,
    phase_band: Band,
    amp_band: Band,
    n_bins: int = 18,
    n_surrogates: int = 200,
    alpha: float = 0.05,
    seed: int = 42,
) -> dict[str, object]:
    """Flag leakage if phase-amplitude coupling exceeds a circular-shift null."""
    if not (0 < alpha < 1):
        raise ValueError("alpha must be in (0, 1)")
    minimum = min_surrogates_for_alpha(alpha)
    if n_surrogates < minimum:
        raise ValueError(f"n_surrogates must be >= {minimum} for alpha={alpha}")
    xa = _validate_1d(signal)
    phase = np.angle(hilbert(_bandpass(xa, fs, phase_band)))
    amp = np.abs(hilbert(_bandpass(xa, fs, amp_band)))
    # No measurable oscillatory power in the amplitude band -> no coupling to test
    # (consistent with modulation_index); report a clean unflagged result instead of the
    # MI of filter ringing.
    scale = float(np.abs(xa).max())
    if scale == 0.0 or float(amp.max()) <= np.sqrt(np.finfo(float).eps) * scale:
        return {
            "detector": "phase_amplitude_coupling",
            "flagged": False,
            "modulation_index": 0.0,
            "surrogate_mi_mean": 0.0,
            "p_value": 1.0,
            "alpha": float(alpha),
            "phase_band_hz": [float(phase_band[0]), float(phase_band[1])],
            "amp_band_hz": [float(amp_band[0]), float(amp_band[1])],
            "n_surrogates": int(n_surrogates),
        }
    edges = np.linspace(-np.pi, np.pi, n_bins + 1)
    idx = np.clip(np.digitize(phase, edges) - 1, 0, n_bins - 1)

    def _mi_from(amp_series: FloatArray) -> float:
        mean_amp = np.array(
            [amp_series[idx == b].mean() if np.any(idx == b) else 0.0 for b in range(n_bins)]
        )
        total = float(mean_amp.sum())
        if total <= 0.0:
            return 0.0
        # Normalize to a probability distribution before taking entropy (see the same
        # fix in modulation_index): an un-normalized clip collapses the entropy and
        # reports spurious maximal coupling for zero-power signals.
        p = mean_amp / total
        entropy = -np.sum(p * np.log(p + 1e-12))
        return float((np.log(n_bins) - entropy) / np.log(n_bins))

    observed = _mi_from(amp)
    rng = np.random.default_rng(seed)
    null = []
    for _ in range(n_surrogates):
        shift = int(rng.integers(1, amp.size))
        null.append(_mi_from(np.roll(amp, shift)))
    p_value = _surrogate_pvalue(observed, null, n=n_surrogates)
    return {
        "detector": "phase_amplitude_coupling",
        "flagged": bool(p_value < alpha),
        "modulation_index": observed,
        "surrogate_mi_mean": float(np.mean(null)),
        "p_value": p_value,
        "alpha": float(alpha),
        "phase_band_hz": [float(phase_band[0]), float(phase_band[1])],
        "amp_band_hz": [float(amp_band[0]), float(amp_band[1])],
        "n_surrogates": int(n_surrogates),
    }
