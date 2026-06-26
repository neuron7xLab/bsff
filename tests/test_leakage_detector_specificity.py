# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (c) 2026 Yaroslav Vasylenko / neuron7xLab
"""Calibration: the deep-leakage detectors must hold nominal specificity under nulls.

The rank-order surrogate test is anti-conservative for strongly autocorrelated linear-
Gaussian nulls (finite-N IAAFT bias, Kugiumtzis 2002) — which is why SURVIVED requires a
corroborating Bayes factor (see test_bayesian_corroboration_gate). The deep-leakage
detectors (PLV / cross-frequency MI) use *circular-shift* surrogates instead, which
preserve each signal's own autocorrelation and spectrum and destroy only the cross-signal
relationship — the correct null for "is there coupling beyond chance".

This measures their empirical false-positive rate on independent autocorrelated AR(1)
processes (no coupling, so every flag is false) and pins it at/below the nominal alpha
within Monte-Carlo slack. A leakage flag short-circuits the verdict to REFUTED, so an
anti-conservative detector would manufacture false REFUTED verdicts. Deterministic
(fixed seeds): the flag count is byte-reproducible, this is a calibration assert, not a
flaky test. Marked slow because it runs ~100 surrogate tests per detector per regime.
"""

from __future__ import annotations

import numpy as np
import pytest

from bsff.leakage_deep import detect_cross_frequency_leakage, detect_phase_locking_leakage

FS = 250.0
N = 512
N_SURROGATES = 49
SEEDS = 100
ALPHA = 0.05
# Monte-Carlo upper bound: at SEEDS=100 the Wilson upper bound for a true rate of alpha is
# ~0.11; 0.13 leaves slack for that noise while still catching gross anti-conservativeness
# (e.g. the 11.7% AR(1) false-SURVIVED that motivated the rank-order conjunction gate, or
# worse). A regression that breaks the circular-shift null will blow well past this.
MAX_FPR = 0.13


def _ar1(n: int, phi: float, seed: int) -> np.ndarray:
    rng = np.random.default_rng(seed)
    x = np.zeros(n)
    e = rng.standard_normal(n)
    for i in range(1, n):
        x[i] = phi * x[i - 1] + e[i]
    return x


@pytest.mark.slow
@pytest.mark.parametrize("phi", [0.0, 0.9])
def test_phase_locking_detector_holds_specificity(phi: float) -> None:
    flags = 0
    for s in range(SEEDS):
        x = _ar1(N, phi, 1000 * s + int(phi * 10))
        y = _ar1(N, phi, 7000 * s + int(phi * 10))  # independent of x -> no phase locking
        out = detect_phase_locking_leakage(
            x, y, fs=FS, band=(8.0, 12.0), n_surrogates=N_SURROGATES, alpha=ALPHA, seed=s
        )
        flags += int(out["flagged"])
    fpr = flags / SEEDS
    assert fpr <= MAX_FPR, f"PLV false-positive rate {fpr} (phi={phi}) exceeds {MAX_FPR}"


@pytest.mark.slow
@pytest.mark.parametrize("phi", [0.0, 0.9])
def test_cross_frequency_detector_holds_specificity(phi: float) -> None:
    flags = 0
    for s in range(SEEDS):
        # A single AR(1) process has no genuine phase-amplitude coupling.
        x = _ar1(N, phi, 1000 * s + int(phi * 10))
        out = detect_cross_frequency_leakage(
            x,
            fs=FS,
            phase_band=(4.0, 8.0),
            amp_band=(30.0, 80.0),
            n_surrogates=N_SURROGATES,
            alpha=ALPHA,
            seed=s,
        )
        flags += int(out["flagged"])
    fpr = flags / SEEDS
    assert fpr <= MAX_FPR, f"cross-frequency FPR {fpr} (phi={phi}) exceeds {MAX_FPR}"
