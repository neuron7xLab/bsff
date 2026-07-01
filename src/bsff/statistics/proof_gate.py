# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (c) 2026 Yaroslav Vasylenko / neuron7xLab
"""Artifact-bound statistical proof gate for BSFF claim evidence."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from bsff.statistics.proof_gate_checks import (
    METRIC_KEYS,
    check_metrics,
    check_nulls,
    hashes,
    paths,
    stat_claim,
)

ROOT = Path(__file__).resolve().parents[3]
CLAIMS = "claims.yaml"
CURRENT_TRUTH = "artifacts/release/CURRENT_TRUTH.json"
DEFAULT_REPORT = "artifacts/release/STATISTICAL_PROOF_GATE_REPORT.json"
SCHEMA = "bsff.statistical_proof_gate/v1"


def _read(root: Path, path: str) -> dict[str, Any]:
    data = json.loads((root / path).read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError(f"JSON artifact must be an object: {path}")
    return data


def _load(root: Path, claim_id: str, path: str, errors: list[str]) -> dict[str, Any]:
    try:
        return _read(root, path)
    except Exception as exc:  # noqa: BLE001 - CLI report must expose root cause
        errors.append(f"{claim_id}: cannot read artifact {path}: {exc}")
        return {}


def _proof(root: Path, claim_id: str, claim: dict[str, Any], truth: dict[str, Any]) -> dict[str, Any]:
    errors: list[str] = []
    artifact_paths = paths(truth)
    summary = _load(root, claim_id, artifact_paths.get("s2_summary", ""), errors)
    s3 = _load(root, claim_id, artifact_paths.get("s3_confirmatory", ""), errors)
    multi_null = _load(root, claim_id, artifact_paths.get("multi_null", ""), errors)
    cluster = _load(root, claim_id, artifact_paths.get("cluster_robust_ci", ""), errors)
    check_metrics(
        claim_id,
        truth,
        summary,
        s3,
        cluster,
        root,
        artifact_paths.get("dataset_manifest", ""),
        errors,
    )
    rels = [
        CURRENT_TRUTH,
        *map(str, claim.get("evidence_artifacts", [])),
        *(artifact_paths.get(key, "") for key in METRIC_KEYS),
    ]
    artifact_hashes = hashes(root, claim_id, rels, errors)
    checks = {
        "claim_id_binding": {"claim_id": claim_id, "bound": bool(claim_id)},
        "artifact_hash_binding": {"hashes": artifact_hashes},
        "null_model_outputs": check_nulls(claim_id, claim, multi_null, errors),
    }
    return {
        "claim_id": claim_id,
        "statement": claim.get("statement"),
        "status": "FAIL" if errors else "PASS",
        "evidence_artifacts": sorted({path for path in rels if path}),
        "artifact_hashes": artifact_hashes,
        "checks": checks,
        "violations": errors,
    }


def evaluate(root: Path | str = ROOT) -> dict[str, Any]:
    root = Path(root)
    errors: list[str] = []
    try:
        claims = _read(root, CLAIMS).get("claims", {})
        truth = _read(root, CURRENT_TRUTH)
    except Exception as exc:  # noqa: BLE001 - report must preserve root cause
        claims, truth = {}, {}
        errors.append(str(exc))
    if not isinstance(claims, dict):
        claims = {}
        errors.append("claim registry field 'claims' must be an object")
    proofs, skipped = [], []
    for claim_id, raw_claim in sorted(claims.items()):
        claim = raw_claim if isinstance(raw_claim, dict) else {}
        if stat_claim(claim):
            proofs.append(_proof(root, str(claim_id), claim, truth))
        else:
            skipped.append(
                {
                    "claim_id": str(claim_id),
                    "reason": "not an internally verified statistical measurement claim",
                }
            )
    violations = [*errors, *(v for proof in proofs for v in proof["violations"])]
    if not proofs and not errors:
        violations.append("no internally verified statistical measurement claims found")
    return {
        "schema": SCHEMA,
        "status": "PASS" if not violations else "FAIL",
        "claim_registry": CLAIMS,
        "current_truth": CURRENT_TRUTH,
        "proof_count": len(proofs),
        "skipped_claims": skipped,
        "claim_proofs": proofs,
        "violations": violations,
    }


def write_report(report: dict[str, Any], output: Path) -> None:
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def validate_report_in_sync(expected: dict[str, Any], output: Path) -> list[str]:
    if not output.is_file():
        return [f"statistical proof report missing: {output}"]
    try:
        committed = json.loads(output.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        return [f"statistical proof report is invalid JSON: {exc}"]
    if committed.get("schema") != expected.get("schema"):
        return ["STATISTICAL_PROOF_GATE_REPORT.json has wrong schema"]
    if committed.get("status") != "PASS":
        return ["STATISTICAL_PROOF_GATE_REPORT.json must commit a PASS report snapshot"]
    return []
