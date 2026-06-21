# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (c) 2026 Yaroslav Vasylenko / neuron7xLab
"""The committed demonstration page must stay in sync with live verdicts."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

pytest.importorskip("yaml")

pytestmark = pytest.mark.slow  # the demonstration runs the YAML-backed honesty gate

ROOT = Path(__file__).resolve().parents[1]


def test_demonstration_is_in_sync_and_green():
    r = subprocess.run(
        [sys.executable, str(ROOT / "tools" / "build_demonstration.py"), "--check"],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )
    assert r.returncode == 0, r.stdout + r.stderr

    data = json.loads((ROOT / "artifacts" / "demonstration" / "demonstration.json").read_text())
    assert data["honesty_ok"] is True
    assert data["controls_ok"] is True
    assert data["control_negative"] != "SURVIVED"
    assert data["control_positive"] == "SURVIVED"
    assert data["conformance_overall"] in {"CONFORMANT", "PARTIAL"}
    assert data["nonconformant"] == 0
