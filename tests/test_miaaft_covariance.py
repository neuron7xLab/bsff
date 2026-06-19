# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (c) 2026 Yaroslav Vasylenko / neuron7xLab
import numpy as np

from bsff.surrogate_engine import covariance_rmsd, miaaft_surrogate
from bsff.synthetic import ar1_multichannel


def test_miaaft_preserves_cross_covariance_within_smoke_tolerance():
    x = ar1_multichannel(n_channels=4, n_samples=512, seed=5)
    s, diag = miaaft_surrogate(x, n_iter=35, seed=42, return_diagnostics=True)
    baseline = float(np.sqrt(np.mean(np.cov(x) ** 2)))
    rel = covariance_rmsd(x, s) / (baseline + 1e-12)
    assert rel < 0.35
    assert diag["mean_abs_spectrum_error"] < 2.0
