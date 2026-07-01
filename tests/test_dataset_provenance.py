# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (c) 2026 Yaroslav Vasylenko / neuron7xLab
"""Dataset provenance guardrails for the R6/R7 path."""

from __future__ import annotations

import json
from pathlib import Path

from bsff.statistics.contracts import assert_valid_dataset_registry

ROOT = Path(__file__).resolve().parents[1]


def _load_registry() -> dict:
    return json.loads((ROOT / "data_registry.json").read_text(encoding="utf-8"))


def test_dataset_registry_is_shape_valid():
    registry = _load_registry()
    assert registry["schema_version"] == "2026.06"
    assert_valid_dataset_registry(registry["datasets"])


def test_dataset_registry_declares_three_r6_evidence_classes():
    datasets = _load_registry()["datasets"]
    assert "synthetic_controlled_v0" in datasets
    assert "bonn_andrzejak_2001_s2" in datasets
    assert "external_replication_dataset_tbd" in datasets


def test_external_replication_dataset_cannot_be_misread_as_complete():
    external = _load_registry()["datasets"]["external_replication_dataset_tbd"]
    assert external["status"] == "external_required"
    assert "not_yet_available" in external["immutable_hash"]
