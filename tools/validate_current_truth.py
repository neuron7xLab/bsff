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
import hashlib
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


def _head_commit() -> str:
    return subprocess.run(
        ["git", "rev-parse", "HEAD"], capture_output=True, text=True, cwd=ROOT
    ).stdout.strip()


def _verify_hash_manifest(manifest_rel: str) -> list[str]:
    """Return a list of integrity problems for a `sha256sum`-format manifest (empty == clean)."""
    problems: list[str] = []
    manifest = ROOT / manifest_rel
    if not manifest.is_file():
        return [f"evidence hash manifest missing: {manifest_rel}"]
    for line in manifest.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        digest, _, rel = line.partition("  ")
        rel = rel.strip()
        target = ROOT / rel
        if not target.is_file():
            problems.append(f"frozen evidence file missing: {rel}")
            continue
        actual = hashlib.sha256(target.read_bytes()).hexdigest()
        if actual != digest:
            problems.append(
                f"frozen evidence drift: {rel} expected {digest[:12]} got {actual[:12]}"
            )
    return problems


def evaluate_freshness(truth: dict, head: str) -> dict:
    """Fail closed unless CURRENT_TRUTH is bound to HEAD (FRESH) or explicitly frozen with a
    non-empty reason AND a still-verifying evidence hash manifest (FROZEN). A freeze can never
    mask drift: the declared hashes must match on-disk bytes for the freeze to be honoured."""
    main_commit = (truth.get("main_commit") or "").strip()
    freshness = truth.get("freshness") or {}
    frozen_commit = (freshness.get("frozen_evidence_commit") or "").strip()
    reason = (freshness.get("reason") or "").strip()
    manifest_rel = freshness.get("evidence_hash_manifest") or truth.get("hash_manifest_path") or ""

    problems: list[str] = []
    if main_commit and head and main_commit == head:
        mode = "FRESH"
    else:
        mode = "FROZEN"
        if not main_commit:
            problems.append("CURRENT_TRUTH.main_commit is empty")
        if frozen_commit != main_commit:
            problems.append(
                f"stale truth: main_commit {main_commit[:12] or '<empty>'} != HEAD "
                f"{head[:12] or '<none>'} and freshness.frozen_evidence_commit "
                f"{frozen_commit[:12] or '<unset>'} does not anchor it"
            )
        if not reason:
            problems.append("freshness.reason is empty — a freeze must declare why")
    # Whichever mode, a declared manifest must verify so the anchor is evidence-backed.
    if manifest_rel:
        problems.extend(_verify_hash_manifest(manifest_rel))
    elif mode == "FROZEN":
        problems.append("no evidence_hash_manifest declared to back the freeze")

    return {
        "status": "PASS" if not problems else "FAIL",
        "mode": mode,
        "head": head,
        "main_commit": main_commit,
        "frozen_evidence_commit": frozen_commit,
        "evidence_hash_manifest": manifest_rel,
        "problems": problems,
    }


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--output", default=str(OUT))
    a = ap.parse_args(argv)
    truth = json.loads(TRUTH.read_text())
    latest = truth["latest_validation_state"]
    bnci = truth["BNCI_chain_state"]
    freshness = evaluate_freshness(truth, _head_commit())

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

    status = (
        "PASS" if not (contradictions or stale_claims) and freshness["status"] == "PASS" else "FAIL"
    )
    result = {
        "status": status,
        "final_state": latest,
        "BNCI_chain_state": bnci,
        "checked_files": checked,
        "contradictions": contradictions,
        "stale_claims": stale_claims,
        "freshness": freshness,
        "timestamp_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "git_commit": freshness["head"],
    }
    Path(a.output).write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(f"CURRENT_TRUTH consistency: {status} (state={latest})")
    print(
        f"  freshness: {freshness['status']} (mode={freshness['mode']}, "
        f"main_commit={freshness['main_commit'][:12] or '<empty>'}, "
        f"head={freshness['head'][:12] or '<none>'})"
    )
    for x in contradictions + stale_claims + freshness["problems"]:
        print("  -", x)
    return 0 if status == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
