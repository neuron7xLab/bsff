# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (c) 2026 Yaroslav Vasylenko / neuron7xLab
from bsff.surrogate_engine import (
    covariance_relative_rmsd,
    miaaft_surrogate,
    var_phase_randomized_surrogate,
)
from bsff.synthetic import ar1_multichannel


def test_miaaft_reports_phase1_convergence_plateau():
    x = ar1_multichannel(n_channels=32, n_samples=1024, seed=42)
    s, diag = miaaft_surrogate(x, max_iter=200, tol=1e-3, seed=42, return_diagnostics=True)
    assert diag["converged"] is True
    assert diag["n_iter_actual"] <= 200
    assert covariance_relative_rmsd(x, s) < 0.35


def test_var_phase_fallback_preserves_covariance_smoke():
    x = ar1_multichannel(n_channels=8, n_samples=1024, seed=12)
    s, diag = var_phase_randomized_surrogate(x, seed=12, return_diagnostics=True)
    assert diag["engine"] == "var_phase_randomized_surrogate"
    assert covariance_relative_rmsd(x, s) < 0.35
