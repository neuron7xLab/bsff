# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (c) 2026 Yaroslav Vasylenko / neuron7xLab
from __future__ import annotations

import hashlib
import json
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]


def test_validation_corpus_manifest_matches_artifact() -> None:
    manifest_path = ROOT / "data" / "validation" / "bsff_validation_corpus_manifest.json"
    manifest = json.loads(manifest_path.read_text())
    artifact = ROOT / manifest["artifact"]
    digest = hashlib.sha256(artifact.read_bytes()).hexdigest()
    assert digest == manifest["sha256"]
    assert manifest["synthetic_only"] is True
    assert manifest["clinical_data"] is False


def test_validation_corpus_contains_expected_arrays() -> None:
    manifest = json.loads(
        (ROOT / "data" / "validation" / "bsff_validation_corpus_manifest.json").read_text()
    )
    arrays = np.load(ROOT / manifest["artifact"])
    assert set(arrays.files) == set(manifest["arrays"])
    assert arrays["ar1_null_bank"].shape == (16, 32, 1024)
    assert arrays["correlated_linear_null_bank"].shape == (16, 32, 1024)
    assert arrays["nonstationary_walk_bank"].shape == (8, 32, 1024)
    assert arrays["gaussian_noise_bank"].shape == (32, 32, 1024)
    assert arrays["block_design_features"].shape == (4096, 32)
    assert arrays["henon_nonlinear_series"].shape == (8192,)
