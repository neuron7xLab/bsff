# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (c) 2026 Yaroslav Vasylenko / neuron7xLab
"""Null + threshold registries: explicit hypotheses and threshold provenance."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

pytest.importorskip("yaml")  # registries are YAML; skip cleanly if PyYAML absent

ROOT = Path(__file__).resolve().parents[1]


def test_null_registry_complete():
    r = subprocess.run(
        [sys.executable, str(ROOT / "tools" / "validate_null_registry.py")],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )
    assert r.returncode == 0, r.stdout + r.stderr


def test_threshold_registry_has_provenance():
    r = subprocess.run(
        [sys.executable, str(ROOT / "tools" / "validate_threshold_registry.py")],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )
    assert r.returncode == 0, r.stdout + r.stderr


def test_every_threshold_has_value_reason_source():
    import yaml

    data = yaml.safe_load((ROOT / "thresholds.yaml").read_text(encoding="utf-8"))
    for name, spec in data["thresholds"].items():
        assert spec.get("value") is not None, name
        assert spec.get("reason"), name
        assert spec.get("source"), name


def test_every_null_has_statement_and_reject_rule():
    import yaml

    data = yaml.safe_load((ROOT / "null_hypotheses.yaml").read_text(encoding="utf-8"))
    for name, spec in data["nulls"].items():
        assert spec.get("statement"), name
        assert spec.get("tested_by"), name
        assert spec.get("reject_if"), name
        assert spec.get("failure_status"), name
