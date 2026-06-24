#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (c) 2026 Yaroslav Vasylenko / neuron7xLab
"""Audit a BNCI executable lock for execution-readiness (Phase 2).

Returns exactly one of: BNCI_LOCK_EXECUTABLE | BNCI_BLOCKED_LOCK_INCOMPLETE |
BNCI_BLOCKED_METHOD | BNCI_BLOCKED_DATA. Fail-closed: any execution-critical gap blocks.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def audit(lock: dict) -> dict:
    checks = []

    def chk(name, ok, detail=""):
        checks.append({"check": name, "ok": bool(ok), "detail": detail})

    runner = lock.get("runner", "")
    chk("status_executable", lock.get("status") == "COMPLETE_EXECUTABLE_LOCK", lock.get("status"))
    chk("runner_declared", bool(runner), runner)
    chk("runner_exists", bool(runner) and (ROOT / runner).is_file(), runner)
    cmds = " ".join(lock.get("exact_commands", []))
    chk(
        "no_placeholder_command",
        "..." not in cmds,
        "literal '...' present" if "..." in cmds else "ok",
    )
    chk(
        "statistic_declared",
        "sampen" in (lock.get("statistic", "") + lock.get("statistic_id", "")).lower(),
        lock.get("statistic"),
    )
    chk(
        "channel_aggregation_specified",
        bool(lock.get("channel_aggregation")),
        lock.get("channel_aggregation"),
    )
    chk("epoch_policy_specified", bool(lock.get("epoch_policy")), lock.get("epoch_policy"))
    chk("alpha_frozen", lock.get("alpha") == 0.05, str(lock.get("alpha")))
    chk(
        "subjects_frozen",
        lock.get("subjects") == [1, 2, 3, 4, 5, 6, 7, 8, 9],
        str(lock.get("subjects")),
    )
    chk("thresholds_frozen", bool(lock.get("success_threshold")), "present")
    chk(
        "method_not_csp",
        "csp" not in cmds.lower() and "lda" not in cmds.lower(),
        "runner command must not be CSP/LDA decoding",
    )
    chk(
        "forbidden_present",
        bool(lock.get("forbidden")),
        f"{len(lock.get('forbidden', []))} entries",
    )

    incomplete = [c["check"] for c in checks if not c["ok"]]
    state = "BNCI_LOCK_EXECUTABLE" if not incomplete else "BNCI_BLOCKED_LOCK_INCOMPLETE"
    return {"state": state, "checks": checks, "incomplete": incomplete}


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--lock", required=True)
    ap.add_argument("--output", required=True)
    a = ap.parse_args(argv)
    lock = json.loads(Path(a.lock).read_text())
    res = audit(lock)
    commit = subprocess.run(
        ["git", "rev-parse", "HEAD"], capture_output=True, text=True, cwd=ROOT
    ).stdout.strip()
    out = {
        "schema": "bsff.bnci_lock_audit/v2",
        "state": res["state"],
        "lock": a.lock,
        "checks": res["checks"],
        "incomplete": res["incomplete"],
        "git_commit": commit,
        "timestamp_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
    }
    Path(a.output).parent.mkdir(parents=True, exist_ok=True)
    Path(a.output).write_text(json.dumps(out, indent=2) + "\n")
    print(f"LOCK_AUDIT: {res['state']}")
    for c in res["incomplete"]:
        print("  [X]", c)
    return 0 if res["state"] == "BNCI_LOCK_EXECUTABLE" else 1


if __name__ == "__main__":
    raise SystemExit(main())
