#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (c) 2026 Yaroslav Vasylenko / neuron7xLab
"""Deterministic SARIF triage for CodeQL output.

GitHub's Security tab shows alerts; it does not, by itself, *fail a build* on a
project-specific severity policy. This tool turns a SARIF file into a ranked,
machine-readable verdict and a non-zero exit code when findings at or above a
chosen tier are present, so security severity can gate a merge the same way a
failing test does.

Severity is taken from each rule's CodeQL `security-severity` score (a CVSS-style
0-10), falling back to the SARIF result `level` when no score is present.

Usage:
    python tools/triage_sarif.py results.sarif --block-at high
    python tools/triage_sarif.py results.sarif --json artifacts/sarif_triage.json
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

TIERS = ["low", "medium", "high", "critical"]
_LEVEL_TO_TIER = {"error": "high", "warning": "medium", "note": "low", "none": "low"}


def _score_to_tier(score: float) -> str:
    if score >= 9.0:
        return "critical"
    if score >= 7.0:
        return "high"
    if score >= 4.0:
        return "medium"
    return "low"


def _rule_index(run: dict[str, Any]) -> dict[str, dict[str, Any]]:
    rules = run.get("tool", {}).get("driver", {}).get("rules", [])
    return {r.get("id", ""): r for r in rules if isinstance(r, dict)}


def _coerce_float(value: Any) -> float | None:
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _result_tier(result: dict[str, Any], rules: dict[str, dict[str, Any]]) -> str:
    rule = rules.get(result.get("ruleId", ""), {})
    score = _coerce_float(rule.get("properties", {}).get("security-severity"))
    if score is not None:
        return _score_to_tier(score)
    return _LEVEL_TO_TIER.get(str(result.get("level", "warning")), "medium")


def triage(sarif: dict[str, Any]) -> dict[str, Any]:
    counts = dict.fromkeys(TIERS, 0)
    findings: list[dict[str, Any]] = []
    for run in sarif.get("runs", []):
        rules = _rule_index(run)
        for result in run.get("results", []):
            tier = _result_tier(result, rules)
            counts[tier] += 1
            loc = result.get("locations", [{}])
            uri = (
                loc[0].get("physicalLocation", {}).get("artifactLocation", {}).get("uri", "")
                if loc
                else ""
            )
            findings.append({"ruleId": result.get("ruleId", ""), "tier": tier, "uri": uri})
    return {
        "schema": "bsff.sarif_triage.v1",
        "counts": counts,
        "total": sum(counts.values()),
        "findings": findings,
    }


def _at_or_above(counts: dict[str, int], tier: str) -> int:
    cutoff = TIERS.index(tier)
    return sum(counts[t] for t in TIERS[cutoff:])


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("sarif", type=Path)
    parser.add_argument("--block-at", choices=TIERS, default="high")
    parser.add_argument("--json", type=Path, default=None)
    args = parser.parse_args(argv)

    sarif = json.loads(args.sarif.read_text())
    report = triage(sarif)
    blocking = _at_or_above(report["counts"], args.block_at)
    report["block_at"] = args.block_at
    report["blocking_findings"] = blocking
    report["status"] = "FAIL" if blocking else "PASS"

    if args.json is not None:
        args.json.parent.mkdir(parents=True, exist_ok=True)
        args.json.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")

    c = report["counts"]
    print(
        f"SARIF triage: critical={c['critical']} high={c['high']} "
        f"medium={c['medium']} low={c['low']} (block-at={args.block_at})"
    )
    if blocking:
        print(f"SARIF triage: FAIL — {blocking} finding(s) at/above {args.block_at}")
        return 1
    print("SARIF triage: PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
