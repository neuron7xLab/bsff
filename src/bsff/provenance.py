# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (c) 2026 Yaroslav Vasylenko / neuron7xLab

from __future__ import annotations

import hashlib
import json
from collections.abc import Iterable, Mapping
from dataclasses import asdict, dataclass
from pathlib import Path

DEFAULT_PROJECT = "BSFF: BCI Signal Falsification Framework"
DEFAULT_AUTHOR = "Yaroslav Vasylenko / neuron7xLab"
DEFAULT_REPOSITORY = "https://github.com/neuron7xLab/bsff"
DEFAULT_CODE_LICENSE = "GPL-3.0-or-later"
DEFAULT_DOCS_LICENSE = "CC-BY-4.0"


@dataclass(frozen=True)
class ProvenanceRecord:
    """Machine-readable origin record for source and release artifacts."""

    project: str
    author: str
    repository: str
    code_license: str
    docs_license: str
    artifact_path: str
    sha256: str
    size_bytes: int

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def canonical_json_sha256(payload: Mapping[str, object]) -> str:
    encoded = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode(
        "utf-8"
    )
    return hashlib.sha256(encoded).hexdigest()


def claim_fingerprint(payload: Mapping[str, object], namespace: str = "bsff-claim") -> str:
    """Stable fingerprint for a claim/verdict/provenance JSON object."""

    return canonical_json_sha256({"namespace": namespace, "payload": dict(payload)})


def iter_tracked_files(root: Path, patterns: Iterable[str]) -> list[Path]:
    files: list[Path] = []
    for pattern in patterns:
        files.extend(p for p in root.glob(pattern) if p.is_file())
    return sorted(set(files), key=lambda p: p.as_posix())


def build_provenance_manifest(
    root: Path,
    patterns: Iterable[str],
    *,
    project: str = DEFAULT_PROJECT,
    author: str = DEFAULT_AUTHOR,
    repository: str = DEFAULT_REPOSITORY,
    code_license: str = DEFAULT_CODE_LICENSE,
    docs_license: str = DEFAULT_DOCS_LICENSE,
) -> dict[str, object]:
    """Build a deterministic manifest tying release files to origin metadata."""

    records: list[ProvenanceRecord] = []
    for path in iter_tracked_files(root, patterns):
        rel = path.relative_to(root).as_posix()
        records.append(
            ProvenanceRecord(
                project=project,
                author=author,
                repository=repository,
                code_license=code_license,
                docs_license=docs_license,
                artifact_path=rel,
                sha256=sha256_file(path),
                size_bytes=path.stat().st_size,
            )
        )
    manifest: dict[str, object] = {
        "schema": "bsff.provenance.v1",
        "project": project,
        "author": author,
        "repository": repository,
        "code_license": code_license,
        "docs_license": docs_license,
        "records": [record.to_dict() for record in records],
    }
    manifest["manifest_sha256"] = claim_fingerprint(manifest, namespace="bsff-provenance")
    return manifest


def verify_attribution_manifest(
    manifest: Mapping[str, object],
    *,
    expected_author: str = DEFAULT_AUTHOR,
    expected_code_license: str = DEFAULT_CODE_LICENSE,
    expected_docs_license: str = DEFAULT_DOCS_LICENSE,
) -> dict[str, object]:
    """Validate the author/license fields that downstream forks tend to quietly erase."""

    failures: list[str] = []
    if manifest.get("author") != expected_author:
        failures.append("author_mismatch")
    if manifest.get("code_license") != expected_code_license:
        failures.append("code_license_mismatch")
    if manifest.get("docs_license") != expected_docs_license:
        failures.append("docs_license_mismatch")
    if not manifest.get("records"):
        failures.append("empty_records")
    return {"ok": not failures, "failures": failures}
