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
