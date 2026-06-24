#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (c) 2026 Yaroslav Vasylenko / neuron7xLab
"""Fail CI if any public document contradicts artifacts/release/CURRENT_TRUTH.json.

Scans for STALE current-state claims (e.g. a present-tense "NOT_PASSED" or "BNCI blocked")
while allowing the SAME phrases when explicitly marked historical (S1 / was / previously /
superseded). Also requires the canonical state token to appear in the headline surfaces.
Writes artifacts/release/TRUTH_CONSISTENCY_CHECK.json.
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TRUTH = ROOT / "artifacts" / "release" / "CURRENT_TRUTH.json"
OUT = ROOT / "artifacts" / "release" / "TRUTH_CONSISTENCY_CHECK.json"

# Public surfaces that must agree with CURRENT_TRUTH.
SURFACES = [
    "FORMAL_VERDICT.md",
    "STATUS.md",
    "REPRODUCE.md",
    "README.md",
    "docs/validation/S2_VERDICT.md",
    "docs/validation/CLAIM_AUDIT.md",
    "docs/validation/BONN_STATUS.md",
    "docs/reviewer_packet/REVIEWER_PACKET.md",
]
# Surfaces that must contain the canonical latest-state token in headline position.
MUST_AFFIRM = ["FORMAL_VERDICT.md", "STATUS.md", "artifacts/release/CURRENT_TRUTH.json"]

# A line marked historical may legitimately quote a stale phrase.
HISTORICAL = re.compile(
    r"\bS1\b|historical|was\b|previously|superseded|earlier|preserved|"
    r"not[- ]passed.*0\.065|S1 .*NOT_PASSED",
    re.IGNORECASE,
)
# Stale CURRENT-state claims (forbidden unless the line is historical).
STALE = [
    (
        r"current\s+(final\s+)?state[^.]*BRIGHT_LINE_NOT_PASSED",
        "present-tense NOT_PASSED as current state",
    ),
    (
        r"BNCI[^.\n]*chain[^.\n]*BLOCKED",
        "BNCI chain claimed BLOCKED (now UNLOCKED_FOR_PREREGISTRATION_ONLY)",
    ),
    (r"no real published dataset is shipped", "unqualified 'no real published dataset'"),
    (r"\bsynthetic[- ]only\b", "unqualified 'synthetic-only'"),
]


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--output", default=str(OUT))
    a = ap.parse_args(argv)
    truth = json.loads(TRUTH.read_text())
    latest = truth["latest_validation_state"]
    bnci = truth["BNCI_chain_state"]

    contradictions, stale_claims, checked = [], [], []
    for rel in SURFACES:
        p = ROOT / rel
        if not p.is_file():
            continue
        checked.append(rel)
        for i, line in enumerate(p.read_text(encoding="utf-8").splitlines(), 1):
            if HISTORICAL.search(line):
                continue
            for pat, why in STALE:
                if re.search(pat, line, re.IGNORECASE):
                    stale_claims.append(f"{rel}:{i}: {why} :: {line.strip()[:80]}")

    for rel in MUST_AFFIRM:
        p = ROOT / rel
        if p.is_file() and latest not in p.read_text(encoding="utf-8"):
            contradictions.append(f"{rel}: missing canonical state token {latest!r}")

    # BNCI must not be claimed validated anywhere.
    for rel in SURFACES:
        p = ROOT / rel
        if p.is_file() and re.search(r"BNCI[^.\n]*validated", p.read_text(), re.IGNORECASE):
            if not re.search(
                r"not\s+BNCI[- ]validated|no BNCI claim|preregistration",
                p.read_text(),
                re.IGNORECASE,
            ):
                contradictions.append(f"{rel}: appears to claim BNCI validated (it is {bnci})")

    status = "PASS" if not (contradictions or stale_claims) else "FAIL"
    result = {
        "status": status,
        "final_state": latest,
        "BNCI_chain_state": bnci,
        "checked_files": checked,
        "contradictions": contradictions,
        "stale_claims": stale_claims,
        "timestamp_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "git_commit": subprocess.run(
            ["git", "rev-parse", "HEAD"], capture_output=True, text=True, cwd=ROOT
        ).stdout.strip(),
    }
    Path(a.output).write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(f"CURRENT_TRUTH consistency: {status} (state={latest})")
    for x in contradictions + stale_claims:
        print("  -", x)
    return 0 if status == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
