# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (c) 2026 Yaroslav Vasylenko / neuron7xLab
"""BNCI lock audit + method-validity invariants (fail-closed)."""

from __future__ import annotations

import json
from pathlib import Path

import audit_bnci_lock as ala

ROOT = Path(__file__).resolve().parents[2]


def _good_lock() -> dict:
    return json.loads(
        (ROOT / "docs" / "preregistration" / "BNCI2014_001_EXECUTABLE_LOCK.json").read_text()
    )


def test_repaired_lock_is_executable():
    assert ala.audit(_good_lock())["state"] == "BNCI_LOCK_EXECUTABLE"


def test_placeholder_command_blocks():
    lock = _good_lock()
    lock["exact_commands"] = ["python tools/... aggregate"]
    assert ala.audit(lock)["state"] == "BNCI_BLOCKED_LOCK_INCOMPLETE"


def test_csp_command_blocks():
    lock = _good_lock()
    lock["exact_commands"] = ["python run_experiment.py --csp --lda"]
    assert ala.audit(lock)["state"] == "BNCI_BLOCKED_LOCK_INCOMPLETE"


def test_missing_aggregation_blocks():
    lock = _good_lock()
    lock.pop("channel_aggregation", None)
    assert ala.audit(lock)["state"] == "BNCI_BLOCKED_LOCK_INCOMPLETE"


def test_method_validity_is_blocked_method():
    mv = json.loads((ROOT / "artifacts" / "blockers" / "bnci" / "METHOD_VALIDITY.json").read_text())
    assert mv["decision"] == "BNCI_BLOCKED_METHOD"


def test_canonical_bnci_state_blocked_method():
    truth = json.loads((ROOT / "artifacts" / "release" / "CURRENT_TRUTH.json").read_text())
    assert truth["bnci_execution_state"] == "BNCI_BLOCKED_METHOD"
    # Bonn evolved to the robustly-passed state; BNCI remains independently method-blocked.
    assert truth["latest_validation_state"].startswith("BONN_S2_BRIGHT_LINE")
