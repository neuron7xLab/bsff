#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (c) 2026 Yaroslav Vasylenko / neuron7xLab

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

REQUIRED_FILES = [
    "LICENSE",
    "LICENSES/GPL-3.0-or-later.txt",
    "LICENSES/CC-BY-4.0.txt",
    "NOTICE",
    "AUTHORS.md",
    "CITATION.cff",
    "docs/IP_PROTECTION_MODEL.md",
    "docs/PROVENANCE_AND_ATTRIBUTION.md",
    "docs/ANTI_PLAGIARISM_PLAYBOOK.md",
    "docs/BRAND_USAGE.md",
    "artifacts/provenance_manifest.json",
]

AUTHOR_MARKER = "Yaroslav Vasylenko / neuron7xLab"
CODE_LICENSE = "GPL-3.0-or-later"
DOCS_LICENSE = "CC-BY-4.0"


def read(rel: str) -> str:
    return (ROOT / rel).read_text(encoding="utf-8")


def main() -> int:
    failures: list[str] = []
    for rel in REQUIRED_FILES:
        if not (ROOT / rel).exists():
            failures.append(f"missing required provenance file: {rel}")

    pyproject = read("pyproject.toml") if (ROOT / "pyproject.toml").exists() else ""
    citation = read("CITATION.cff") if (ROOT / "CITATION.cff").exists() else ""
    notice = read("NOTICE") if (ROOT / "NOTICE").exists() else ""

    if CODE_LICENSE not in pyproject:
        failures.append("pyproject.toml does not declare GPL-3.0-or-later")
    if CODE_LICENSE not in citation:
        failures.append("CITATION.cff does not declare GPL-3.0-or-later")
    if AUTHOR_MARKER not in notice:
        failures.append("NOTICE does not preserve the canonical author marker")
    if DOCS_LICENSE not in notice:
        failures.append("NOTICE does not declare CC-BY-4.0 documentation/spec license")

    for path in sorted((ROOT / "src").rglob("*.py")):
        text = path.read_text(encoding="utf-8")[:300]
        if f"SPDX-License-Identifier: {CODE_LICENSE}" not in text:
            failures.append(f"source file missing SPDX code license: {path.relative_to(ROOT)}")
        if AUTHOR_MARKER not in text:
            failures.append(f"source file missing copyright marker: {path.relative_to(ROOT)}")

    for path in sorted((ROOT / "docs").glob("*.md")):
        text = path.read_text(encoding="utf-8")[:300]
        if f"SPDX-License-Identifier: {DOCS_LICENSE}" not in text:
            failures.append(f"doc file missing CC-BY SPDX marker: {path.relative_to(ROOT)}")

    release_workflow = ROOT / ".github" / "workflows" / "release-artifact.yml"
    if release_workflow.exists():
        text = release_workflow.read_text(encoding="utf-8")
        for needle in [
            "id-token: write",
            "attestations: write",
            # Pin-agnostic: the action is hash-pinned (@<sha> # v2.4.0), so match
            # the prefix instead of a specific tag.
            "actions/attest-build-provenance@",
        ]:
            if needle not in text:
                failures.append(f"release workflow missing provenance control: {needle}")
    else:
        failures.append("missing release-artifact workflow")

    readme = read("README.md") if (ROOT / "README.md").exists() else ""
    readme_lower = readme.lower()
    for needle in ["provenance", "notice", "citation.cff", "gpl-3.0-or-later", "cc-by-4.0"]:
        if needle not in readme_lower:
            failures.append(f"README missing attribution/provenance marker: {needle}")

    if failures:
        print("IP/provenance validation failures:")
        for failure in failures:
            print(f"- {failure}")
        return 1
    print("IP/provenance validation: PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
