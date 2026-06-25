#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (c) 2026 Yaroslav Vasylenko / neuron7xLab
"""Re-validate the red-team corpus matrix WITHOUT trusting its stored verdict.

The generator is the producer; this is the independent acceptor that the final
verdict tool calls so a forged or stale matrix cannot certify itself. It:

  * requires exactly the 14 canonical categories (no missing, no extras, no dups),
  * requires all 8 fields per entry with valid types and enum values,
  * recomputes each per-entry sha256 and rejects any mismatch (forged matrix),
  * recomputes categories_killed from per-entry verdicts and rejects a disagreeing
    stored count,
  * confirms gate verdict == PASS iff every category is KILLED and total == 14.

    python tools/validate_redteam_matrix.py [--path artifacts/redteam/redteam_matrix.json]

Exit 0 iff the matrix is structurally valid AND verdict == PASS; nonzero otherwise.
No network.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_PATH = ROOT / "artifacts" / "redteam" / "redteam_matrix.json"

GATE_NAME = "openai-2026-red-team-corpus"
SEED_ROOT = 2026

EXPECTED_CATEGORIES = frozenset(
    {
        "malformed_signal",
        "poisoned_input",
        "adversarial_surrogate",
        "unstable_statistic",
        "forged_evidence",
        "stale_manifest",
        "missing_provenance",
        "contradictory_claim",
        "nonconverged_null",
        "edge_case_short_series",
        "pathological_constant_series",
        "randomized_label_leakage",
        "benchmark_gaming",
        "cli_misuse",
    }
)
_TOTAL = len(EXPECTED_CATEGORIES)
_CATEGORY_KEYS = (
    "category",
    "input",
    "expected_failure_mode",
    "seed",
    "observed_result",
    "severity",
    "verdict",
    "hash",
)
_HASHED_FIELDS = ("category", "input", "expected_failure_mode", "seed", "observed_result")
_SEVERITIES = frozenset({"low", "medium", "high", "critical"})
_VERDICTS = frozenset({"KILLED", "SURVIVED"})


def _canonical_hash(record: dict[str, Any]) -> str:
    payload = {k: record[k] for k in _HASHED_FIELDS}
    blob = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
    return hashlib.sha256(blob.encode("utf-8")).hexdigest()


def validate(matrix: dict[str, Any]) -> list[str]:
    """Return a list of failures; an empty list means valid AND PASS."""
    failures: list[str] = []

    if matrix.get("gate") != GATE_NAME:
        failures.append(f"gate mismatch: {matrix.get('gate')!r} != {GATE_NAME!r}")
    if matrix.get("seed_root") != SEED_ROOT:
        failures.append(f"seed_root mismatch: {matrix.get('seed_root')!r} != {SEED_ROOT}")

    categories = matrix.get("categories")
    if not isinstance(categories, list):
        failures.append("categories is not a list")
        return failures

    seen: set[str] = set()
    recomputed_killed = 0
    for i, entry in enumerate(categories):
        if not isinstance(entry, dict):
            failures.append(f"category[{i}] is not an object")
            continue
        missing = [k for k in _CATEGORY_KEYS if k not in entry]
        if missing:
            failures.append(f"category[{i}] missing fields: {missing}")
            continue
        extra = [k for k in entry if k not in _CATEGORY_KEYS]
        if extra:
            failures.append(f"category[{i}] unexpected fields: {extra}")

        name = entry["category"]
        if not isinstance(name, str):
            failures.append(f"category[{i}].category not a string")
            continue
        if name in seen:
            failures.append(f"duplicate category: {name}")
        seen.add(name)

        if not isinstance(entry["input"], str):
            failures.append(f"{name}.input not a string")
        if not isinstance(entry["expected_failure_mode"], str):
            failures.append(f"{name}.expected_failure_mode not a string")
        if not isinstance(entry["observed_result"], str):
            failures.append(f"{name}.observed_result not a string")
        if not isinstance(entry["seed"], int) or isinstance(entry["seed"], bool):
            failures.append(f"{name}.seed not an int")
        if entry["severity"] not in _SEVERITIES:
            failures.append(f"{name}.severity invalid: {entry['severity']!r}")
        if entry["verdict"] not in _VERDICTS:
            failures.append(f"{name}.verdict invalid: {entry['verdict']!r}")
        if not isinstance(entry["hash"], str):
            failures.append(f"{name}.hash not a string")

        # Recompute the content hash; a tampered field will not match (forgery).
        expected_hash = _canonical_hash(entry)
        if entry.get("hash") != expected_hash:
            failures.append(f"{name}.hash mismatch (tampered): stored != recomputed")

        if entry.get("verdict") == "KILLED":
            recomputed_killed += 1

    present = frozenset(seen)
    for missing_cat in sorted(EXPECTED_CATEGORIES - present):
        failures.append(f"missing required category: {missing_cat}")
    for extra_cat in sorted(present - EXPECTED_CATEGORIES):
        failures.append(f"unexpected category: {extra_cat}")

    total = matrix.get("categories_total")
    if total != _TOTAL:
        failures.append(f"categories_total {total!r} != {_TOTAL}")

    stored_killed = matrix.get("categories_killed")
    if stored_killed != recomputed_killed:
        failures.append(
            f"categories_killed mismatch: stored {stored_killed!r} != recomputed {recomputed_killed}"
        )

    all_killed = recomputed_killed == len(present) == _TOTAL
    expected_verdict = "PASS" if all_killed else "FAIL"
    if matrix.get("verdict") != expected_verdict:
        failures.append(
            f"verdict {matrix.get('verdict')!r} disagrees with recompute {expected_verdict!r}"
        )
    if matrix.get("verdict") != "PASS":
        failures.append(f"gate verdict is not PASS: {matrix.get('verdict')!r}")

    return failures


def run(path: Path) -> tuple[bool, list[str]]:
    """Load and validate the matrix at ``path``. Returns (ok, failures)."""
    try:
        matrix = json.loads(path.read_text(encoding="utf-8"))
    except OSError as exc:
        return False, [f"cannot read matrix: {exc}"]
    except json.JSONDecodeError as exc:
        return False, [f"matrix is not valid JSON: {exc}"]
    if not isinstance(matrix, dict):
        return False, ["matrix root is not an object"]
    failures = validate(matrix)
    return (not failures), failures


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--path", type=Path, default=DEFAULT_PATH)
    args = parser.parse_args(argv)

    ok, failures = run(args.path)
    if ok:
        print(f"redteam matrix VALID and PASS: {args.path}")
        return 0
    print(f"redteam matrix REJECTED: {args.path}")
    for failure in failures:
        print(f"  - {failure}")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
