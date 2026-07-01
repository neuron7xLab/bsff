"""Tests for the bipartite claim<->evidence completeness checker."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from tools.claim_coverage import SCHEMA, evaluate

ROOT = Path(__file__).resolve().parents[1]


def test_real_repo_coverage_is_complete() -> None:
    """The live BSFF registry must form a complete bipartite graph.

    If this ever FAILs it is a real registry defect, not a test bug: the
    assertion message names the offending invariant.
    """
    result = evaluate(ROOT)

    assert result["schema"] == SCHEMA
    assert result["claims"] >= 1
    assert result["bound_artifacts"] >= 1
    assert result["dangling_claim_ids"] == [], "manifest names unknown claim ids"
    assert result["missing_evidence_files"] == [], "asserted claim points at missing file"
    assert result["orphan_claims"] == [], "asserted claim references no evidence"
    assert result["status"] == "PASS"


def _write_root(
    tmp_path: Path,
    claims: dict[str, object],
    artifacts: list[dict[str, object]],
    files: list[str],
) -> Path:
    (tmp_path / "artifacts").mkdir(parents=True, exist_ok=True)
    for rel in files:
        fp = tmp_path / rel
        fp.parent.mkdir(parents=True, exist_ok=True)
        fp.write_text("evidence", encoding="utf-8")
    (tmp_path / "claims.yaml").write_text(
        json.dumps({"schema_version": "test", "claims": claims}), encoding="utf-8"
    )
    (tmp_path / "artifacts" / "MANIFEST.json").write_text(
        json.dumps({"schema_version": "test", "artifacts": artifacts}),
        encoding="utf-8",
    )
    return tmp_path


def test_negative_control_dangling_claim_id(tmp_path: Path) -> None:
    root = _write_root(
        tmp_path,
        claims={
            "BSFF-CLAIM-001": {
                "status": ["internally_verified"],
                "evidence_artifacts": ["evidence/a.json"],
            }
        },
        artifacts=[
            {
                "path": "claims.yaml",
                "claim_ids": ["BSFF-CLAIM-001", "BSFF-CLAIM-999"],
            }
        ],
        files=["evidence/a.json"],
    )

    result = evaluate(root)

    assert result["status"] == "FAIL"
    dangling = [d["claim_id"] for d in result["dangling_claim_ids"]]
    assert "BSFF-CLAIM-999" in dangling
    # the valid id is not reported as dangling
    assert "BSFF-CLAIM-001" not in dangling


def test_negative_control_missing_evidence_file(tmp_path: Path) -> None:
    root = _write_root(
        tmp_path,
        claims={
            "BSFF-CLAIM-001": {
                "status": ["internally_verified"],
                "evidence_artifacts": ["evidence/present.json", "evidence/gone.json"],
            }
        },
        artifacts=[{"path": "claims.yaml", "claim_ids": ["BSFF-CLAIM-001"]}],
        files=["evidence/present.json"],  # gone.json intentionally not created
    )

    result = evaluate(root)

    assert result["status"] == "FAIL"
    missing = [m["path"] for m in result["missing_evidence_files"]]
    assert "evidence/gone.json" in missing
    assert "evidence/present.json" not in missing


def test_unverified_claim_is_exempt_not_orphan(tmp_path: Path) -> None:
    root = _write_root(
        tmp_path,
        claims={
            "BSFF-CLAIM-050": {
                "status": ["unverified"],
                "evidence_artifacts": [],  # no evidence, but scope-only -> exempt
            }
        },
        artifacts=[{"path": "claims.yaml", "claim_ids": ["BSFF-CLAIM-050"]}],
        files=[],
    )

    result = evaluate(root)

    assert result["status"] == "PASS"
    assert result["orphan_claims"] == []
    exempt_ids = [e["claim_id"] for e in result["exempt"]]
    assert "BSFF-CLAIM-050" in exempt_ids


def test_orphan_asserted_claim_fails(tmp_path: Path) -> None:
    root = _write_root(
        tmp_path,
        claims={
            "BSFF-CLAIM-001": {
                "status": ["internally_verified"],
                "evidence_artifacts": [],  # asserted but references nothing
            }
        },
        artifacts=[{"path": "claims.yaml", "claim_ids": ["BSFF-CLAIM-001"]}],
        files=[],
    )

    result = evaluate(root)

    assert result["status"] == "FAIL"
    assert "BSFF-CLAIM-001" in result["orphan_claims"]


@pytest.mark.parametrize("bad_status", [["internally_verified"], ["committed_evidence"]])
def test_asserted_tokens_trigger_evidence_requirement(
    tmp_path: Path, bad_status: list[str]
) -> None:
    root = _write_root(
        tmp_path,
        claims={"BSFF-CLAIM-001": {"status": bad_status, "evidence_artifacts": []}},
        artifacts=[{"path": "claims.yaml", "claim_ids": ["BSFF-CLAIM-001"]}],
        files=[],
    )
    assert evaluate(root)["status"] == "FAIL"
