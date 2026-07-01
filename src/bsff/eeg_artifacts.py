# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (c) 2026 Yaroslav Vasylenko / neuron7xLab
"""Deterministic, seeded EEG artifact and leakage generators.

This module is a *falsification battery*: it produces realistic EEG recording
artifacts (ocular, muscular, mains, drift, dead channels) and three classic
data-leakage configurations on top of a clean base signal, and pairs each one
with the *actual* BSFF detection / caveat behavior so the test suite can assert
machine-readable expectations rather than aspirations.

Two families are provided.

Waveform artifacts
    Return a ``(n_channels, n_samples)`` float array. They corrupt a clean AR(1)
    base (reused from :mod:`bsff.synthetic`) with a physically motivated artifact.
    The expected BSFF behavior of each was verified against
    :func:`bsff.stationarity.check_stationarity` and
    :func:`bsff.surrogate_engine.rank_order_surrogate_test`:

    * ``ocular_blink`` is a dense, high-amplitude transient train: it shifts the
      local level enough that KPSS **flags** every channel *and* the IAAFT
      rank-order surrogate **rejects** its null (non-Gaussian transient structure
      the spectral surrogate cannot reproduce). It is caught by both paths.
    * ``emg_burst`` is a *sparse* high-frequency broadband burst on an
      autocorrelated base. This is the honest negative result: neither KPSS (a
      *level* test, ``regression="c"``) nor the IAAFT rank-order surrogate flags
      it. Its observable signature is elevated high-frequency band power, i.e. a
      spectral caveat — BSFF's waveform falsification paths do not catch it.
    * ``line_noise`` is a *stationary* periodic component: KPSS reports
      stationary and the spectral surrogate does **not** reject. The honest
      caveat is spectral (a narrowband peak), not stationarity.
    * ``slow_drift`` is *level*-non-stationary: KPSS **flags** every channel.
    * ``channel_dropout`` zeroes channels: KPSS marks them ``constant_channel``
      (stationary by definition); the artifact is detectable as a zero-variance
      channel, not by a falsification verdict.

Leakage generators
    Return ``(features, labels, group_ids)``. Each is detectable by a BSFF
    leakage detector (block-design temporal autocorrelation or label-permutation
    mutual-information), which causes :func:`bsff.verdict_engine.evaluate_claim`
    to short-circuit to ``REFUTED``.

All generators are deterministic given ``seed`` and use numpy only.
"""

from __future__ import annotations

from collections.abc import Callable

import numpy as np
from numpy.typing import NDArray

from .synthetic import ar1_multichannel, block_design_dataset

FloatArray = NDArray[np.float64]
IntArray = NDArray[np.int64]
LeakageDataset = tuple[FloatArray, IntArray, IntArray]


def _clean_base(n_channels: int, n_samples: int, seed: int) -> FloatArray:
    """Standardized clean multichannel EEG base (reuses synthetic AR(1))."""
    if n_channels < 1:
        raise ValueError("n_channels must be >= 1")
    if n_samples < 16:
        raise ValueError("n_samples must be >= 16")
    return ar1_multichannel(n_channels=n_channels, n_samples=n_samples, seed=seed)


def ocular_blink(
    n_channels: int,
    n_samples: int,
    *,
    fs: float = 250.0,
    seed: int = 101,
    n_blinks: int = 8,
    amplitude: float = 10.0,
    width_ms: float = 80.0,
) -> FloatArray:
    """Frontal ocular-blink transients on a clean base.

    Models eye blinks as low-frequency, high-amplitude Gaussian transients that
    are strongest at frontal channels (channel 0, with reduced coupling onto
    channel 1) and decay toward posterior channels. With the default dense,
    high-amplitude train the local level shifts enough that KPSS flags every
    channel *and* the IAAFT surrogate null is rejected (non-Gaussian structure):
    the blink is caught by both BSFF waveform paths.

    Parameters
    ----------
    n_channels, n_samples
        Output shape ``(n_channels, n_samples)``.
    fs
        Sampling rate in Hz (controls transient width in samples).
    seed
        Deterministic seed for blink onsets and the base.
    n_blinks
        Number of blink events.
    amplitude
        Peak transient amplitude (in standardized base units).
    width_ms
        Gaussian transient standard deviation in milliseconds.
    """
    base = _clean_base(n_channels, n_samples, seed)
    rng = np.random.default_rng(seed + 1)
    sigma = max(1.0, width_ms * 1e-3 * fs)
    onsets = rng.integers(int(2 * sigma), n_samples - int(2 * sigma) - 1, size=n_blinks)
    t = np.arange(n_samples)
    transient = np.zeros(n_samples, dtype=float)
    for onset in onsets:
        transient += amplitude * np.exp(-((t - onset) ** 2) / (2.0 * sigma**2))
    out: FloatArray = base.copy()
    out[0] += transient
    if n_channels > 1:
        out[1] += 0.6 * transient
    for ch in range(2, n_channels):
        out[ch] += (0.25 / ch) * transient
    return out


