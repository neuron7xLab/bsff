# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (c) 2026 Yaroslav Vasylenko / neuron7xLab
"""Make the claim audit unable to lie — deterministic, fail-closed enforcement.

The coupling rule and status discipline of CLAIM_AUDIT.md were prose; this turns
them into a machine check that blocks merge. Enforced invariants:

  * only the allowed status vocabulary (VERIFIED / FALSE / UNPROVEN /
    NEEDS_EXTERNAL_CHECK, plus "NOT VERIFIED"); soft states (PASS, OK, LIKELY,
    STRONG, PROBABLY, GOOD) are forbidden;
  * every VERIFIED row carries a command (a backticked invocation) AND a
    non-empty value/hash;
  * every FALSE / UNPROVEN / NEEDS_EXTERNAL_CHECK row carries a non-empty reason;
  * the governing status-coupling rule section is present.

A claim that cannot show its command and value cannot be VERIFIED. That is the
anti-decoration floor, enforced by exit code, not by trust.
"""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FORBIDDEN_SOFT = ("PASS", "OK", "LIKELY", "STRONG", "PROBABLY", "GOOD", "SEEMS")
ALLOWED_PRIMARY = ("VERIFIED", "NOT VERIFIED", "FALSE", "UNPROVEN", "NEEDS_EXTERNAL_CHECK")


def _cells(line: str) -> list[str]:
    return [c.strip() for c in line.strip().strip("|").split("|")]


def _is_data_row(cells: list[str]) -> bool:
    return len(cells) == 6 and bool(re.match(r"^[0-9]+[a-z]?$", cells[0]))


def _status_token(raw: str) -> str:
    s = raw.replace("*", "").strip()
    if s.upper().startswith("NOT VERIFIED"):
        return "NOT VERIFIED"
    return s.split()[0].split("(")[0].split("/")[0].strip() if s else ""


def audit(path: Path) -> dict:
    text = path.read_text(encoding="utf-8")
    failures: list[str] = []
    rows = 0
    verified = 0

    if "status coupling" not in text.lower():
        failures.append("missing governing 'status coupling' rule section")

    for line in text.splitlines():
        if not line.startswith("|"):
            continue
        cells = _cells(line)
        if not _is_data_row(cells):
            continue
        rows += 1
        rid, _claim, evidence, command, value, status_raw = cells
        token = _status_token(status_raw)
        su = status_raw.replace("*", "").upper()

        for soft in FORBIDDEN_SOFT:
            if re.search(rf"\b{soft}\b", su):
                failures.append(f"row {rid}: forbidden soft-state '{soft}' in status")
        if token not in ALLOWED_PRIMARY:
            failures.append(f"row {rid}: status '{token}' not in allowed vocabulary")

        if token == "VERIFIED":
            verified += 1
            if "`" not in command:
                failures.append(f"row {rid}: VERIFIED without a command (no backticked invocation)")
            if not value:
                failures.append(f"row {rid}: VERIFIED without a value/hash")
        elif token in ("FALSE", "UNPROVEN", "NEEDS_EXTERNAL_CHECK", "NOT VERIFIED"):
            if not (value or evidence):
                failures.append(f"row {rid}: {token} without a reason")

    if rows == 0:
        failures.append("no claim rows parsed — audit table missing or malformed")

    return {"rows": rows, "verified": verified, "failures": failures, "ok": not failures}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, default=ROOT / "CLAIM_AUDIT.md")
    parser.add_argument(
        "--output",
        type=Path,
        default=ROOT / "artifacts" / "claim_audit" / "CLAIM_AUDIT_RESULT.json",
    )
    args = parser.parse_args(argv)

    result = audit(args.input)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2), encoding="utf-8")

    print(f"claim audit: {result['rows']} rows, {result['verified']} VERIFIED")
    for f in result["failures"]:
        print(f"  FAIL: {f}")
    if not result["ok"]:
        return 1
    print(
        "claim audit: every VERIFIED has a command + value; no soft states; coupling rule present."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
