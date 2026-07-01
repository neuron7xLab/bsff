# SPDX-License-Identifier: GPL-3.0-or-later
"""The quality dashboard must aggregate every dimension and fail if any fails."""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TOOLS = ROOT / "tools"


def _load(module: str):
    spec = importlib.util.spec_from_file_location(module, TOOLS / f"{module}.py")
    mod = importlib.util.module_from_spec(spec)
    sys.path.insert(0, str(TOOLS))
    spec.loader.exec_module(mod)
    return mod


def test_dashboard_aggregates_all_dimensions():
    qd = _load("quality_dashboard")
    # Skip mypy here (slow subprocess); the wired dimensions must still aggregate.
    report = qd.evaluate(ROOT, mypy=False)
    assert report["schema"] == "bsff.quality_dashboard/v1"
    # gate_soundness, fail_open, claim_coverage, complexity, determinism.
    assert report["dimensions_total"] >= 5
    for name in ("gate_soundness", "fail_open", "claim_coverage", "complexity", "determinism"):
        assert name in report["dimensions"], name
        assert report["dimensions"][name]["status"] in ("PASS", "FAIL")


def test_dashboard_composite_passes_on_real_repo():
    qd = _load("quality_dashboard")
    report = qd.evaluate(ROOT, mypy=False)
    assert report["composite_status"] == "PASS", report["dimensions"]


def test_dashboard_fails_if_any_dimension_fails(monkeypatch):
    """Composite must be FAIL when even one gate's --check fails — negative control.

    Status is taken from each gate's authoritative --check verdict, so we force
    one gate's --check to report FAIL and assert the composite propagates it.
    """
    qd = _load("quality_dashboard")
    real_check = qd._check_status

    def fake_check(root, tool):
        return "FAIL" if tool == "gate_soundness" else real_check(root, tool)

    monkeypatch.setattr(qd, "_check_status", fake_check)
    monkeypatch.setattr(qd, "_subprocess_gate", lambda root, tool: {"status": "PASS"})
    report = qd.evaluate(ROOT, mypy=False)
    assert report["composite_status"] == "FAIL"
    assert report["dimensions"]["gate_soundness"]["status"] == "FAIL"
