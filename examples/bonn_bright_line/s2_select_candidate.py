#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (c) 2026 Yaroslav Vasylenko / neuron7xLab
"""S2 selection lock (Phase I): freeze exactly ONE candidate that passed exploratory
G1+G2 (or NONE). The lock is written before any confirmatory run; the frozen params /
alpha / thresholds must not change afterwards."""

from __future__ import annotations

import argparse
import json
import subprocess
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def main(argv=None) -> int:
    p = argparse.ArgumentParser()
    p.add_argument(
        "--exploratory", default="artifacts/bonn_bright_line/s2_EXPLORATORY_RESULTS.json"
    )
    p.add_argument("--output", default="artifacts/bonn_bright_line/S2_SELECTION_LOCK.json")
    a = p.parse_args(argv)

    expl = json.loads((ROOT / a.exploratory).read_text())
    from s2_candidate_registry import CANDIDATES

    reg = {c["id"]: c for c in CANDIDATES}

    passing = [r for r in expl["results"] if r.get("status") == "PASS"]
    # Tie-break: lowest combined_FPR, then highest Set-E power. Pre-declared, deterministic.
    passing.sort(key=lambda r: (r["combined_FPR"], -r["G1_E_survived"]))
    commit = subprocess.run(
        ["git", "rev-parse", "HEAD"], capture_output=True, text=True, cwd=ROOT
    ).stdout.strip()

    if not passing:
        lock = {
            "S2_SELECTION": "NONE",
            "reason": "no candidate achieved G1+G2 exploratory criteria",
            "exploratory": a.exploratory,
            "git_commit": commit,
            "timestamp_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        }
    else:
        win = passing[0]
        cand = reg[win["id"]]
        lock = {
            "S2_SELECTION": win["id"],
            "family": cand["family"],
            "rule": cand["rule"],
            "frozen_params": cand["params"],
            "alpha_frozen": 0.05,
            "thresholds_frozen": {"G1_min": 0.80, "G2_max_fpr": 0.05},
            "selection_reason": f"lowest combined_FPR ({win['combined_FPR']}) among "
            f"{len(passing)} passing candidate(s), then highest Set-E power",
            "exploratory_metrics": {
                k: win.get(k)
                for k in (
                    "G1_E_survived",
                    "G1_A_not_survived",
                    "G1_B_not_survived",
                    "FPR_A",
                    "FPR_B",
                    "combined_FPR",
                )
            },
            "forbidden_changes": [
                "alpha",
                "thresholds",
                "params",
                "candidate after freeze",
                "set removal",
                "segment cherry-picking",
            ],
            "git_commit": commit,
            "timestamp_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        }
    (ROOT / a.output).write_text(json.dumps(lock, indent=2) + "\n", encoding="utf-8")
    print(f"S2_SELECTION: {lock['S2_SELECTION']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
