# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (c) 2026 Yaroslav Vasylenko / neuron7xLab
"""Non-convergence is a contract, not a crash.

When the MIAAFT rank projection cannot plateau within the iteration budget, the
engine must do one of three declared things — warn, fall back to the
covariance-preserving variance-phase surrogate, or raise — never silently emit a
surrogate that pretends it converged. These paths were previously unexercised.
"""

from __future__ import annotations

import numpy as np
import pytest

from bsff.surrogate_engine import miaaft_surrogate
from bsff.synthetic import ar1_multichannel


def _force_nonconvergence(**kwargs):
    x = ar1_multichannel(n_channels=8, n_samples=1024, seed=1)
    # max_iter=1 with an impossibly tight tolerance guarantees no plateau.
    return x, miaaft_surrogate(x, max_iter=1, tol=1e-12, seed=1, return_diagnostics=True, **kwargs)


def test_nonconvergence_warns_by_default():
    _x, (_s, diag) = _force_nonconvergence(fallback="warn")
    assert diag["converged"] is False
    assert "did not plateau" in diag["warning"]


def test_var_phase_fallback_engages_on_nonconvergence():
    x, (surrogate, diag) = _force_nonconvergence(fallback="var_phase")
    assert diag["converged"] is False
    assert "Fallback used" in diag["warning"]
    # The fallback's whole purpose is lag-0 covariance fidelity; it must beat the
    # tolerance a single un-projected MIAAFT iteration could never reach.
    assert diag["covariance_relative_rmsd"] < 0.2
    assert surrogate.shape == x.shape


def test_raise_fallback_raises_on_nonconvergence():
    x = ar1_multichannel(n_channels=8, n_samples=1024, seed=1)
    with pytest.raises(RuntimeError, match="did not plateau"):
        miaaft_surrogate(x, max_iter=1, tol=1e-12, seed=1, fallback="raise")


def test_converged_run_does_not_warn():
    x = ar1_multichannel(n_channels=8, n_samples=1024, seed=1)
    _s, diag = miaaft_surrogate(x, max_iter=200, tol=1e-3, seed=1, return_diagnostics=True)
    assert diag["converged"] is True
    assert diag["warning"] == ""
    assert np.isfinite(diag["covariance_relative_rmsd"])
