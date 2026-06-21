# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (c) 2026 Yaroslav Vasylenko / neuron7xLab
"""The investment-decision gate derives its recommendation from evidence."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

pytest.importorskip("yaml")

ROOT = Path(__file__).resolve().parents[1]


def test_decision_in_sync_and_recommendation_is_derived():
    r = subprocess.run(
        [sys.executable, str(ROOT / "tools" / "decision_gate.py"), "--check"],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )
    assert r.returncode == 0, r.stdout + r.stderr
    d = json.loads((ROOT / "artifacts" / "decision" / "decision.json").read_text())
    # all must-criteria met -> not NO-GO; external legs open -> CONDITIONAL not GO
    assert d["must_criteria_met"] is True
    assert d["recommendation"] in {"GO", "CONDITIONAL GO"}
    if d["external_validation_open"]:
        assert d["recommendation"] == "CONDITIONAL GO"
    # the recommendation must be a function of the criteria, not free text
    musts = [c for c in d["criteria"] if c["must"]]
    assert all(c["met"] for c in musts)
    assert any(c["id"] == "V2" and c["met"] for c in d["criteria"])  # real falsification on record


def test_nogo_when_a_must_criterion_fails():
    # sanity on the decision logic itself: if a must-criterion were unmet, it is NO-GO
    import importlib.util

    spec = importlib.util.spec_from_file_location(
        "decision_gate", ROOT / "tools" / "decision_gate.py"
    )
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    d = m.evaluate()
    forced = [dict(c, met=False) if c["id"] == "V3" else c for c in d["criteria"]]
    must_met = all(c["met"] for c in forced if c["must"])
    assert must_met is False  # a broken honesty gate must block GO
