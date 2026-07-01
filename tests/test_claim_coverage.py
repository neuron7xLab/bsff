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


def test_unbacked_asserted_claim_fails(tmp_path: Path) -> None:
    """An asserted claim whose evidence exists but which no MANIFEST artifact
    binds (claim_ids) is an unbacked hole in the bipartite graph -> FAIL."""
    root = _write_root(
        tmp_path,
        claims={
            "BSFF-CLAIM-001": {
                "status": ["internally_verified"],
                "evidence_artifacts": ["evidence/a.json"],
            }
        },
        artifacts=[{"path": "claims.yaml", "claim_ids": []}],
        files=["evidence/a.json"],
    )
    result = evaluate(root)
    assert result["status"] == "FAIL"
    assert "BSFF-CLAIM-001" in result["unbacked_claims"]


# --- Hole 1: fail-closed asserted-predicate -----------------------------
@pytest.mark.parametrize(
    "status",
    [
        ["verified"],  # not in the old substring vocabulary -> used to slip to exempt
        ["survived"],
        ["internally-verified"],  # hyphen variant of the old token
        ["typo_status_xyz"],  # unknown/mistyped -> must fail closed to asserted
        ["unverified", "verified"],  # mixed: one non-exempt token -> asserted
    ],
)
def test_negative_control_nonexempt_status_is_asserted(tmp_path: Path, status: list[str]) -> None:
    """A status not drawn entirely from the closed EXEMPT vocabulary must be
    treated as ASSERTED: with no evidence it is an orphan -> FAIL, never
    silently exempt."""
    root = _write_root(
        tmp_path,
        claims={"BSFF-CLAIM-001": {"status": status, "evidence_artifacts": []}},
        artifacts=[{"path": "claims.yaml", "claim_ids": ["BSFF-CLAIM-001"]}],
        files=[],
    )

    result = evaluate(root)

    assert result["status"] == "FAIL"
    assert "BSFF-CLAIM-001" in result["orphan_claims"]
    exempt_ids = [e["claim_id"] for e in result["exempt"]]
    assert "BSFF-CLAIM-001" not in exempt_ids


# --- Hole 2: evidence must be a non-empty regular file -------------------
def test_negative_control_empty_evidence_file_fails(tmp_path: Path) -> None:
    """A 0-byte evidence file does not satisfy the completeness requirement."""
    root = _write_root(
        tmp_path,
        claims={
            "BSFF-CLAIM-001": {
                "status": ["internally_verified"],
                "evidence_artifacts": ["evidence/empty.json"],
            }
        },
        artifacts=[{"path": "claims.yaml", "claim_ids": ["BSFF-CLAIM-001"]}],
        files=[],  # create the evidence file empty, below
    )
    empty = root / "evidence" / "empty.json"
    empty.parent.mkdir(parents=True, exist_ok=True)
    empty.write_bytes(b"")  # 0 bytes

    result = evaluate(root)

    assert result["status"] == "FAIL"
    missing = [m["path"] for m in result["missing_evidence_files"]]
    assert "evidence/empty.json" in missing


def test_negative_control_directory_evidence_fails(tmp_path: Path) -> None:
    """A directory at the evidence path is not a valid artifact."""
    root = _write_root(
        tmp_path,
        claims={
            "BSFF-CLAIM-001": {
                "status": ["internally_verified"],
                "evidence_artifacts": ["evidence/as_dir"],
            }
        },
        artifacts=[{"path": "claims.yaml", "claim_ids": ["BSFF-CLAIM-001"]}],
        files=[],
    )
    (root / "evidence" / "as_dir").mkdir(parents=True, exist_ok=True)

    result = evaluate(root)

    assert result["status"] == "FAIL"
    missing = [m["path"] for m in result["missing_evidence_files"]]
    assert "evidence/as_dir" in missing


# --- Hole 3: phantom manifest path cannot back a claim ------------------
def test_negative_control_phantom_manifest_path_unbacks_claim(
    tmp_path: Path,
) -> None:
    """A claim 'backed' only by a manifest artifact whose path does not exist
    (or is empty) is unbacked -> FAIL. Real evidence still exists on disk, so
    the failure is specifically the unbacked hole."""
    root = _write_root(
        tmp_path,
        claims={
            "BSFF-CLAIM-001": {
                "status": ["internally_verified"],
                "evidence_artifacts": ["evidence/a.json"],
            }
        },
        artifacts=[
            {"path": "does/not/exist.json", "claim_ids": ["BSFF-CLAIM-001"]},
        ],
        files=["evidence/a.json"],
    )

    result = evaluate(root)

    assert result["status"] == "FAIL"
    assert result["missing_evidence_files"] == []
    assert "BSFF-CLAIM-001" in result["unbacked_claims"]
    # the phantom path contributes nothing to the coverage matrix
    assert result["coverage_matrix"]["BSFF-CLAIM-001"] == []


def test_negative_control_empty_manifest_path_unbacks_claim(tmp_path: Path) -> None:
    """A manifest artifact whose path exists but is a 0-byte file also fails to
    back the claim."""
    root = _write_root(
        tmp_path,
        claims={
            "BSFF-CLAIM-001": {
                "status": ["internally_verified"],
                "evidence_artifacts": ["evidence/a.json"],
            }
        },
        artifacts=[{"path": "empty_backer.json", "claim_ids": ["BSFF-CLAIM-001"]}],
        files=["evidence/a.json"],
    )
    (root / "empty_backer.json").write_bytes(b"")  # 0 bytes -> not a real backer

    result = evaluate(root)

    assert result["status"] == "FAIL"
    assert "BSFF-CLAIM-001" in result["unbacked_claims"]
