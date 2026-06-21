# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (c) 2026 Yaroslav Vasylenko / neuron7xLab
"""Validate that every null hypothesis is explicit and complete (fail-closed).

Each entry must carry a statement, a test method, a reject condition, and a
failure status. A p-value with no registered H0 is not allowed.
"""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REQUIRED = ("statement", "tested_by", "reject_if", "failure_status")


def main(argv: list[str] | None = None) -> int:
    import yaml

    path = ROOT / "null_hypotheses.yaml"
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    nulls = (data or {}).get("nulls", {})
    if not nulls:
        print("FAIL: no nulls registered")
        return 1
    failures = []
    for name, spec in nulls.items():
        for field in REQUIRED:
            if not spec.get(field):
                failures.append(f"{name}: missing '{field}'")
    if failures:
        print("Null registry FAILURES:")
        for f in failures:
            print(f"  - {f}")
        return 1
    print(f"Null registry OK: {len(nulls)} hypotheses, all complete.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
