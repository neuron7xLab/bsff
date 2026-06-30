# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (c) 2026 Yaroslav Vasylenko / neuron7xLab
"""Fail-closed R6/R7 ascension contract gate.

This gate validates the public research-software scaffold without requiring external
services, optional YAML dependencies, or private reviewer context. It is deliberately
strict about rank inflation: the repository may define an R6/R7 path, but it must not
claim R6/R7 completion until external hostile reproduction exists.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from bsff.statistics.contracts import (  # noqa: E402
    assert_valid_claim_registry,
    assert_valid_dataset_registry,
)

REQUIRED_FILES = (
    "docs/R6_R7_ASCENSION_PROTOCOL.md",
    "CLAIMS.md",
    "claims.yaml",
    "DATASET_PROVENANCE.md",
    "data_registry.json",
    "STATISTICAL_CONTRACT.md",
    "src/bsff/statistics/contracts.py",
    "REPRODUCE.md",
    "reproduce.sh",
    "ARTIFACT_EVALUATION.md",
    "artifact_manifest.json",
    "reviewer_quickstart.md",
    "SUPPLY_CHAIN.md",
    "RELEASE_CHECKLIST.md",
)

PUBLIC_BINDING_FILES = (
    "README.md",
    "docs/R6_R7_ASCENSION_PROTOCOL.md",
    "CLAIMS.md",
    "DATASET_PROVENANCE.md",
    "STATISTICAL_CONTRACT.md",
    "ARTIFACT_EVALUATION.md",
    "reviewer_quickstart.md",
)

FORBIDDEN_COMPLETION_PHRASES = (
    "bsff is r6",
    "bsff is r7",
    "r6 complete",
    "r7 complete",
    "field-standard achieved",
    "externally validated",
    "externally replicated",
    "clinical-grade",
    "regulatory-grade",
)

REQUIRED_RANK_BOUNDARY_PHRASES = (
    "not yet r6",
    "not r6 by itself",
    "external reviewer",
    "external hostile reproduction",
)


class GateFailure(RuntimeError):
    """Raised when the R6/R7 ascension contract is violated."""


def _read_text(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def _read_json(path: str) -> dict[str, Any]:
    return json.loads(_read_text(path))


def _check_required_files() -> list[str]:
    return [f"missing required R6/R7 file: {path}" for path in REQUIRED_FILES if not (ROOT / path).is_file()]


def _check_registries() -> list[str]:
    errors: list[str] = []

    try:
        claim_registry = _read_json("claims.yaml")
        assert_valid_claim_registry(claim_registry["claims"])
    except Exception as exc:  # pragma: no cover - message is exercised by CLI path
        errors.append(f"claim registry invalid: {exc}")

    try:
        dataset_registry = _read_json("data_registry.json")
        assert_valid_dataset_registry(dataset_registry["datasets"])
    except Exception as exc:  # pragma: no cover - message is exercised by CLI path
        errors.append(f"dataset registry invalid: {exc}")

    return errors


def _check_claim_dataset_links() -> list[str]:
    claims = _read_json("claims.yaml")["claims"]
    datasets = set(_read_json("data_registry.json")["datasets"])
    errors: list[str] = []

    for claim_id, claim in claims.items():
        for dataset_id in claim.get("required_datasets", []):
            if dataset_id not in datasets:
                errors.append(f"{claim_id}: unknown required dataset {dataset_id!r}")

    return errors


def _check_rank_boundary() -> list[str]:
    text = "\n".join(_read_text(path) for path in PUBLIC_BINDING_FILES if (ROOT / path).is_file())
    lowered = text.lower()
    errors: list[str] = []

    missing = [phrase for phrase in REQUIRED_RANK_BOUNDARY_PHRASES if phrase not in lowered]
    if missing:
        errors.append("rank boundary language missing: " + ", ".join(missing))

    # Allow negative formulations such as "not yet R6/R7" but reject completion language.
    for phrase in FORBIDDEN_COMPLETION_PHRASES:
        if phrase in lowered:
            errors.append(f"forbidden rank or domain overclaim phrase present: {phrase!r}")

    boundary_claim = _read_json("claims.yaml")["claims"].get("BSFF-CLAIM-004", {})
    if boundary_claim.get("status") != ["unverified"]:
        errors.append("BSFF-CLAIM-004 must remain unverified until external reproduction exists")

    return errors


def _check_reproduction_entrypoint() -> list[str]:
    script = _read_text("reproduce.sh") if (ROOT / "reproduce.sh").is_file() else ""
    required_tokens = (
        "test_claim_registry.py",
        "test_dataset_provenance.py",
        "test_statistical_contract.py",
        "bsff evidence verify",
        "REPRODUCTION_REPORT.md",
    )
    return [f"reproduce.sh missing token: {token}" for token in required_tokens if token not in script]


def evaluate() -> list[str]:
    """Return all R6/R7 contract violations."""

    errors: list[str] = []
    errors.extend(_check_required_files())
    errors.extend(_check_registries())
    errors.extend(_check_claim_dataset_links())
    errors.extend(_check_rank_boundary())
    errors.extend(_check_reproduction_entrypoint())
    return errors


def main() -> int:
    errors = evaluate()
    if errors:
        print("R6/R7 CONTRACT: FAIL")
        for error in errors:
            print(f"- {error}")
        return 1

    print("R6/R7 CONTRACT: PASS")
    print("rank_boundary: pre-R6 until external hostile reproduction exists")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
