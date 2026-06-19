# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (c) 2026 Yaroslav Vasylenko / neuron7xLab
"""Phase-synchrony and cross-frequency-coupling leakage probes.

Fixtures use band-limited noise (a wandering-phase theta), not pure sinusoids:
a pure tone is the degenerate case where any spectrum-preserving surrogate keeps
the coupling, so it cannot test the surrogate machinery. Realistic broadband
phase is what makes the circular-shift null separate signal from chance.
"""

from __future__ import annotations

import numpy as np
import pytest
from hypothesis import HealthCheck, given, settings
from hypothesis import strategies as st
from hypothesis.extra.numpy import arrays
from scipy.signal import butter, hilbert, sosfiltfilt

from bsff.leakage_deep import (
    detect_cross_frequency_leakage,
    detect_phase_locking_leakage,
    modulation_index,
    phase_locking_value,
)

FS = 250.0
N = 3000


def _bandpass(x, lo, hi):
    sos = butter(4, [lo / (FS / 2), hi / (FS / 2)], btype="band", output="sos")
    return sosfiltfilt(sos, x)


def _theta(seed):
    return _bandpass(np.random.default_rng(seed).normal(size=N), 4, 8)


def test_plv_is_in_unit_interval_and_high_for_shared_source():
    theta = _theta(1)
    rng = np.random.default_rng(2)
    x = theta + 0.5 * rng.normal(size=N)
    y = theta + 0.5 * rng.normal(size=N)
    plv = phase_locking_value(x, y, fs=FS, band=(4, 8))
    assert 0.0 <= plv <= 1.0
    assert plv > 0.4


def test_modulation_index_is_in_unit_interval_and_higher_for_coupled():
    theta = _theta(1)
    ph = np.angle(hilbert(theta))
    gamma = (1 + np.cos(ph)) * np.sin(2 * np.pi * 40 * np.arange(N) / FS)
    pac = theta + gamma + 0.3 * np.random.default_rng(3).normal(size=N)
    noise = np.random.default_rng(4).normal(size=N)
    mi_pac = modulation_index(pac, fs=FS, phase_band=(4, 8), amp_band=(30, 60))
    mi_noise = modulation_index(noise, fs=FS, phase_band=(4, 8), amp_band=(30, 60))
    assert 0.0 <= mi_noise <= mi_pac <= 1.0
    assert mi_pac > 10 * mi_noise


def test_phase_locking_leakage_flags_shared_source_clears_independent():
    theta = _theta(1)
    rng = np.random.default_rng(5)
    x = theta + 0.5 * rng.normal(size=N)
    y = theta + 0.5 * rng.normal(size=N)
    indep = _theta(99) + 0.5 * rng.normal(size=N)
    flagged = detect_phase_locking_leakage(x, y, fs=FS, band=(4, 8), n_surrogates=200, seed=0)
    clean = detect_phase_locking_leakage(x, indep, fs=FS, band=(4, 8), n_surrogates=200, seed=0)
    assert flagged["flagged"] is True and flagged["p_value"] < 0.05
    assert clean["flagged"] is False


def test_cross_frequency_leakage_flags_pac_clears_noise():
    theta = _theta(1)
    ph = np.angle(hilbert(theta))
    gamma = (1 + np.cos(ph)) * np.sin(2 * np.pi * 40 * np.arange(N) / FS)
    pac = theta + gamma + 0.3 * np.random.default_rng(7).normal(size=N)
    noise = np.random.default_rng(8).normal(size=N)
    flagged = detect_cross_frequency_leakage(
        pac, fs=FS, phase_band=(4, 8), amp_band=(30, 60), n_surrogates=200, seed=0
    )
    clean = detect_cross_frequency_leakage(
        noise, fs=FS, phase_band=(4, 8), amp_band=(30, 60), n_surrogates=200, seed=0
    )
    assert flagged["flagged"] is True and flagged["p_value"] < 0.05
    assert clean["flagged"] is False


@given(
    x=arrays(
        np.float64,
        st.integers(64, 256),
        elements=st.floats(-1e2, 1e2, allow_nan=False, allow_infinity=False, width=64),
    )
)
@settings(max_examples=25, deadline=None, suppress_health_check=[HealthCheck.too_slow])
def test_plv_and_mi_always_in_unit_interval(x):
    y = np.roll(x, 3)
    plv = phase_locking_value(x, y, fs=FS, band=(4, 8))
    mi = modulation_index(x, fs=FS, phase_band=(4, 8), amp_band=(30, 60))
    assert 0.0 <= plv <= 1.0 + 1e-9
    assert 0.0 <= mi <= 1.0 + 1e-9


def test_non_finite_input_rejected_fail_closed():
    x = _theta(1).copy()
    x[0] = np.nan
    with pytest.raises(ValueError, match="finite"):
        modulation_index(x, fs=FS, phase_band=(4, 8), amp_band=(30, 60))
    with pytest.raises(ValueError, match="finite"):
        phase_locking_value(x, _theta(2), fs=FS, band=(4, 8))


def test_invalid_band_rejected():
    with pytest.raises(ValueError, match="band"):
        phase_locking_value(_theta(1), _theta(2), fs=FS, band=(8, 4))
    with pytest.raises(ValueError, match="band"):
        modulation_index(_theta(1), fs=FS, phase_band=(4, 8), amp_band=(30, 200))


def test_deep_leakage_flag_short_circuits_claim_to_refuted():
    from bsff.schemas import ClaimSpec
    from bsff.synthetic import henon_series
    from bsff.verdict_engine import evaluate_claim

    theta = _theta(1)
    rng = np.random.default_rng(5)
    x = theta + 0.5 * rng.normal(size=N)
    y = theta + 0.5 * rng.normal(size=N)
    probe = detect_phase_locking_leakage(x, y, fs=FS, band=(4, 8), n_surrogates=200, seed=0)
    assert probe["flagged"] is True

    spec = ClaimSpec(
        claim_id="deep-leakage-refute",
        signal_type="EEG",
        task_type="nonlinear_structure",
        sampling_rate_hz=FS,
        n_channels=1,
        n_samples=768,
        statistic="lagged_quadratic",
        surrogate_count=19,
    )
    verdict = evaluate_claim(
        spec, henon_series(n_samples=768, seed=11), leakage_flags={"phase_locking": probe}
    )
    # A deep-leakage flag must short-circuit to REFUTED before surrogate testing,
    # exactly as a block-design or feature-selection flag does.
    assert verdict.verdict == "REFUTED"
    assert "leakage" in verdict.evidence.get("reason", "")
