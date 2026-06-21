# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (c) 2026 Yaroslav Vasylenko / neuron7xLab
"""Labelled ground-truth EEG-shaped generator for BSFF-CASE-001.

The point of this generator is *not* realism — it is **known truth**. It lets the
case harness demonstrate, where the answer is fixed by construction, that:

* a decoder can score high *within* a subject while the discriminative structure is
  subject-specific and therefore does **not** transfer across subjects (LOSO →
  chance), and
* when a genuinely subject-shared discriminative pattern is present, the same harness
  recovers above-chance leave-one-subject-out accuracy.

The model is faithful to the mechanism that actually inflates within-subject BCI
numbers: band-limited power (mu/beta ERD/ERS) is modulated along channel patterns,
and the *per-subject* pattern is unrelated across subjects. Class separation is by
power (variance), never by sign, so it is recoverable by the same log-variance
features a real motor-imagery decoder uses.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from numpy.typing import NDArray

FloatArray = NDArray[np.float64]
IntArray = NDArray[np.int_]


@dataclass(frozen=True)
class SyntheticConfig:
    """Configuration for one ground-truth cohort.

    ``subject_effect`` injects a *subject-specific* discriminative pattern (decodable
    within a subject, not transferable). ``shared_effect`` injects a *subject-shared*
    pattern (transferable, so LOSO can recover it). The headline falsification config
    sets ``subject_effect`` high and ``shared_effect`` zero.
    """

    n_subjects: int = 9
    trials_per_subject: int = 60
    n_channels: int = 16
    n_times: int = 320  # 2 s at 160 Hz, matching EEGMMI sample rate
    sfreq: float = 160.0
    subject_effect: float = 1.6
    shared_effect: float = 0.0
    noise: float = 1.0
    carrier_hz: float = 11.0  # mu band
    seed: int = 20260621


@dataclass(frozen=True)
class Cohort:
    """An assembled cohort: trials, labels, and subject ids."""

    x: FloatArray  # (n_trials, n_channels, n_times)
    y: IntArray  # (n_trials,) in {0, 1}
    subject: IntArray  # (n_trials,) subject id
    config: SyntheticConfig

    @property
    def n_trials(self) -> int:
        return int(self.x.shape[0])


def _channel_pattern(rng: np.random.Generator, n_channels: int, active: int) -> FloatArray:
    """A non-negative channel weighting with ``active`` dominant channels (unit norm)."""
    idx = rng.choice(n_channels, size=active, replace=False)
    pattern = np.zeros(n_channels, dtype=float)
    pattern[idx] = rng.uniform(0.6, 1.0, size=active)
    norm = float(np.linalg.norm(pattern))
    return pattern / norm if norm > 0 else pattern


def make_cohort(config: SyntheticConfig) -> Cohort:
    """Generate a deterministic labelled cohort from ``config``.

    Class 0 carries extra band power along the "B" patterns; class 1 along the "A"
    patterns. Separation is by power only (sign-free), so log-variance features
    recover it exactly as a real ERD/ERS decoder would.
    """
    rng = np.random.default_rng(config.seed)
    n_ch, n_t = config.n_channels, config.n_times
    t = np.arange(n_t) / config.sfreq

    # Subject-shared discriminative patterns (transferable across subjects).
    shared_a = _channel_pattern(rng, n_ch, active=max(2, n_ch // 4))
    shared_b = _channel_pattern(rng, n_ch, active=max(2, n_ch // 4))

    xs: list[FloatArray] = []
    ys: list[int] = []
    subs: list[int] = []

    half = config.trials_per_subject // 2
    for s in range(config.n_subjects):
        # Subject-specific patterns — unrelated across subjects (the trap).
        subj_a = _channel_pattern(rng, n_ch, active=max(2, n_ch // 4))
        subj_b = _channel_pattern(rng, n_ch, active=max(2, n_ch // 4))
        labels = np.array([0] * half + [1] * (config.trials_per_subject - half), dtype=int)
        labels = rng.permutation(labels)
        for lab in labels:
            # Background EEG-like noise.
            trial = rng.normal(0.0, config.noise, size=(n_ch, n_t))
            # Band-limited carrier with a random phase per trial.
            phase = rng.uniform(0.0, 2.0 * np.pi)
            carrier = np.sin(2.0 * np.pi * config.carrier_hz * t + phase)
            # Class-dependent power modulation. Class 1 -> "A" patterns; class 0 -> "B".
            subj_pat = subj_a if lab == 1 else subj_b
            shared_pat = shared_a if lab == 1 else shared_b
            gain = config.subject_effect * subj_pat + config.shared_effect * shared_pat
            trial += np.outer(gain, carrier)
            xs.append(trial)
            ys.append(int(lab))
            subs.append(s)

    x = np.asarray(xs, dtype=float)
    y = np.asarray(ys, dtype=int)
    subject = np.asarray(subs, dtype=int)
    return Cohort(x=x, y=y, subject=subject, config=config)
