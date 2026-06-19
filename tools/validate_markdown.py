#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (c) 2026 Yaroslav Vasylenko / neuron7xLab
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REQUIRED_HEADINGS = {
    "README.md": ["## Install", "## One-command local gate", "## Known limits"],
    "SECURITY.md": ["## Supported versions", "## Reporting a vulnerability"],
    "CONTRIBUTING.md": ["## Development loop", "## Pull request contract"],
}


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
    if failures:
        print("Markdown validation failures:")
        for failure in failures:
            print(f"- {failure}")
        return 1
    print("Markdown validation: PASS")
    return 0


if __name__ == "__main__":
    sys.exit(main())
