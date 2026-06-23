#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (c) 2026 Yaroslav Vasylenko / neuron7xLab
"""Minimal Bonn bright-line release-check (Phase 10).

Validates, fail-closed: required files exist, JSON parses, the verdict is an allowed
state, forbidden (clinical/hype) claims are absent from the verdict docs, provenance +
tests are recorded. Exit 0 only if every check passes.
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]

REQUIRED = [
    "artifacts/bonn_bright_line/BRIGHT_LINE_SUMMARY.json",
    "artifacts/bonn_bright_line/DATASET_MANIFEST.json",
    "artifacts/bonn_bright_line/HASHES.sha256",
    "docs/validation/BONN_BRIGHT_LINE_PROTOCOL.md",
    "docs/validation/STATISTIC_REGISTRY.md",
    "docs/validation/BRIGHT_LINE_VERDICT.md",
    "FORMAL_VERDICT.md",
    "REPRODUCE.md",
    "artifacts/release/VERDICT.json",
    "artifacts/release/TESTS.json",
    "artifacts/release/ENVIRONMENT.txt",
]
ALLOWED_STATES = {"BRIGHT_LINE_PASSED", "BRIGHT_LINE_NOT_PASSED", "BLOCKED_DATA",
                  "BLOCKED_RUNTIME", "BLOCKED_API", "BLOCKED_METHOD"}
# Forbidden claims must NOT appear as positive assertions in the verdict docs.
FORBIDDEN = [r"clinical(?:ly)? (?:proven|validated|approved)", r"medical (?:device|use|diagnosis)",
             r"diagnos(?:e|is) (?:patients|seizures)", r"regulatory (?:approval|clearance|validated)",
             r"FDA", r"final proof of brain", r"universal (?:BCI )?benchmark authority", r"cures?\b"]


def main() -> int:
    fails = []
    for rel in REQUIRED:
        if not (ROOT / rel).is_file():
            fails.append(f"missing: {rel}")

    summary_p = ROOT / "artifacts/bonn_bright_line/BRIGHT_LINE_SUMMARY.json"
    verdict = None
    if summary_p.is_file():
        try:
            summary = json.loads(summary_p.read_text())
            verdict = summary.get("verdict")
            if verdict not in ALLOWED_STATES:
                fails.append(f"verdict {verdict!r} not in allowed states")
            if "git_commit" not in summary:
                fails.append("summary missing git_commit provenance")
        except json.JSONDecodeError as e:
            fails.append(f"summary JSON invalid: {e}")

    for rel in ("artifacts/release/VERDICT.json", "artifacts/release/TESTS.json"):
        p = ROOT / rel
        if p.is_file():
            try:
                json.loads(p.read_text())
            except json.JSONDecodeError as e:
                fails.append(f"{rel} JSON invalid: {e}")

    for rel in ("FORMAL_VERDICT.md", "docs/validation/BRIGHT_LINE_VERDICT.md"):
        p = ROOT / rel
        if p.is_file():
            text = p.read_text().lower()
            for pat in FORBIDDEN:
                # allow negated mentions ("not a medical device", "no clinical claim")
                for m in re.finditer(pat, text):
                    ctx = text[max(0, m.start() - 24): m.start()]
                    if not re.search(r"no\b|not\b|never\b|forbidden|excluded|n't", ctx):
                        fails.append(f"forbidden claim {pat!r} asserted in {rel}")
                        break

    if fails:
        print("RELEASE_CHECK: FAIL")
        for f in fails:
            print(f"  - {f}")
        return 1
    print(f"RELEASE_CHECK: PASS (verdict={verdict})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
