# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (c) 2026 Yaroslav Vasylenko / neuron7xLab
"""Cluster-robust specificity gate for the Bonn S3 bright-line result.

The headline G2 FPR is a *pooled* Wilson interval over 1000 trials that reuse the
same EEG segments across seeds — a clustered design whose pooled interval can
understate between-seed variance. These tests pin the cluster-robust (seed-
clustered) interval, prove the gate can actually fail on over-dispersed input
(so it is not theater), and confirm the committed artifact stays in sync.
"""

import importlib.util
import json
from pathlib import Path

import numpy as np
import pytest

REPO = Path(__file__).resolve().parents[2]
TOOL = REPO / "tools" / "cluster_robust_specificity.py"
ARTIFACT = REPO / "artifacts" / "bonn_bright_line" / "S3_CLUSTER_ROBUST_CI.json"
S3 = REPO / "artifacts" / "bonn_bright_line" / "S3_CONFIRMATORY_VERDICT.json"


def _load_tool():
    spec = importlib.util.spec_from_file_location("cluster_robust_specificity", TOOL)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


@pytest.fixture(scope="module")
def tool():
    return _load_tool()


def test_artifact_exists_and_matches_recompute(tool):
    """The committed artifact must equal a fresh recompute (fail-closed on drift)."""
    assert ARTIFACT.exists(), "run tools/cluster_robust_specificity.py"
    rendered = json.dumps(tool.compute(), indent=1, sort_keys=True) + "\n"
    assert ARTIFACT.read_text() == rendered


def test_cluster_robust_gate_passes_on_real_data(tool):
    """On the real 10-seed S3 data the cluster-robust interval clears the gate."""
    result = tool.compute()
    assert result["cluster_robust_upper_below_threshold"] is True
    assert result["cluster_bootstrap_upper_below_threshold"] is True
    assert result["cluster_robust_t_95ci"][1] <= 0.05
    assert result["verdict"] == "S3_SPECIFICITY_CLUSTER_ROBUST_BELOW_0.05"


def test_pooled_wilson_in_artifact_matches_committed_s3(tool):
    """The recomputed pooled Wilson interval must match the canonical S3 verdict."""
    s3 = json.loads(S3.read_text())
    result = tool.compute()
    assert result["pooled_wilson_95ci"] == s3["G2"]["wilson_95ci"]
    assert result["pooled_fpr"] == s3["G2"]["ar_null_fpr"]


def test_cluster_interval_does_not_understate_variance(tool):
    """The seed-clustered SE must not be smaller than the iid-binomial SE.

    The whole point of the correction is that clustering can only *widen* the
    honest interval; a design effect below ~1 would mean the cluster analysis
    is cheating the variance back down.
    """
    result = tool.compute()
    assert result["design_effect"] >= 0.95
    assert result["seed_level_se"] >= result["iid_binomial_se"] - 1e-9


def test_gate_fails_closed_on_overdispersed_seeds(tool):
    """Faithfulness probe: an over-dispersed per-seed FPR set must FAIL the gate.

    If this ever passes, the gate is theater. Same pooled mean (~0.03) as the
    real run, but concentrated in a few seeds → large between-seed variance.
    """
    overdispersed = np.array([0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.15, 0.15, 0.0])
    iv = tool.seed_cluster_interval(overdispersed, n_total=1000)
    assert iv["design_effect"] > 2.0
    assert iv["upper_two_sided"] > 0.05  # gate would fail closed


def test_real_data_has_negligible_clustering(tool):
    """Document the measured fact: the real S3 design effect is ~1 (no inflation)."""
    result = tool.compute()
    assert 0.95 <= result["design_effect"] <= 1.5
