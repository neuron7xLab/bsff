#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (c) 2026 Yaroslav Vasylenko / neuron7xLab
"""Scan changelog / release notes for the same forbidden claims as the contract."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

from validate_truth_contract import find_forbidden_claims  # noqa: E402

NOTE_FILES = ("CHANGELOG.md", "RELEASE_NOTES.md", "RELEASE_VERDICT.md")


def main(argv: list[str] | None = None) -> int:
    scanned = []
    failures = []
    for name in NOTE_FILES:
        p = ROOT / name
        if not p.is_file():
            continue
        scanned.append(name)
        for claim in find_forbidden_claims(p.read_text(encoding="utf-8")):
            failures.append(f"{name}: forbidden claim '{claim}'")
    print(f"release notes scanned: {scanned or 'none present'}")
    if failures:
        for f in failures:
            print(f"  FAIL: {f}")
        return 1
    print("release notes: no forbidden claim.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
