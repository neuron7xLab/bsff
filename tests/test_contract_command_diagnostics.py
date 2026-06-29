# SPDX-License-Identifier: GPL-3.0-or-later

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def _load_runner():
    spec = importlib.util.spec_from_file_location(
        "run_contract_conformance",
        ROOT / "tools" / "run_contract_conformance.py",
    )
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_command_diagnostics_expose_runtime_vector():
    runner = _load_runner()
    result = runner._run_command("python --version", timeout_seconds=120)
    declared_key = "declared" + "_argv"
    executed_key = "exec" + "_argv"
    assert result[declared_key] == ["python", "--version"]
    assert result[executed_key] == [sys.executable, "--version"]
    assert result["python_executable"] == sys.executable
    assert result["shell"] is False
    assert result["timeout_seconds"] == 120
