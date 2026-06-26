# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (c) 2026 Yaroslav Vasylenko / neuron7xLab
"""Regression: Tort MI must not report spurious maximal coupling for zero-power signals.

Adversarial probe (2026-06): modulation_index built its phase-amplitude distribution as
``p = mean_amp / (mean_amp.sum() + 1e-12)`` then ``clip(p, 1e-12, None)`` and took the
entropy of that vector. When the band-limited amplitudes underflow the additive epsilon
(a constant/DC signal, a near-zero signal), ``p`` no longer sums to one, the entropy
collapses to ~0, and MI returns 1.0 — maximal phase-amplitude coupling for a signal with
none. Because a leakage flag short-circuits the verdict to REFUTED, a degenerate input
could be falsely refuted. MI now normalizes the distribution (and reports 0 when there is
no measurable band power), matching the Tort 2010 definition.
"""

from __future__ import annotations

import math

import numpy as np
import pytest

from bsff.leakage_deep import detect_cross_frequency_leakage, modulation_index

FS = 250.0
PHASE_BAND = (4.0, 8.0)
AMP_BAND = (30.0, 80.0)
N = 2048


def _mi(x: np.ndarray) -> float:
    return modulation_index(x, fs=FS, phase_band=PHASE_BAND, amp_band=AMP_BAND)


@pytest.mark.parametrize(
    "name,signal",
    [
        ("constant", np.full(N, 2.0)),
        ("zeros", np.zeros(N)),
        ("tiny_amplitude", 1e-280 * np.random.default_rng(0).standard_normal(N)),
        ("white_noise", np.random.default_rng(1).standard_normal(N)),
    ],
)
def test_zero_power_signal_has_near_zero_mi_not_maximal(name: str, signal: np.ndarray) -> None:
    mi = _mi(signal)
    assert math.isfinite(mi)
    assert 0.0 <= mi <= 1.0
    # The bug returned exactly 1.0 (maximal) here; a signal with no genuine coupling must
    # sit far from the maximum.
    assert mi < 0.01, f"{name}: MI={mi} — spurious coupling on a zero-coupling signal"


def test_exact_constant_and_zero_return_zero() -> None:
    assert _mi(np.full(N, 2.0)) == 0.0
    assert _mi(np.zeros(N)) == 0.0


def test_mi_stays_bounded_across_random_signals() -> None:
    rng = np.random.default_rng(7)
    for _ in range(15):
        x = rng.standard_normal(N) * rng.uniform(1e-6, 1e3)
        mi = _mi(x)
        assert math.isfinite(mi) and 0.0 <= mi <= 1.0


def test_cross_frequency_detector_does_not_flag_a_constant() -> None:
    # A constant carries no coupling: the detector must not flag it, and its reported MI
    # must not be the spurious maximum.
    out = detect_cross_frequency_leakage(
        np.full(N, 2.0), fs=FS, phase_band=PHASE_BAND, amp_band=AMP_BAND, n_surrogates=99
    )
    assert out["flagged"] is False
    assert float(out["modulation_index"]) < 0.01
