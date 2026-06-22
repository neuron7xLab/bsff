#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (c) 2026 Yaroslav Vasylenko / neuron7xLab
from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REQUIRED_HEADINGS = {
    "README.md": ["## Install", "## One-command local gate", "## Known limits"],
    "SECURITY.md": ["## Supported versions", "## Reporting a vulnerability"],
    "CONTRIBUTING.md": ["## Development loop", "## Pull request contract"],
}

# --- No hardcoded live-test-count literal in prose --------------------------
#
# The live test count has exactly one source: the generated `STATUS.md`
# (`tools/update_status.py`, enforced by `--check`). A count typed into any
# other document is decoration that drifts — the repo already enforces this for
# the README badge (`tools/verify_grounding.py`) and for governed JSON artifacts
# (`tools/validate_artifact_schema.py`); this closes the remaining gap, prose.
#
# Forbidden adjacencies (case-insensitive), e.g. `310 passed`, `80/80 passed`,
# `389 tests collected`, `expect 310 passed`, `passes 310`. Single-digit
# per-file counts (`6 tests pass`) are not the live-suite count and are allowed.
COUNT_LITERAL_PATTERNS = (
    re.compile(r"\bexpect\s+\d+\s+passed\b", re.IGNORECASE),
    re.compile(r"\b\d{2,}\s+tests?\s+(?:passed|collected)\b", re.IGNORECASE),
    re.compile(r"\b\d{2,}\s+passed\b", re.IGNORECASE),
    re.compile(r"\bpasses\s+\*{0,2}\d{2,}", re.IGNORECASE),
)
# The generated single source legitimately holds the live count.
COUNT_LITERAL_EXEMPT_FILES = {"STATUS.md"}
# An auditable per-line escape hatch for docs that must quote the forbidden
# pattern to define/illustrate it (e.g. the schema doc's example of the defect).
COUNT_LITERAL_OK_MARKER = "count-literal-ok"
SKIP_DIRS = {".git", ".venv", "node_modules", "__pycache__", "dist", "build"}


def iter_markdown(root: Path) -> list[Path]:
    return sorted(
        p
        for p in root.rglob("*.md")
        if not any(part in SKIP_DIRS for part in p.relative_to(root).parts)
    )


def find_count_literals(root: Path = ROOT) -> list[str]:
    failures: list[str] = []
    for path in iter_markdown(root):
        rel = path.relative_to(root).as_posix()
        if rel in COUNT_LITERAL_EXEMPT_FILES:
            continue
        for lineno, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
            if COUNT_LITERAL_OK_MARKER in line:
                continue
            for pat in COUNT_LITERAL_PATTERNS:
                match = pat.search(line)
                if match:
                    failures.append(
                        f"{rel}:{lineno}: hardcoded test-count literal "
                        f"({match.group(0)!r}) — cite STATUS.md, do not embed a count"
                    )
                    break
    return failures


def main() -> int:
    failures: list[str] = []
    for rel, headings in REQUIRED_HEADINGS.items():
        path = ROOT / rel
        if not path.exists():
            failures.append(f"missing {rel}")
            continue
        text = path.read_text(encoding="utf-8")
        for heading in headings:
            if heading not in text:
                failures.append(f"{rel}: missing heading {heading}")
    failures.extend(find_count_literals())
    if failures:
        print("Markdown validation failures:")
        for failure in failures:
            print(f"- {failure}")
        return 1
    print("Markdown validation: PASS")
    return 0


if __name__ == "__main__":
    sys.exit(main())
