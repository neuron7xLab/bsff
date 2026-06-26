# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (c) 2026 Yaroslav Vasylenko / neuron7xLab
"""Operating characteristic: the deep-leakage detectors must hold specificity AND power.

Specificity (no false flags on nulls) and power (detection of genuine leakage) are the two
halves of the calibration — a detector that has one without the other still corrupts the
verdict, since a leakage flag short-circuits to REFUTED: a false flag forges REFUTED, and a
missed flag (fail-open) lets contaminated data falsely SURVIVE.

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


# --- Power (sensitivity): the other half of the operating characteristic. A detector that
# holds specificity but never fires on genuine leakage is a fail-open — contaminated data
# would falsely SURVIVE. These pin the detection rate against textbook positive controls.
# (The first power probe alarmed on a near-zero rate that turned out to be a *malformed*
# synthetic with no explicit low-frequency oscillation; a reference Tort MI agreed with the
# engine, proving the signal — not the detector — was wrong. The canonical signals below
# carry an explicit phase carrier.)
MIN_POWER = 0.80


@pytest.mark.slow
def test_phase_locking_detector_has_power_against_genuine_locking() -> None:
    hits = 0
    for s in range(SEEDS):
        rng = np.random.default_rng(s)
        t = np.arange(N) / FS
        base = np.sin(2 * np.pi * 10.0 * t)
        ref = base + 0.3 * rng.standard_normal(N)
        sig = 0.9 * base + 0.1 * rng.standard_normal(N)  # genuinely phase-locked to ref
        out = detect_phase_locking_leakage(
            sig, ref, fs=FS, band=(8.0, 12.0), n_surrogates=N_SURROGATES, alpha=ALPHA, seed=s
        )
        hits += int(out["flagged"])
    power = hits / SEEDS
    assert power >= MIN_POWER, f"PLV detection rate {power} below {MIN_POWER}"


@pytest.mark.slow
def test_cross_frequency_detector_has_power_against_genuine_pac() -> None:
    hits = 0
    for s in range(SEEDS):
        rng = np.random.default_rng(s)
        t = np.arange(N) / FS
        ph = 2 * np.pi * 6.0 * t
        low = np.sin(ph)  # explicit low-frequency oscillation: the phase carrier
        amp_env = 1.0 + 1.0 * ((np.sin(ph) + 1.0) / 2.0)  # 6 Hz phase modulates 40 Hz amplitude
        sig = low + amp_env * np.sin(2 * np.pi * 40.0 * t) + 0.1 * rng.standard_normal(N)
        out = detect_cross_frequency_leakage(
            sig,
            fs=FS,
            phase_band=(4.0, 8.0),
            amp_band=(30.0, 80.0),
            n_surrogates=N_SURROGATES,
            alpha=ALPHA,
            seed=s,
        )
        hits += int(out["flagged"])
    power = hits / SEEDS
    assert power >= MIN_POWER, f"cross-frequency detection rate {power} below {MIN_POWER}"
