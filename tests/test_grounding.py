# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (c) 2026 Yaroslav Vasylenko / neuron7xLab
"""Grounding gate: prose numbers must re-derive from their artifacts."""

from __future__ import annotations

import importlib.util
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def _mod():
    spec = importlib.util.spec_from_file_location(
        "verify_grounding", ROOT / "tools" / "verify_grounding.py"
    )
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


def test_real_grounding_passes():
    assert _mod().check() == []


def test_wrong_number_is_caught():
    m = _mod()
    bogus = [
        {
            "label": "bogus",
            "doc": "docs/MANUSCRIPT.md",
            "source": "research/bci_generalization/result_bnci2014_001_sub1-2.json",
            "key": "within_mean",
            "dp": 9,  # full precision -> won't appear in the doc
        }
    ]
    failures = m.check(facts=bogus, readme_check=False)
    assert failures and "ungrounded/stale" in failures[0]


def test_grounding_tool_exit_zero():
    r = subprocess.run(
        [sys.executable, str(ROOT / "tools" / "verify_grounding.py")],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )
    assert r.returncode == 0, r.stdout + r.stderr
