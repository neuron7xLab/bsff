# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (c) 2026 Yaroslav Vasylenko / neuron7xLab
from bsff.cli import validate_kernel
from bsff.validation import assert_phase1_artifact, validate_phase1_artifact


def test_phase1_artifact_contract(tmp_path):
    report = validate_kernel(tmp_path / "phase1.json")
    assert_phase1_artifact(report)
    assert validate_phase1_artifact(report) == []


def test_phase1_artifact_contract_rejects_failed_status():
    failures = validate_phase1_artifact({"status": "FAILED", "gates": {}})
    assert failures


def test_phase1_rejects_nondict_gate_tokens(tmp_path):
    # Regression (type-confusion fail-open): the gate checks were
    # `isinstance(x, dict) and not x.get(...)`, which short-circuits to False on a bare
    # `True`. A forged SURVIVED artifact whose gates are non-dict truthy tokens (negative
    # evidence erased) then passed with zero failures. Non-dict gates must fail closed.
    report = validate_kernel(tmp_path / "phase1.json")
    assert validate_phase1_artifact(report) == []
    forged = dict(report)
    forged["gates"] = dict.fromkeys(report["gates"], True)  # every gate -> bare True
    failures = validate_phase1_artifact(forged)
    assert failures, "a forged SURVIVED artifact with non-dict gate tokens must be rejected"
