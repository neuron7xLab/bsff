#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (c) 2026 Yaroslav Vasylenko / neuron7xLab
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from bsff.cli import validate_kernel  # noqa: E402
from bsff.provenance import build_provenance_manifest  # noqa: E402
from bsff.validation import sha256_file  # noqa: E402

TRACKED = [
    "README.md",
    "VERDICT.md",
    "pyproject.toml",
    "src/bsff/surrogate_engine.py",
    "src/bsff/verdict_engine.py",
    "src/bsff/calibration.py",
    "src/bsff/validation.py",
    ".github/workflows/ci.yml",
    ".github/workflows/security.yml",
    ".github/dependabot.yml",
]


def main() -> int:
    artifact_path = ROOT / "artifacts" / "bsff_phase1_validation.json"
    report = validate_kernel(artifact_path)
    manifest = {
        "document_ref": "OS-BSFF-CORE-2026.1",
        "evidence_status": report["status"],
        "validation_artifact": artifact_path.relative_to(ROOT).as_posix(),
        "validation_artifact_sha256": sha256_file(artifact_path),
        "tracked_files": {rel: sha256_file(ROOT / rel) for rel in TRACKED if (ROOT / rel).exists()},
    }
    provenance = build_provenance_manifest(
        ROOT,
        [
            "README.md",
            "LICENSE",
            "NOTICE",
            "CITATION.cff",
            "AUTHORS.md",
            "pyproject.toml",
            "src/bsff/*.py",
            "tests/*.py",
            "tools/*.py",
            "docs/*.md",
            "paper/*.md",
            "paper/*.bib",
            ".zenodo.json",
            ".github/workflows/*.yml",
        ],
    )
    provenance_out = ROOT / "artifacts" / "provenance_manifest.json"
    provenance_out.write_text(
        json.dumps(provenance, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    manifest["provenance_manifest"] = provenance_out.relative_to(ROOT).as_posix()
    manifest["provenance_manifest_sha256"] = sha256_file(provenance_out)
    out = ROOT / "artifacts" / "evidence_manifest.json"
    out.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(manifest, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
