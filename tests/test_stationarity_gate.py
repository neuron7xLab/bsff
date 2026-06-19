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
