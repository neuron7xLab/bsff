# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (c) 2026 Yaroslav Vasylenko / neuron7xLab
"""Analytical reference validation for the surrogate engines.

TISEAN is the de-facto reference for amplitude-adjusted surrogates, but shelling
out to its CLI is not reproducible inside a hermetic CI. Instead we validate the
only property that the multivariate null model must preserve in expectation: the
lag-0 channel covariance. Over an ensemble, the mean surrogate covariance must
converge to the original covariance. This is a closed-form, dependency-free
oracle — no external binary, fully deterministic under fixed seeds.
"""

from __future__ import annotations

import numpy as np

from bsff.surrogate_engine import miaaft_surrogate, var_phase_randomized_surrogate
from bsff.synthetic import ar1_multichannel

_ENSEMBLE = 20


def _relative_covariance_error(original: np.ndarray, surrogates: list[np.ndarray]) -> float:
    sigma_original = np.cov(original)
    sigma_mean = np.mean([np.cov(s) for s in surrogates], axis=0)
    return float(np.linalg.norm(sigma_mean - sigma_original) / np.linalg.norm(sigma_original))


def test_miaaft_mean_covariance_matches_reference_over_ensemble():
    x = ar1_multichannel(n_channels=8, n_samples=4096, seed=42)
    surrogates = [miaaft_surrogate(x, n_iter=100, seed=s) for s in range(_ENSEMBLE)]
    rel_err = _relative_covariance_error(x, surrogates)
    # Measured ~0.0003; 0.05 is a generous, version-stable ceiling.
    assert rel_err < 0.05


def test_var_phase_mean_covariance_matches_reference_over_ensemble():
    x = ar1_multichannel(n_channels=8, n_samples=4096, seed=42)
    surrogates = [var_phase_randomized_surrogate(x, seed=s) for s in range(_ENSEMBLE)]
    rel_err = _relative_covariance_error(x, surrogates)
    # Measured ~0.0027; the whitening/recoloring path preserves Sigma by construction.
    assert rel_err < 0.05
