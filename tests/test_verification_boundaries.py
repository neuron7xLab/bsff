# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (c) 2026 Yaroslav Vasylenko / neuron7xLab
"""Bind the declared verification boundaries to the implementation.

`docs/VERIFICATION_BOUNDARIES.md` declares where each gate could falsely PASS and
the constant that bounds it. This test makes that declaration non-fiction: the
bounding constants must equal the declared values AND be named in the ledger, so a
gate cannot silently become more permissive than it admits. It also proves the two
mechanisms the integrity fixes depend on: pytest's collection-error exit code and
the offline guard's connectionless (UDP) coverage.
"""

from __future__ import annotations

import importlib.util
import socket
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
LEDGER = (ROOT / "docs" / "VERIFICATION_BOUNDARIES.md").read_text(encoding="utf-8")
sys.path.insert(0, str(ROOT))

from tools import network_guard  # noqa: E402


def _load(tool: str):
    spec = importlib.util.spec_from_file_location(tool, ROOT / "tools" / f"{tool}.py")
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = mod
    spec.loader.exec_module(mod)
    return mod


def test_degradation_bounds_match_ledger():
    cmp = _load("compare_benchmark_baseline")
    assert cmp.TIME_THRESHOLD == 1.0
    assert cmp.TIME_NOISE_FLOOR_S == 5e-4
    assert cmp.MEMORY_THRESHOLD == 0.15
    for name in ("TIME_THRESHOLD", "TIME_NOISE_FLOOR_S", "MEMORY_THRESHOLD"):
        assert name in LEDGER, f"ledger omits the bounding constant {name}"


def test_power_battery_bounds_match_ledger():
    p = _load("statistical_power_profile")
    assert p.N_NULL == 40 and p.N_POSITIVE == 30
    assert p.THRESHOLDS["null_false_positive_rate_max"] == 0.05
    assert p.THRESHOLDS["positive_control_detection_min"] == 0.80
    assert p.THRESHOLDS["surrogate_convergence_min"] == 0.95
    assert "N_null" in LEDGER and "fixed-seed" in LEDGER.lower()


def test_mutation_kill_requires_assertion_exit_code():
    # The gate's rc==1 logic relies on pytest distinguishing an ASSERTION failure
    # (exit 1) from a COLLECTION error (exit 2). Prove that distinction is real.
    failing = ROOT / "tests" / "_tmp_boundary_fail.py"
    broken = ROOT / "tests" / "_tmp_boundary_broken.py"
    failing.write_text("def test_x():\n    assert False\n", encoding="utf-8")
    broken.write_text("def test_x(:\n    pass\n", encoding="utf-8")  # syntax error
    try:
        rc_fail = subprocess.run(
            [sys.executable, "-m", "pytest", str(failing), "-q", "-p", "no:cacheprovider"],
            cwd=ROOT,
            capture_output=True,
            text=True,
        ).returncode
        rc_broken = subprocess.run(
            [sys.executable, "-m", "pytest", str(broken), "-q", "-p", "no:cacheprovider"],
            cwd=ROOT,
            capture_output=True,
            text=True,
        ).returncode
    finally:
        failing.unlink(missing_ok=True)
        broken.unlink(missing_ok=True)
    assert rc_fail == 1, "an assertion failure must be pytest exit 1 (a genuine kill)"
    assert rc_broken == 2, "a collection error must be exit 2 (NOT counted as a kill)"
    # And the gate source enforces exactly this.
    gate = (ROOT / "tools" / "mutation_kill_gate.py").read_text(encoding="utf-8")
    assert "code not in (0, 1)" in gate and "code == 1" in gate


def test_offline_guard_covers_connectionless_egress():
    # Under the active conftest guard, external UDP sendto must fail closed.
    assert socket.socket.sendto is network_guard._guarded_sendto
    udp = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        with pytest.raises(network_guard.NetworkAccessError):
            udp.sendto(b"x", ("8.8.8.8", 53))
    finally:
        udp.close()
    assert "sendto" in LEDGER


def test_every_gate_has_a_declared_boundary():
    for gate in (
        "network_guard",
        "mutation_kill_gate",
        "compare_benchmark_baseline",
        "statistical_power_profile",
        "final_validation_verdict",
        "validate_lockfiles",
        "validate_provenance",
    ):
        assert gate in LEDGER, f"gate {gate} has no declared verification boundary"
