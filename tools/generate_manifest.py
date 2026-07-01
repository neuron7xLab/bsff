#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (c) 2026 Yaroslav Vasylenko / neuron7xLab
"""Generate or check artifacts/MANIFEST.json."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
from pathlib import Path

try:
    import tomllib
except ModuleNotFoundError:  # pragma: no cover - py3.10 fallback
    import tomli as tomllib  # type: ignore[no-redef]

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "artifacts" / "MANIFEST.json"

RELEASE_GATES = [
    "truth_contract",
    "architecture_contract",
    "status_sync",
    "manifest_sync",
    "ip_provenance",
    "secret_scan",
    "release_check_strict",
    "codeql_high",
]

# Critical artifacts bound by content hash. Each must be a DETERMINISTIC,
# tracked source/evidence file (never nondeterministic run-exhaust). Because
# build_core() embeds each file's live sha256, any content change that is not
# re-manifested makes `generate_manifest.py --check` (the manifest_sync gate)
# fail — this is the fail-closed artifact-integrity binding, not a listing.
CRITICAL_ARTIFACTS = [
    {
        "path": "claims.yaml",
        "producer_command": "hand-authored claim registry (source of truth)",
        "verified_by": ["tools/validate_r6_contracts.py", "tests/test_claim_registry.py"],
        "claim_ids": ["BSFF-CLAIM-001", "BSFF-CLAIM-002", "BSFF-CLAIM-003", "BSFF-CLAIM-004"],
    },
    {
        "path": "contracts/bsff_contract.yaml",
        "producer_command": "hand-authored self-conformance contract (source of truth)",
        "verified_by": ["tools/run_contract_conformance.py", "tools/check_contracts.py"],
        "claim_ids": ["BSFF-CLAIM-001", "BSFF-CLAIM-002", "BSFF-CLAIM-003", "BSFF-CLAIM-004"],
    },
    {
        "path": "reproduce.sh",
        "producer_command": "hand-authored reproduction entrypoint (source of truth)",
        "verified_by": ["tools/validate_r6_contracts.py"],
        "claim_ids": ["BSFF-CLAIM-001", "BSFF-CLAIM-002", "BSFF-CLAIM-003"],
    },
    {
        "path": "artifacts/release/bonn_bright_line/HASHES.sha256",
        "producer_command": "frozen Bonn S2 bright-line evidence hash manifest",
        "verified_by": ["bsff evidence verify"],
        "claim_ids": ["BSFF-CLAIM-001", "BSFF-CLAIM-002"],
    },
    {
        "path": "STATISTICAL_CONTRACT.md",
        "producer_command": "hand-authored statistical contract (source of truth)",
        "verified_by": ["tools/validate_statistical_claims.py"],
        "claim_ids": ["BSFF-CLAIM-001", "BSFF-CLAIM-002"],
    },
    {
        "path": "CLAIMS.md",
        "producer_command": "hand-authored public claim ledger (source of truth)",
        "verified_by": ["tests/test_claim_registry.py"],
        "claim_ids": ["BSFF-CLAIM-001", "BSFF-CLAIM-002", "BSFF-CLAIM-003", "BSFF-CLAIM-004"],
    },
]


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _bound_artifacts() -> list[dict]:
    bound: list[dict] = []
    for entry in CRITICAL_ARTIFACTS:
        path = ROOT / entry["path"]
        if not path.is_file():
            raise SystemExit(f"critical artifact missing, cannot hash-bind: {entry['path']}")
        bound.append(
            {
                "path": entry["path"],
                "sha256": _sha256(path),
                "size_bytes": path.stat().st_size,
                "producer_command": entry["producer_command"],
                "verified_by": entry["verified_by"],
                "claim_ids": entry["claim_ids"],
            }
        )
    return bound


def _version() -> str:
    data = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    return str(data["project"]["version"])


def _test_count() -> int:
    match = re.search(
        r"committed_test_count \| \*\*(\d+)\*\*",
        (ROOT / "STATUS.md").read_text(encoding="utf-8"),
    )
    if not match:
        raise SystemExit("could not read committed_test_count from STATUS.md")
    return int(match.group(1))


def build_core() -> dict:
    return {
        "schema_version": "bsff.manifest/v1",
        "artifact_type": "release_manifest",
        "package": "bsff",
        "generator": "tools/generate_manifest.py",
        "version": _version(),
        "test_count": _test_count(),
        "release_gates": RELEASE_GATES,
        "inputs": ["pyproject.toml", "STATUS.md"],
        "outputs": ["artifacts/MANIFEST.json"],
        "artifacts": _bound_artifacts(),
        "verdict": "GENERATED",
        "source_of_truth": "pyproject.toml + STATUS.md",
    }


def _with_ci(core: dict) -> dict:
    return {
        **core,
        "commit_sha": os.environ.get("GITHUB_SHA", ""),
        "workflow_run_id": os.environ.get("GITHUB_RUN_ID", ""),
        "generated_at_utc": os.environ.get("BSFF_BUILD_UTC", ""),
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true")
    parser.add_argument("--ci", action="store_true", help="augment with commit/run/timestamp env")
    args = parser.parse_args(argv)

    core = build_core()
    if args.check:
        if not OUT.is_file():
            print("artifacts/MANIFEST.json missing")
            return 1
        committed = json.loads(OUT.read_text(encoding="utf-8"))
        committed_core = {k: committed.get(k) for k in core}
        if committed_core != core:
            print("MANIFEST.json is STALE")
            print(f"expected: version={core['version']} test_count={core['test_count']}")
            print(
                f"found: version={committed.get('version')} "
                f"test_count={committed.get('test_count')}"
            )
            return 1
        print(f"MANIFEST.json: in sync (version {core['version']}, {core['test_count']} tests)")
        return 0

    payload = _with_ci(core) if args.ci else core
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    print(f"Wrote {OUT.relative_to(ROOT)} (version {core['version']}, {core['test_count']} tests)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