def emg_burst(
    n_channels: int,
    n_samples: int,
    *,
    fs: float = 250.0,
    seed: int = 202,
    n_bursts: int = 3,
    burst_ms: float = 600.0,
    amplitude: float = 4.0,
) -> FloatArray:
    """High-frequency broadband muscle (EMG) bursts on a clean base.

    Models muscle activity as time-windowed high-frequency broadband noise added
    to a temporal (e.g. posterior/temporal) channel. This is the honest negative
    case: a sparse EMG burst on an autocorrelated base is flagged by *neither*
    KPSS (level test) nor the IAAFT rank-order surrogate. Its detectable
    signature is elevated high-frequency band power (a spectral caveat).

    Parameters
    ----------
    n_bursts
        Number of burst windows.
    burst_ms
        Duration of each burst window in milliseconds.
    amplitude
        Scale of the broadband noise within a burst.
    """
    base = _clean_base(n_channels, n_samples, seed)
    rng = np.random.default_rng(seed + 1)
    burst_len = max(8, int(burst_ms * 1e-3 * fs))
    burst = np.zeros(n_samples, dtype=float)
    for _ in range(n_bursts):
        onset = int(rng.integers(0, max(1, n_samples - burst_len)))
        window = np.zeros(n_samples, dtype=float)
        window[onset : onset + burst_len] = 1.0
        burst += window * amplitude * rng.normal(size=n_samples)
    out: FloatArray = base.copy()
    target = n_channels - 1
    out[target] += burst
    return out


def line_noise(
    n_channels: int,
    n_samples: int,
    *,
    fs: float = 250.0,
    seed: int = 303,
    line_hz: float = 50.0,
    amplitude: float = 1.5,
) -> FloatArray:
    """Narrowband mains (line) interference on a clean base.

    Models power-line interference as a stationary sinusoid at ``line_hz``
    (50 Hz Europe / 60 Hz US) shared across all channels with a small per-channel
    phase jitter. This is a *stationary* periodic component: KPSS reports
    stationary and the spectral surrogate does **not** reject — the honest BSFF
    caveat is spectral (a narrowband power peak), not a falsification verdict.
    """
    if not (0.0 < line_hz < 0.5 * fs):
        raise ValueError("line_hz must satisfy 0 < line_hz < fs/2")
    base = _clean_base(n_channels, n_samples, seed)
    rng = np.random.default_rng(seed + 1)
    t = np.arange(n_samples) / fs
    out: FloatArray = base.copy()
    for ch in range(n_channels):
        phase = float(rng.uniform(0.0, 2.0 * np.pi))
        out[ch] += amplitude * np.sin(2.0 * np.pi * line_hz * t + phase)
    return out


def slow_drift(
    n_channels: int,
    n_samples: int,
    *,
    fs: float = 250.0,
    seed: int = 404,
    drift_hz: float = 0.1,
    amplitude: float = 3.0,
) -> FloatArray:
    """Low-frequency baseline wander (drift) on a clean base.

    Models sweat / electrode-impedance baseline wander as a very-low-frequency
    sinusoid (sub-Hz) added to all channels. This is *level*-non-stationary:
    KPSS **flags** every channel, which surfaces in BSFF as a stationarity-gate
    caveat on the verdict.
    """
    if drift_hz <= 0.0:
        raise ValueError("drift_hz must be positive")
    base = _clean_base(n_channels, n_samples, seed)
    rng = np.random.default_rng(seed + 1)
    t = np.arange(n_samples) / fs
    out: FloatArray = base.copy()
    for ch in range(n_channels):
        phase = float(rng.uniform(0.0, 2.0 * np.pi))
        out[ch] += amplitude * np.sin(2.0 * np.pi * drift_hz * t + phase)
    return out


