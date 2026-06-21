# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (c) 2026 Yaroslav Vasylenko / neuron7xLab
"""Surrogates must satisfy the defining IAAFT properties (intrinsic validation)."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import numpy as np

from bsff.surrogate_engine import miaaft_surrogate
from bsff.synthetic import ar1_multichannel, henon_series, white_noise_series

ROOT = Path(__file__).resolve().parents[1]


def _max_sorted_diff(a: np.ndarray, b: np.ndarray) -> float:
    return float(np.max(np.abs(np.sort(a.ravel()) - np.sort(b.ravel()))))


def test_marginal_distribution_is_preserved_exactly():
    # IAAFT rank-matches: the surrogate is a reordering of the original amplitudes.
    for sig in (
        ar1_multichannel(n_channels=4, n_samples=1024, phi=0.75, seed=7),
        henon_series(1024, seed=11)[np.newaxis, :],
        white_noise_series(1024, seed=3)[np.newaxis, :],
    ):
        surr, _ = miaaft_surrogate(sig, max_iter=200, tol=1e-4, seed=42, return_diagnostics=True)
        assert _max_sorted_diff(np.asarray(sig), np.atleast_2d(surr)) <= 1e-9


def test_spectrum_residual_is_small_but_nonzero():
    # ~1% residual is the IAAFT marginal/spectrum trade-off, not a bug.
    sig = ar1_multichannel(n_channels=4, n_samples=1024, phi=0.75, seed=7)
    _, diag = miaaft_surrogate(sig, max_iter=200, tol=1e-4, seed=42, return_diagnostics=True)
    assert 0.0 < float(diag["relative_spectrum_error"]) < 0.05


def test_covariance_is_preserved():
    sig = ar1_multichannel(n_channels=4, n_samples=1024, phi=0.75, seed=7)
    _, diag = miaaft_surrogate(sig, max_iter=200, tol=1e-4, seed=42, return_diagnostics=True)
    assert float(diag["covariance_relative_rmsd"]) < 0.05
    assert bool(diag["converged"]) is True


def test_fidelity_tool_passes():
    result = subprocess.run(
        [sys.executable, str(ROOT / "tools" / "validate_surrogate_fidelity.py"), "--quick"],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )
    assert result.returncode == 0, result.stdout + result.stderr
