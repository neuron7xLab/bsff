#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
"""Validate artifact-bound statistical proof for BSFF claim evidence."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from bsff.statistics.proof_gate import (  # noqa: E402
    DEFAULT_REPORT,
    evaluate,
    validate_report_in_sync,
    write_report,
)


def main(argv: list[str] | None = None, *, root: Path | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true")
    parser.add_argument("--output", default=DEFAULT_REPORT)
    args = parser.parse_args(argv)
    resolved_root = ROOT if root is None else root
    output = resolved_root / args.output
    report = evaluate(resolved_root)
    if args.check:
        sync_violations = validate_report_in_sync(report, output)
        if sync_violations:
            report = {
                **report,
                "status": "FAIL",
                "violations": [*report["violations"], *sync_violations],
            }
    else:
        write_report(report, output)
    print(f"STATISTICAL_PROOF_GATE: {report['status']}")
    print(f"proof_count: {report['proof_count']}")
    for violation in report["violations"]:
        print(f"  - {violation}")
    return 0 if report["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
