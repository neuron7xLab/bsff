# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (c) 2026 Yaroslav Vasylenko / neuron7xLab
"""Contract entrypoints must be real gates, never PASS-printing stubs."""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TOOLS = ROOT / "tools"


def _load(name: str):
    sys.path.insert(0, str(TOOLS))
    spec = importlib.util.spec_from_file_location(name, TOOLS / f"{name}.py")
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_check_contracts_delegates_to_conformance_runner(monkeypatch):
    """It must invoke the real runner and propagate its exit code — not fabricate 0.

    A stub that unconditionally returned 0 (the prior behaviour) fails this test:
    a NONCONFORMANT contract has to be able to surface as a non-zero exit.
    """
    check_contracts = _load("check_contracts")
    calls: dict[str, object] = {}

    def fake_runner(argv=None):
        calls["argv"] = argv
        return 7  # simulate NONCONFORMANT

    monkeypatch.setattr(check_contracts, "_conformance_main", fake_runner)
    rc = check_contracts.main(["--contract", "x"])

    assert "argv" in calls, "check_contracts must call the conformance runner"
    assert calls["argv"] == ["--contract", "x"], "arguments must pass through unchanged"
    assert rc == 7, "check_contracts must propagate the runner's exit code, never a hardcoded 0"
