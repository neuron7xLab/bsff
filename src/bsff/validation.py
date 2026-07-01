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
    data: dict[str, Any] = json.loads(Path(path).read_text(encoding="utf-8"))
    return data


def canonical_artifact_sha256(report: dict[str, Any]) -> str:
    """Recompute the artifact hash over the report with its own hash field removed.

    The generator hashes the report *before* inserting ``artifact_sha256``; this
    reproduces that exact byte sequence so a tampered or non-canonical artifact is
    machine-detectable instead of a decorative trust-me string.
    """
    clone = {k: v for k, v in report.items() if k != "artifact_sha256"}
    serialized = json.dumps(clone, ensure_ascii=False, indent=2)
    return sha256_bytes(serialized.encode("utf-8"))


def validate_phase1_artifact(report: dict[str, Any]) -> list[str]:
    """Return machine-checkable failures for a BSFF validation artifact."""
    failures: list[str] = []
    if report.get("document_ref") != "OS-BSFF-CORE-2026.1":
        failures.append("document_ref mismatch")
    if report.get("pipeline_status") != "EXECUTION_COMPLETE":
        failures.append("pipeline did not complete")
    if report.get("status") != "SURVIVED_PHASE_1_GATES":
        failures.append("phase1 status is not SURVIVED_PHASE_1_GATES")
    if "artifact_sha256" in report:
        expected = canonical_artifact_sha256(report)
        if report["artifact_sha256"] != expected:
            failures.append("artifact_sha256 mismatch (artifact tampered or non-canonical)")
    gates = report.get("gates")
    if not isinstance(gates, dict):
        failures.append("gates must be a dictionary")
        return failures
    missing = REQUIRED_PHASE1_GATES.difference(gates)
    if missing:
        failures.append(f"missing gates: {sorted(missing)}")
    # Fail closed on type-confusion: a non-dict gate value is not structured evidence,
    # so it must FAIL its gate, never bypass it. The old `isinstance(x, dict) and not
    # x.get(...)` short-circuited to False on a bare ``True`` token, letting a forged
    # SURVIVED artifact whose gates are non-dict truthy values pass with zero failures.
    conv = gates.get("miaaft_convergence", {})
    if not isinstance(conv, dict) or not conv.get("converged"):
        failures.append("miaaft convergence gate did not converge")
    leak = gates.get("block_design_leakage", {})
    if not isinstance(leak, dict) or not leak.get("flagged"):
        failures.append("block-design leakage smoke did not flag leakage")
    # A SURVIVED artifact may not ride on a non-converged null: every surrogate
    # gate that carries convergence evidence must report all_converged.
    for gate_name in ("ar1_null_not_rejected", "henon_power_smoke"):
        gate = gates.get(gate_name, {})
        if not isinstance(gate, dict):
            failures.append(f"{gate_name} gate is not a structured evidence object")
            continue
        gate_conv = gate.get("surrogate_convergence")
        if not isinstance(gate_conv, dict):
            failures.append(f"{gate_name} missing surrogate_convergence evidence")
        elif not gate_conv.get("all_converged"):
            failures.append(f"{gate_name} surrogate null did not converge")
    return failures


def assert_phase1_artifact(report: dict[str, Any]) -> None:
    failures = validate_phase1_artifact(report)
    if failures:
        raise AssertionError("; ".join(failures))
