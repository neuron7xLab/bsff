#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (c) 2026 Yaroslav Vasylenko / neuron7xLab
"""Cyclomatic-complexity ratchet gate.

Shells out to ``radon cc`` over the target paths and FAILs when any
function or method has a cyclomatic complexity above the ceiling
(``CC <= 15``, radon grade C). A small committed allowlist freezes the
current genuinely-hard offenders so this behaves as a *ratchet*: new or
edited code cannot exceed the ceiling, while existing debt stays visible
and bounded until it is decomposed.

Allowlist semantics (``tools/complexity_allowlist.json``):
  ``"relpath::qualified_name" -> recorded_cc``
An offender is tolerated only if it is allowlisted AND its live CC has not
risen above the recorded value. A live CC above the recorded value (or an
allowlist entry whose function no longer exceeds the ceiling) is surfaced.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

SCHEMA = "bsff.complexity/v1"
CEILING = 15
ROOT = Path(__file__).resolve().parents[1]
DEFAULT_PATHS = ("src/bsff",)
ALLOWLIST_PATH = Path(__file__).resolve().parent / "complexity_allowlist.json"


def _qualified_name(block):
    """Return ``Class.method`` for methods, plain ``name`` otherwise."""
    name = block.get("name", "")
    classname = block.get("classname")
    return f"{classname}.{name}" if classname else name


def _run_radon(root, paths):
    """Invoke ``python -m radon cc <paths> -j`` and parse the JSON payload."""
    cmd = [sys.executable, "-m", "radon", "cc", *paths, "-j"]
    completed = subprocess.run(
        cmd,
        cwd=str(root),
        capture_output=True,
        text=True,
        check=True,
    )
    return json.loads(completed.stdout)


def _load_allowlist(path=ALLOWLIST_PATH):
    """Load the ``key -> recorded_cc`` mapping (empty if the file is absent)."""
    try:
        data = json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}
    allow = data.get("allowlist", {})
    return {str(k): int(v) for k, v in allow.items()}


def _iter_blocks(radon_data, root):
    """Yield ``(key, complexity)`` for every function/method radon reported."""
    root = Path(root)
    for file_path, blocks in radon_data.items():
        try:
            rel = str(Path(file_path).resolve().relative_to(root))
        except ValueError:
            rel = file_path
        for block in blocks:
            if not isinstance(block, dict) or "complexity" not in block:
                continue
            yield f"{rel}::{_qualified_name(block)}", int(block["complexity"])


def evaluate(root=ROOT, paths=DEFAULT_PATHS, allowlist_path=ALLOWLIST_PATH):
    """Evaluate the complexity ratchet over ``paths`` beneath ``root``.

    Returns a report dict with ``schema``, ``ceiling``, ``violations``
    (non-allowlisted offenders, or allowlisted ones whose CC has grown),
    ``allowlisted`` (frozen offenders still within their recorded CC), and
    an aggregate ``status`` of ``PASS``/``FAIL``.
    """
    root = Path(root)
    allowlist = _load_allowlist(allowlist_path)
    radon_data = _run_radon(root, paths)

    violations = []
    allowlisted = []
    for key, cc in sorted(_iter_blocks(radon_data, root)):
        if cc <= CEILING:
            continue
        recorded = allowlist.get(key)
        if recorded is None:
            violations.append(
                {
                    "target": key,
                    "complexity": cc,
                    "ceiling": CEILING,
                    "reason": "exceeds ceiling and not allowlisted",
                }
            )
        elif cc > recorded:
            violations.append(
                {
                    "target": key,
                    "complexity": cc,
                    "allowed": recorded,
                    "ceiling": CEILING,
                    "reason": "exceeds frozen allowlist value (ratchet regression)",
                }
            )
        else:
            allowlisted.append({"target": key, "complexity": cc, "allowed": recorded})

    return {
        "schema": SCHEMA,
        "ceiling": CEILING,
        "violations": violations,
        "allowlisted": allowlisted,
        "status": "PASS" if not violations else "FAIL",
    }


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="exit 1 on any violation")
    parser.add_argument(
        "--paths",
        nargs="*",
        default=list(DEFAULT_PATHS),
        help="paths to scan (relative to repo root)",
    )
    parser.add_argument("--json", action="store_true", help="emit the full report as JSON")
    args = parser.parse_args(argv)

    report = evaluate(paths=tuple(args.paths))
    if args.json:
        print(json.dumps(report, indent=2, sort_keys=True))
    else:
        print(f"COMPLEXITY_GATE: {report['status']} (ceiling CC<={report['ceiling']})")
        print(f"allowlisted (frozen debt): {len(report['allowlisted'])}")
        for item in report["allowlisted"]:
            print(f"  ~ {item['target']} CC={item['complexity']} (allowed {item['allowed']})")
        for item in report["violations"]:
            print(f"  - {item['target']} CC={item['complexity']}: {item['reason']}")

    if args.check and report["violations"]:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
