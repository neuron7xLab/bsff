# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (c) 2026 Yaroslav Vasylenko / neuron7xLab
"""MANIFEST.json must be generated truth, synced to pyproject + STATUS."""

from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def _mod():
    spec = importlib.util.spec_from_file_location(
        "generate_manifest", ROOT / "tools" / "generate_manifest.py"
    )
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


def test_manifest_in_sync():
    r = subprocess.run(
        [sys.executable, str(ROOT / "tools" / "generate_manifest.py"), "--check"],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )
    assert r.returncode == 0, r.stdout + r.stderr


def test_manifest_matches_pyproject_and_status():
    m = _mod()
    committed = json.loads((ROOT / "artifacts" / "MANIFEST.json").read_text())
    core = m.build_core()
    assert committed["version"] == core["version"]
    assert committed["test_count"] == core["test_count"]
    # the stale historical values must never reappear
    assert committed["version"] != "0.1.4"
    assert committed["test_count"] != 80


def test_check_catches_drift(tmp_path, monkeypatch):
    m = _mod()
    bad = tmp_path / "MANIFEST.json"
    core = m.build_core()
    core["version"] = "9.9.9"
    bad.write_text(json.dumps(core))
    monkeypatch.setattr(m, "OUT", bad)
    assert m.main(["--check"]) == 1
