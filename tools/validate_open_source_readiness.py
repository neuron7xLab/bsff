#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (c) 2026 Yaroslav Vasylenko / neuron7xLab
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REQUIRED_FILES = [
    "LICENSE",
    "README.md",
    "SECURITY.md",
    "CONTRIBUTING.md",
    "CODE_OF_CONDUCT.md",
    "SUPPORT.md",
    "CITATION.cff",
    ".editorconfig",
    ".gitignore",
    ".gitattributes",
    ".github/CODEOWNERS",
    ".github/dependabot.yml",
    ".github/PULL_REQUEST_TEMPLATE.md",
    ".github/ISSUE_TEMPLATE/bug_report.yml",
    ".github/ISSUE_TEMPLATE/falsification_claim.yml",
    ".github/workflows/ci.yml",
    ".github/workflows/security.yml",
    ".github/workflows/scorecard.yml",
    "docs/GITHUB_PUBLICATION_RUNBOOK.md",
    "docs/REPRODUCIBILITY.md",
    "docs/FALSIFICATION_PROTOCOL.md",
    "docs/SECURITY_MODEL.md",
    "NOTICE",
    "AUTHORS.md",
    "LICENSES/GPL-3.0-or-later.txt",
    "LICENSES/CC-BY-4.0.txt",
    "docs/IP_PROTECTION_MODEL.md",
    "docs/PROVENANCE_AND_ATTRIBUTION.md",
    "docs/ANTI_PLAGIARISM_PLAYBOOK.md",
    "docs/BRAND_USAGE.md",
    "tools/validate_ip_provenance.py",
    "tools/generate_provenance_manifest.py",
]

TRUTH_MARKERS = [
    "does **not** prove BCI claims",
    "not externally validated against TISEAN",
    "not regulatory validation",
]


def main() -> int:
    failures: list[str] = []
    for rel in REQUIRED_FILES:
        if not (ROOT / rel).exists():
            failures.append(f"missing required file: {rel}")
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    for marker in TRUTH_MARKERS:
        if marker not in readme:
            failures.append(f"README missing truth marker: {marker}")
    if failures:
        print("Open-source readiness failures:")
        for failure in failures:
            print(f"- {failure}")
        return 1
    print("Open-source readiness: PASS")
    return 0


if __name__ == "__main__":
    sys.exit(main())
