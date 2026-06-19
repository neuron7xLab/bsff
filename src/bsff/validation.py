# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (c) 2026 Yaroslav Vasylenko / neuron7xLab
from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

REQUIRED_PHASE1_GATES = {
    "miaaft_convergence",
    "ar1_null_not_rejected",
    "henon_power_smoke",
    "block_design_leakage",
    "verdict_json",
}


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_file(path: str | Path) -> str:
    return sha256_bytes(Path(path).read_bytes())


def load_json(path: str | Path) -> dict[str, Any]:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def validate_phase1_artifact(report: dict[str, Any]) -> list[str]:
    """Return machine-checkable failures for a BSFF validation artifact."""
    failures: list[str] = []
    if report.get("document_ref") != "OS-BSFF-CORE-2026.1":
        failures.append("document_ref mismatch")
    if report.get("pipeline_status") != "EXECUTION_COMPLETE":
        failures.append("pipeline did not complete")
    if report.get("status") != "SURVIVED_PHASE_1_GATES":
        failures.append("phase1 status is not SURVIVED_PHASE_1_GATES")
    gates = report.get("gates")
    if not isinstance(gates, dict):
        failures.append("gates must be a dictionary")
        return failures
    missing = REQUIRED_PHASE1_GATES.difference(gates)
    if missing:
        failures.append(f"missing gates: {sorted(missing)}")
    conv = gates.get("miaaft_convergence", {})
    if isinstance(conv, dict) and not conv.get("converged"):
        failures.append("miaaft convergence gate did not converge")
    leak = gates.get("block_design_leakage", {})
    if isinstance(leak, dict) and not leak.get("flagged"):
        failures.append("block-design leakage smoke did not flag leakage")
    return failures


def assert_phase1_artifact(report: dict[str, Any]) -> None:
    failures = validate_phase1_artifact(report)
    if failures:
        raise AssertionError("; ".join(failures))
