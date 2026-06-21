# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (c) 2026 Yaroslav Vasylenko / neuron7xLab
"""Governed artifacts must not contradict pyproject/STATUS (generic stale-guard)."""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def _mod():
    spec = importlib.util.spec_from_file_location(
        "validate_artifact_schema", ROOT / "tools" / "validate_artifact_schema.py"
    )
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


def test_governed_artifacts_in_truth():
    r = _mod().validate()
    assert r["ok"], r["failures"]
    assert "artifacts/MANIFEST.json" in r["governed"]


def test_drifted_governed_artifact_is_caught(tmp_path, monkeypatch):
    m = _mod()
    d = tmp_path / "artifacts"
    d.mkdir()
    (d / "x.json").write_text(json.dumps({"schema_version": "x/v1", "version": "0.0.0-bogus"}))
    monkeypatch.setattr(m, "ARTIFACT_DIR", d)
    r = m.validate()
    assert not r["ok"]
    assert any("0.0.0-bogus" in f for f in r["failures"])
