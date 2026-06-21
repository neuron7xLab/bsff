# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (c) 2026 Yaroslav Vasylenko / neuron7xLab
"""Tests for the independent AAFT/IAAFT reference and the TISEAN gate.

These validate three things: (a) the reference AAFT/IAAFT surrogates preserve the
amplitude spectrum and the marginal distribution on a linear-Gaussian fixture;
(b) BSFF's MIAAFT engine and the independent reference IAAFT agree within the
documented tolerances; (c) the ``validate_tisean_reference`` gate exits 0 and
writes its three artifacts.
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import numpy as np

from bsff.reference_surrogate import (
    aaft_surrogate,
    amplitude_spectrum_rel_error,
    compare_against_reference,
    covariance_preservation_rmsd,
    detect_tisean,
    iaaft_surrogate,
    marginal_ks_distance,
)
from bsff.synthetic import ar1_multichannel, henon_series

ROOT = Path(__file__).resolve().parents[1]


def _ar1() -> np.ndarray:
    return ar1_multichannel(n_channels=1, n_samples=512, seed=7)[0]


# --------------------------------------------------------------------------- #
# (a) reference AAFT/IAAFT preserve spectrum and marginal on AR(1)
# --------------------------------------------------------------------------- #


def test_aaft_preserves_marginal_exactly():
    x = _ar1()
    surr = aaft_surrogate(x, seed=0)
    assert surr.shape == x.shape
    # AAFT is a permutation of the original amplitudes -> KS distance is zero.
    assert marginal_ks_distance(x, surr) < 1e-12
    np.testing.assert_allclose(np.sort(surr), np.sort(x), atol=1e-12)


def test_iaaft_preserves_marginal_and_spectrum_on_ar1():
    x = _ar1()
    surr, diag = iaaft_surrogate(x, n_iter=200, seed=0, return_diagnostics=True)
    assert marginal_ks_distance(x, surr) < 1e-12
    # On a linear-Gaussian series IAAFT recovers the amplitude spectrum tightly.
    assert amplitude_spectrum_rel_error(x, surr) < 0.05
    assert diag["converged"] is True
    assert 0 < diag["n_iter_actual"] <= 200


def test_iaaft_is_deterministic_under_seed():
    x = _ar1()
    a = iaaft_surrogate(x, n_iter=50, seed=3)
    b = iaaft_surrogate(x, n_iter=50, seed=3)
    np.testing.assert_array_equal(a, b)


def test_iaaft_improves_spectrum_over_aaft_on_average():
    x = _ar1()
    aaft_err = np.mean(
        [amplitude_spectrum_rel_error(x, aaft_surrogate(x, seed=s)) for s in range(8)]
    )
    iaaft_err = np.mean(
        [amplitude_spectrum_rel_error(x, iaaft_surrogate(x, n_iter=100, seed=s)) for s in range(8)]
    )
    # The whole point of IAAFT: lower amplitude-spectrum error than plain AAFT.
    assert iaaft_err <= aaft_err


def test_covariance_preservation_metric_small_for_surrogate():
    x = _ar1()
    surr = iaaft_surrogate(x, n_iter=100, seed=1)
    assert covariance_preservation_rmsd(x, surr) < 0.05


def test_nonfinite_input_fails_closed():
    bad = np.array([0.0, 1.0, np.nan, 2.0, 3.0, 4.0, 5.0, 6.0])
    try:
        iaaft_surrogate(bad, seed=0)
    except ValueError:
        return
    raise AssertionError("expected ValueError on non-finite input")


# --------------------------------------------------------------------------- #
# (b) BSFF MIAAFT and the reference IAAFT agree
# --------------------------------------------------------------------------- #


def test_bsff_agrees_with_reference_on_ar1():
    x = _ar1()
    report = compare_against_reference(x, seed=7, n_iter=100)
    assert report["agrees"] is True
    assert report["spectrum_error_gap"] <= report["tolerances"]["spectrum_gap_tol"]
    assert report["marginal_ks_bsff"] <= report["tolerances"]["marginal_tol"]
    assert report["marginal_ks_reference"] <= report["tolerances"]["marginal_tol"]
    assert report["covariance_rmsd_gap"] <= report["tolerances"]["covariance_gap_tol"]


def test_bsff_agrees_with_reference_on_henon():
    x = henon_series(n_samples=512, seed=7)
    report = compare_against_reference(x, seed=7, n_iter=100)
    assert report["agrees"] is True
    assert report["rank_correlation_p_stability"] <= 0.2


def test_compare_reports_tisean_honestly():
    x = _ar1()
    report = compare_against_reference(x, seed=0, n_iter=50)
    # TISEAN is never claimed to have run; the path reflects real availability.
    assert report["tisean_was_run"] is False
    assert report["tisean_reference"] == detect_tisean()


# --------------------------------------------------------------------------- #
# (c) the gate script exits 0 and writes the three artifacts
# --------------------------------------------------------------------------- #


def test_validate_gate_exits_zero_and_writes_artifacts(tmp_path):
    proc = subprocess.run(
        [sys.executable, str(ROOT / "tools" / "validate_tisean_reference.py")],
        capture_output=True,
        text=True,
        cwd=str(ROOT),
    )
    assert proc.returncode == 0, proc.stdout + proc.stderr
    for name in ("tisean_validation.json", "tisean_validation.md", "tisean_validation.csv"):
        artifact = ROOT / "artifacts" / name
        assert artifact.exists(), f"missing artifact {name}"
    report = json.loads((ROOT / "artifacts" / "tisean_validation.json").read_text())
    assert report["all_passed"] is True
    assert report["tisean_was_run"] is False
    assert len(report["cases"]) == 2
