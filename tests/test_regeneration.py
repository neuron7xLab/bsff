# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (c) 2026 Yaroslav Vasylenko / neuron7xLab
"""The generated surfaces are a convergent fixpoint: regeneration is idempotent."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

pytest.importorskip("yaml")

pytestmark = pytest.mark.slow  # runs the full generator cascade

ROOT = Path(__file__).resolve().parents[1]
TOOL = ROOT / "tools" / "regenerate.py"


def test_system_is_at_fixpoint():
    r = subprocess.run(
        [sys.executable, str(TOOL), "--check"],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )
    assert r.returncode == 0, r.stdout + r.stderr
    assert "at fixpoint" in r.stdout


def test_regeneration_is_idempotent():
    r = subprocess.run(
        [sys.executable, str(TOOL), "--verify-idempotent"],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )
    assert r.returncode == 0, r.stdout + r.stderr
    assert "changed nothing" in r.stdout
