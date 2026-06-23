#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (c) 2026 Yaroslav Vasylenko / neuron7xLab
"""Bonn bright-line release-check (Phase 11), fail-closed.

Validates: required files exist, JSON parses, final_state is allowed, G1/G2 values
present, bright-line logic correct, hash file exists, tests recorded, forbidden claims
absent (or explicitly negated), raw dataset not git-tracked, docs carry the final state,
release bundle exists. Exit 0 only if every check passes.
"""
from __future__ import annotations

import argparse
import json
import re
import subprocess
import time
from pathlib import Path

ALLOWED_STATES = {"BRIGHT_LINE_PASSED", "BRIGHT_LINE_NOT_PASSED", "BLOCKED_DATA",
                  "BLOCKED_RUNTIME", "BLOCKED_API", "BLOCKED_METHOD"}
FORBIDDEN = [r"clinical(?:ly)? (?:proven|validated|approved)", r"medical (?:device|use|diagnosis)",
             r"diagnos(?:e|is) (?:patients|seizures)", r"regulatory (?:approval|clearance|validated)",
             r"\bFDA\b", r"final proof of brain", r"universal (?:BCI )?benchmark authority", r"\bcures?\b"]
REQUIRED = [
    "artifacts/bonn_bright_line/BRIGHT_LINE_SUMMARY.json",
    "artifacts/bonn_bright_line/bonn_CONFIRMATORY_VERDICT.json",
    "artifacts/bonn_bright_line/DATASET_MANIFEST.json",
    "artifacts/controls/ar_negative_CONFIRMATORY_A.json",
    "artifacts/controls/ar_negative_CONFIRMATORY_B.json",
    "artifacts/release/bonn_bright_line/HASHES.sha256",
    "artifacts/release/bonn_bright_line/VERDICT.json",
    "artifacts/release/bonn_bright_line/TESTS.json",
    "artifacts/release/bonn_bright_line/ENVIRONMENT.txt",
    "docs/validation/BONN_BRIGHT_LINE_PROTOCOL.md",
    "docs/validation/STATISTIC_REGISTRY.md",
    "docs/validation/CLAIM_AUDIT.md",
    "docs/validation/DATASET_PROVENANCE_AUDIT.md",
    "docs/validation/NEXT_METHOD_CONTRACT_S2.md",
    "docs/validation/BRIGHT_LINE_VERDICT.md",
    "docs/reviewer_packet/REVIEWER_PACKET.md",
    "FORMAL_VERDICT.md",
    "REPRODUCE.md",
]


def _neg_ok(line: str) -> bool:
    return bool(re.search(r"\bno\b|\bnot\b|\bnever\b|forbidden|excluded|out of scope|n't", line))


def main(argv=None) -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--root", default=str(Path(__file__).resolve().parents[2]))
    p.add_argument("--output", default=None)
    a = p.parse_args(argv)
    root = Path(a.root).resolve()
    checks, failures, warnings = [], [], []

    def check(name, ok, detail=""):
        checks.append({"name": name, "ok": bool(ok), "detail": detail})
        if not ok:
            failures.append(f"{name}: {detail}")

    for rel in REQUIRED:
        check(f"exists:{rel}", (root / rel).is_file())

    summary = None
    sp = root / "artifacts/bonn_bright_line/BRIGHT_LINE_SUMMARY.json"
    if sp.is_file():
        try:
            summary = json.loads(sp.read_text())
        except json.JSONDecodeError as e:
            check("summary_json_parses", False, str(e))
    final_state = (summary or {}).get("final_state") or (summary or {}).get("verdict")
    check("final_state_allowed", final_state in ALLOWED_STATES, str(final_state))
    if summary:
        check("git_commit_present", bool(summary.get("git_commit")))
        check("G1_values_present", all(k in summary.get("G1", {}) for k in
              ("E_survived_fraction", "A_not_survived_fraction", "B_not_survived_fraction")))
        check("G2_values_present", all(k in summary.get("G2", {}) for k in ("FPR_A", "FPR_B", "combined_FPR")))
        bl = bool(summary.get("BRIGHT_LINE_PASSED"))
        check("bright_line_logic", bl == (bool(summary.get("G1_PASS")) and bool(summary.get("G2_PASS"))))

    tp = root / "artifacts/release/bonn_bright_line/TESTS.json"
    if tp.is_file():
        t = json.loads(tp.read_text())
        check("tests_recorded", t.get("passed", 0) > 0 and t.get("failed", 1) == 0,
              f"passed={t.get('passed')} failed={t.get('failed')}")

    # raw data not tracked
    tracked = subprocess.run(["git", "ls-files"], capture_output=True, text=True, cwd=root).stdout
    raw = [ln for ln in tracked.splitlines() if "bonn_data/" in ln or ln.endswith((".edf",))
           or re.search(r"bonn_data/.*\.(txt|zip)$", ln)]
    check("raw_data_not_tracked", not raw, f"{len(raw)} raw files tracked")

    # forbidden claims absent (or negated) in verdict docs
    for rel in ("FORMAL_VERDICT.md", "docs/validation/BRIGHT_LINE_VERDICT.md", "docs/validation/BONN_STATUS.md"):
        fp = root / rel
        if fp.is_file():
            for line in fp.read_text().lower().splitlines():
                for pat in FORBIDDEN:
                    if re.search(pat, line) and not _neg_ok(line):
                        check(f"forbidden_claim:{rel}", False, f"{pat!r}: {line.strip()[:50]}")
                        break

    # docs carry final state
    for rel in ("FORMAL_VERDICT.md", "docs/validation/BONN_STATUS.md"):
        fp = root / rel
        if fp.is_file() and final_state:
            check(f"final_state_in:{rel}", final_state in fp.read_text())

    status = "PASS" if not failures else "FAIL"
    result = {
        "status": status, "final_state": final_state,
        "checks": checks, "failures": failures, "warnings": warnings,
        "timestamp_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "git_commit": subprocess.run(["git", "rev-parse", "HEAD"], capture_output=True, text=True,
                                     cwd=root).stdout.strip(),
    }
    if a.output:
        op = root / a.output if not Path(a.output).is_absolute() else Path(a.output)
        op.parent.mkdir(parents=True, exist_ok=True)
        op.write_text(json.dumps(result, indent=2) + "\n")
    print(f"RELEASE_CHECK: {status} (final_state={final_state})")
    for f in failures:
        print("  -", f)
    return 0 if status == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
