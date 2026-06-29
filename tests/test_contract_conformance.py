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
        [
            sys.executable,
            str(ROOT / "tools" / "run_contract_conformance.py"),
            "--output",
            str(out),
        ],
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


def test_command_items_record_argv_duration_and_bounded_output():
    import importlib.util

    spec = importlib.util.spec_from_file_location(
        "run_contract_conformance",
        ROOT / "tools" / "run_contract_conformance.py",
    )
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    result = mod._check_item(
        {"id": "cmd", "kind": "command", "run": "python -c 'print(42)'"}
    )
    assert result["status"] == "CONFORMANT"
    assert result["argv"] == ["python", "-c", "print(42)"]
    assert isinstance(result["duration_ms"], int)
    assert result["stdout_tail"].strip() == "42"


def test_command_items_do_not_use_shell_redirection(tmp_path):
    import importlib.util

    spec = importlib.util.spec_from_file_location(
        "run_contract_conformance",
        ROOT / "tools" / "run_contract_conformance.py",
    )
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    target = tmp_path / "must_not_exist.txt"
    result = mod._check_item(
        {"id": "cmd", "kind": "command", "run": f"echo ok > {target}"}
    )
    assert result["status"] == "CONFORMANT"
    assert not target.exists()
    assert ">" in result["argv"]
