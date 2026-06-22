# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (c) 2026 Yaroslav Vasylenko / neuron7xLab
"""The presented core map stays in sync with the system it describes."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

pytest.importorskip("yaml")

pytestmark = pytest.mark.slow

ROOT = Path(__file__).resolve().parents[1]


def test_core_map_in_sync():
    r = subprocess.run(
        [sys.executable, str(ROOT / "tools" / "build_core.py"), "--check"],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )
    assert r.returncode == 0, r.stdout + r.stderr


def test_apex_verify_all_passes():
    r = subprocess.run(
        [sys.executable, str(ROOT / "tools" / "verify_all.py")],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )
    assert r.returncode == 0, r.stdout + r.stderr
    assert "RECOMMENDATION:" in r.stdout
    assert "verification core" in r.stdout
