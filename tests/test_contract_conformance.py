# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (c) 2026 Yaroslav Vasylenko / neuron7xLab
"""The system verifies itself against its declared contract (self-conformance)."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

pytest.importorskip("yaml")

pytestmark = pytest.mark.slow

ROOT = Path(__file__).resolve().parents[1]


def test_conformance_runs_and_has_no_nonconformant_feasible_item(tmp_path):
    out = tmp_path / "conf"
    r = subprocess.run(
        [sys.executable, str(ROOT / "tools" / "run_contract_conformance.py"), "--output", str(out)],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )
    # exit 0 == no feasible item is NONCONFORMANT (PARTIAL from blocked items is OK)
    assert r.returncode == 0, r.stdout + r.stderr

    verdict = json.loads((out / "CONFORMANCE_VERDICT.json").read_text())
    assert verdict["overall"] in {"CONFORMANT", "PARTIAL"}
    assert verdict["nonconformant"] == 0
    # the feasible items must actually be present and checked
    assert verdict["conformant"] >= 10
    # blocked items must be honestly UNVERIFIABLE, never silently passed
    blocked = [i for i in verdict["items"] if i["kind"] == "blocked"]
    assert blocked and all(i["status"] == "UNVERIFIABLE" for i in blocked)
