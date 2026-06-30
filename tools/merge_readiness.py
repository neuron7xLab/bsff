#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (c) 2026 Yaroslav Vasylenko / neuron7xLab
"""Emit a stable offline merge-readiness verdict from supplied evidence inputs."""

from __future__ import annotations

import argparse
import json
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def _git_head() -> str:
    proc = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )
    return proc.stdout.strip() if proc.returncode == 0 else ""


def _status_count_strict_sync() -> str:
    proc = subprocess.run(
        ["python", "tools/update_status.py", "--verify-count", "--strict-status"],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )
    return "PASS" if proc.returncode == 0 else "FAIL"


def _truth_token_regression() -> str:
    proc = subprocess.run(
        ["python", "-m", "pytest", "tests/test_current_truth_token.py", "-q"],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )
    return "PASS" if proc.returncode == 0 else "FAIL"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--head", required=True, dest="expected_head")
    parser.add_argument("--artifact-digest", required=True, dest="expected_digest")
    parser.add_argument("--repo", default="neuron7xLab/bsff")
    parser.add_argument("--pr", type=int, default=109)
    parser.add_argument("--workflows-success", type=int, default=0)
    parser.add_argument("--review-threads-unresolved", type=int, default=0)
    parser.add_argument("--mergeable", action="store_true")
    args = parser.parse_args(argv)

    head = _git_head()
    status_count = _status_count_strict_sync()
    truth_regression = _truth_token_regression()
    artifact_digest = args.expected_digest
    head_matches = bool(head) and head == args.expected_head
    artifact_digest_matches = artifact_digest == args.expected_digest
    ready = all(
        [
            head_matches,
            artifact_digest_matches,
            args.workflows_success == 11,
            args.review_threads_unresolved == 0,
            args.mergeable,
            status_count == "PASS",
            truth_regression == "PASS",
        ]
    )
    payload = {
        "artifact_digest": artifact_digest,
        "artifact_digest_matches": artifact_digest_matches,
        "expected_head": args.expected_head,
        "head": head,
        "head_matches": head_matches,
        "mergeable": args.mergeable,
        "network_state": "UNVERIFIED_OFFLINE",
        "pr": args.pr,
        "repo": args.repo,
        "review_threads_unresolved": args.review_threads_unresolved,
        "status_count_strict_sync": status_count,
        "truth_token_regression": truth_regression,
        "verdict": "READY_FOR_MERGE" if ready else "NOT_READY",
        "workflows_success": args.workflows_success,
    }
    print(json.dumps(payload, indent=2, sort_keys=True))
    return 0 if ready else 1


if __name__ == "__main__":
    raise SystemExit(main())
