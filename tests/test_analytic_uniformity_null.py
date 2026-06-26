# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (c) 2026 Yaroslav Vasylenko / neuron7xLab
"""Analytic-uniformity null — an in-repo correctness check that needs no TISEAN.

Under a true linear-Gaussian null the rank-order surrogate p-value must be
Uniform(0,1), so FPR must equal alpha. These tests pin that the committed
artifact confirms three facts — the engine is calibrated on white noise, the
documented IAAFT anti-conservatism is present (and openly measured) on AR(1),
and the conjunction gate restores nominal specificity — and a @slow recompute
proves the gates are not frozen theater.
"""

import importlib.util
import json
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]
TOOL = REPO / "tools" / "analytic_uniformity_null.py"
ARTIFACT = REPO / "artifacts" / "analytic_uniformity_null.json"
ALPHA = 0.05


def _load_tool():
    spec = importlib.util.spec_from_file_location("analytic_uniformity_null", TOOL)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_committed_artifact_confirms_uniformity():
    assert ARTIFACT.exists(), "run tools/analytic_uniformity_null.py"
    d = json.loads(ARTIFACT.read_text())
    assert d["verdict"] == "ANALYTIC_UNIFORMITY_CONFIRMED"
    assert all(d["gates"].values()), d["gates"]


def test_white_null_is_calibrated():
    """On a genuine white null the p-value is uniform and FPR ~ alpha."""
    d = json.loads(ARTIFACT.read_text())
    white = d["nulls"]["white"]
    assert white["ks_pvalue_bare"] >= 0.05, "white-null p-values are not Uniform(0,1)"
    assert abs(white["fpr_bare"] - ALPHA) <= 0.03


def test_ar1_anticonservatism_is_measured_and_corrected():
    """AR(1): bare rank-order over-rejects; the conjunction gate restores FPR<=alpha."""
    d = json.loads(ARTIFACT.read_text())
    ar = d["nulls"]["ar1_phi0.75"]
    assert ar["fpr_bare"] > ALPHA, "documented IAAFT anti-conservatism should be visible"
    assert ar["ks_pvalue_bare"] < 0.05, "AR(1) bare p-values should be non-uniform"
    assert ar["fpr_conjunction"] <= ALPHA + 0.03, "conjunction gate must restore specificity"


@pytest.mark.slow
def test_recompute_holds_gates():
    """A fresh (smaller-N) recompute must reproduce the three qualitative gates.

    Guards against the committed artifact going stale or the engine's calibration
    silently regressing — the gates are live, not frozen.
    """
    tool = _load_tool()
    result = tool.compute(n_draws=60)
    assert result["gates"]["white_null_calibrated"] is True
    assert result["gates"]["ar1_anticonservatism_present"] is True
    assert result["gates"]["conjunction_restores_specificity"] is True
