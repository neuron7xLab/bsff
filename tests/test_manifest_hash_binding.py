# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (c) 2026 Yaroslav Vasylenko / neuron7xLab
"""MANIFEST.json must hash-bind every critical artifact, not merely list it."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

REQUIRED_FIELDS = {"path", "sha256", "size_bytes", "producer_command", "verified_by", "claim_ids"}


def _manifest() -> dict:
    return json.loads((ROOT / "artifacts" / "MANIFEST.json").read_text(encoding="utf-8"))


def test_manifest_declares_bound_artifacts():
    artifacts = _manifest().get("artifacts")
    assert isinstance(artifacts, list) and artifacts, "MANIFEST.json must bind critical artifacts"


def test_every_bound_artifact_has_full_integrity_fields():
    for entry in _manifest()["artifacts"]:
        missing = REQUIRED_FIELDS - entry.keys()
        assert not missing, f"{entry.get('path')} missing integrity fields: {sorted(missing)}"
        assert entry["verified_by"], f"{entry['path']} must name at least one verifier"
        assert entry["claim_ids"], f"{entry['path']} must bind at least one claim id"


def test_committed_hashes_match_files_on_disk():
    """Recompute sha256/size for each bound artifact; committed must match — fail-closed."""
    mismatches: list[str] = []
    for entry in _manifest()["artifacts"]:
        path = ROOT / entry["path"]
        assert path.is_file(), f"bound artifact absent: {entry['path']}"
        live_sha = hashlib.sha256(path.read_bytes()).hexdigest()
        if live_sha != entry["sha256"]:
            mismatches.append(
                f"{entry['path']}: sha256 committed={entry['sha256'][:12]} live={live_sha[:12]}"
            )
        if path.stat().st_size != entry["size_bytes"]:
            mismatches.append(
                f"{entry['path']}: size committed={entry['size_bytes']} live={path.stat().st_size}"
            )
    assert not mismatches, "hash-binding drift: " + "; ".join(mismatches)


def test_bound_claim_ids_exist_in_registry():
    registry = set(json.loads((ROOT / "claims.yaml").read_text(encoding="utf-8"))["claims"])
    for entry in _manifest()["artifacts"]:
        unknown = set(entry["claim_ids"]) - registry
        assert not unknown, f"{entry['path']} binds unknown claim ids: {sorted(unknown)}"