def channel_dropout(
    n_channels: int,
    n_samples: int,
    *,
    fs: float = 250.0,
    seed: int = 505,
    dropout_channels: tuple[int, ...] | None = None,
) -> FloatArray:
    """One or more flatlined (zeroed) channels on a clean base.

    Models a dead / disconnected electrode by zeroing whole channels. A zeroed
    channel is constant, hence *stationary by definition*: BSFF's KPSS gate marks
    it ``constant_channel`` rather than flagging it. The artifact is detectable as
    a zero-variance channel, not via a falsification verdict.

    Parameters
    ----------
    dropout_channels
        Channel indices to zero. Defaults to the middle channel (or channel 0 if
        single-channel).
    """
    base = _clean_base(n_channels, n_samples, seed)
    if dropout_channels is None:
        dropout_channels = (n_channels // 2,) if n_channels > 1 else (0,)
    out: FloatArray = base.copy()
    for ch in dropout_channels:
        if not (0 <= ch < n_channels):
            raise ValueError(f"dropout channel {ch} out of range for {n_channels} channels")
        out[ch] = 0.0
    return out


def session_split_leakage(
    *,
    n_sessions: int = 4,
    session_len: int = 50,
    seed: int = 606,
) -> LeakageDataset:
    """Per-session bias that aligns with the label (subject/session leakage).

    Each session contributes a constant per-session bias feature, and the binary
    label is constant within a session (label == session parity). A feature that
    encodes session identity therefore trivially predicts the label, which the
    label-permutation mutual-information detector flags; the block-design detector
    flags it as well because every group has 100% label purity. ``group_ids`` are
    the session indices.

    Returns ``(features, labels, group_ids)``.
    """
    if n_sessions < 2:
        raise ValueError("n_sessions must be >= 2")
    if session_len < 2:
        raise ValueError("session_len must be >= 2")
    rng = np.random.default_rng(seed)
    n = n_sessions * session_len
    group_ids = np.repeat(np.arange(n_sessions), session_len).astype(np.int64)
    labels = np.repeat(np.arange(n_sessions) % 2, session_len).astype(np.int64)
    session_bias = np.repeat(rng.normal(scale=2.0, size=n_sessions), session_len)
    features = np.column_stack(
        [
            session_bias + 0.1 * rng.normal(size=n),
            rng.normal(size=n),
        ]
    ).astype(float)
    return features, labels, group_ids


def block_design_leakage(
    *,
    n_blocks: int = 16,
    block_len: int = 32,
    seed: int = 707,
) -> LeakageDataset:
    """Temporal block-design leakage (thin wrapper over the synthetic fixture).

    Reuses :func:`bsff.synthetic.block_design_dataset`: contiguous temporal blocks
    carry a single label, so within-block label purity is ~1 and the label
    transition rate is low. The block-design temporal-autocorrelation detector
    flags it. ``group_ids`` are the block indices.

    Returns ``(features, labels, group_ids)``.
    """
    return block_design_dataset(n_blocks=n_blocks, block_len=block_len, seed=seed)


def global_normalization_leakage(
    *,
    n_samples: int = 200,
    seed: int = 808,
    separation: float = 0.5,
    noise: float = 0.8,
) -> LeakageDataset:
    """Global normalization applied across the whole set before splitting.

    A discriminative feature is standardized using statistics computed over the
    *entire* dataset (train+test pooled) rather than train-only. The pooled
    z-scoring leaks test-set scale into training and preserves a label-correlated
    feature, which the label-permutation mutual-information detector flags.
    ``group_ids`` are per-sample (no grouping structure), so subject/block
    splitting alone would not have prevented this leakage.

    Returns ``(features, labels, group_ids)``.
    """
    if n_samples < 16:
        raise ValueError("n_samples must be >= 16")
    rng = np.random.default_rng(seed)
    labels = (np.arange(n_samples) % 2).astype(np.int64)
    raw = np.where(labels == 1, separation, -separation) + noise * rng.normal(size=n_samples)
    nuisance = rng.normal(size=n_samples)
    pooled = np.column_stack([raw, nuisance]).astype(float)
    # Global (whole-set) standardization — the leakage: stats span train + test.
    normalized = (pooled - pooled.mean(axis=0)) / (pooled.std(axis=0) + 1e-12)
    group_ids = np.arange(n_samples).astype(np.int64)
    return normalized, labels, group_ids


WaveformGenerator = Callable[..., FloatArray]
LeakageGenerator = Callable[..., LeakageDataset]

EEG_ARTIFACTS: dict[str, WaveformGenerator | LeakageGenerator] = {
    "ocular_blink": ocular_blink,
    "emg_burst": emg_burst,
    "line_noise": line_noise,
    "slow_drift": slow_drift,
    "channel_dropout": channel_dropout,
    "session_split_leakage": session_split_leakage,
    "block_design_leakage": block_design_leakage,
    "global_normalization_leakage": global_normalization_leakage,
}

# Machine-readable expected BSFF behavior per artifact. Every field below was
# verified against bsff.stationarity.check_stationarity,
# bsff.surrogate_engine.rank_order_surrogate_test, bsff.leakage_detector, and
# bsff.verdict_engine.evaluate_claim before being recorded here. Do NOT assert a
# behavior that has not been reproduced against those modules.
_EXPECTED: dict[str, dict[str, object]] = {
    "ocular_blink": {
        "kind": "waveform",
        "physical": "low-frequency high-amplitude frontal ocular transients",
        "kpss_flags_nonstationarity": True,
        "surrogate_rejects_null": True,
        "primary_path": "stationarity_and_surrogate",
        "caveat": "nonstationarity",
        "note": (
            "Dense high-amplitude transient train: KPSS flags every channel and the "
            "IAAFT rank-order surrogate also rejects its null. Caught by both paths."
        ),
    },
    "emg_burst": {
        "kind": "waveform",
        "physical": "high-frequency broadband muscle bursts",
        "kpss_flags_nonstationarity": False,
        "surrogate_rejects_null": False,
        "primary_path": "spectral",
        "caveat": "spectral",
        "note": (
            "Honest negative: a sparse EMG burst on an autocorrelated base is flagged by "
            "neither KPSS nor the IAAFT surrogate. Signature is elevated high-frequency "
            "band power only — BSFF's waveform falsification paths do not catch it."
        ),
    },
    "line_noise": {
        "kind": "waveform",
        "physical": "narrowband mains interference (50/60 Hz)",
        "kpss_flags_nonstationarity": False,
        "surrogate_rejects_null": False,
        "primary_path": "spectral",
        "caveat": "spectral",
        "note": (
            "Stationary periodic component: KPSS reports stationary and the spectral "
            "surrogate does not reject. Caveat is a narrowband spectral peak, not a verdict."
        ),
    },
    "slow_drift": {
        "kind": "waveform",
        "physical": "sub-Hz baseline wander / electrode drift",
        "kpss_flags_nonstationarity": True,
        "surrogate_rejects_null": False,
        "primary_path": "stationarity",
        "caveat": "stationarity",
        "note": "Level-non-stationary: KPSS flags all channels, surfacing a stationarity-gate caveat.",
    },
    "channel_dropout": {
        "kind": "waveform",
        "physical": "dead / disconnected electrode (flatlined channel)",
        "kpss_flags_nonstationarity": False,
        "surrogate_rejects_null": None,
        "primary_path": "constant_channel",
        "caveat": "constant_channel",
        "note": (
            "Zeroed channel is constant => stationary by definition; KPSS marks it "
            "'constant_channel'. Detectable as zero variance, not via a falsification verdict."
        ),
    },
    "session_split_leakage": {
        "kind": "leakage",
        "physical": "per-session bias aligned with label (subject/session leakage)",
        "leakage_detector": "feature_selection_or_block_design",
        "leakage_flagged": True,
        "verdict": "REFUTED",
        "note": "Session-identity feature predicts the label; MI/permutation and block-design detectors flag it.",
    },
    "block_design_leakage": {
        "kind": "leakage",
        "physical": "contiguous temporal blocks carrying one label each",
        "leakage_detector": "block_design",
        "leakage_flagged": True,
        "verdict": "REFUTED",
        "note": "High within-block label purity + low transition rate => block-design detector flags it.",
    },
    "global_normalization_leakage": {
        "kind": "leakage",
        "physical": "normalization stats computed over the whole set before splitting",
        "leakage_detector": "feature_selection",
        "leakage_flagged": True,
        "verdict": "REFUTED",
        "note": "Whole-set z-scoring leaks test-set scale; the label-permutation MI detector flags it.",
    },
}


def expected_behavior(name: str) -> dict[str, object]:
    """Return the verified expected BSFF behavior for an artifact.

    The returned dict is a copy describing the *actual* BSFF detection / caveat
    behavior (verified against the engine), keyed by fields such as ``kind``,
    ``caveat``, ``surrogate_rejects_null``, ``leakage_flagged`` and ``verdict``.

    Raises
    ------
    KeyError
        If ``name`` is not a registered artifact.
    """
    if name not in _EXPECTED:
        raise KeyError(f"unknown artifact {name!r}; known: {sorted(_EXPECTED)}")
    return dict(_EXPECTED[name])
