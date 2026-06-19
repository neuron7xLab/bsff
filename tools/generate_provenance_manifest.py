#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (c) 2026 Yaroslav Vasylenko / neuron7xLab

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from bsff.provenance import build_provenance_manifest  # noqa: E402

TRACKED_PATTERNS = [
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
    ".github/workflows/*.yml",
    ".github/*.md",
    ".github/ISSUE_TEMPLATE/*.yml",
]


def main() -> int:
    manifest = build_provenance_manifest(ROOT, TRACKED_PATTERNS)
    out = ROOT / "artifacts" / "provenance_manifest.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(manifest, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
