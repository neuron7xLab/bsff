# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (c) 2026 Yaroslav Vasylenko / neuron7xLab
import numpy as np

from bsff.stationarity import check_stationarity
from bsff.synthetic import ar1_multichannel


def test_stationarity_gate_flags_nonstationary_random_walk():
    rng = np.random.default_rng(7)
    drift = np.cumsum(rng.normal(size=512))
    result = check_stationarity(drift[None, :])
    assert result["all_stationary"] is False
    assert result["n_channels_failed"] == 1


def test_stationarity_gate_accepts_stationary_ar1_fixture():
    x = ar1_multichannel(n_channels=2, n_samples=1024, phi=0.35, seed=2)
    result = check_stationarity(x)
    assert result["all_stationary"] is True


def test_stationarity_gate_fails_closed_below_kpss_p_floor():
    # Regression: statsmodels floors the KPSS p-value at 0.01, so `p_value > alpha`
    # vacuously passed a clearly non-stationary random walk for any alpha < 0.01,
    # silently bypassing the fatal stationarity gate. Below the resolution floor the
    # gate must fail closed (cannot certify stationarity), not wave the signal through.
    rng = np.random.default_rng(7)
    drift = np.cumsum(rng.normal(size=512))[None, :]
    assert check_stationarity(drift, alpha=0.05)["all_stationary"] is False
    assert check_stationarity(drift, alpha=0.005)["all_stationary"] is False
