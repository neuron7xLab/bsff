#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (c) 2026 Yaroslav Vasylenko / neuron7xLab
"""Lock-integrity gate: every dependency must be pinned AND hashed.

Hermetic CI is only hermetic if the lock files cannot float. This fail-closed gate
parses each ``requirements/*.lock`` and asserts:

* every requirement is an exact ``==`` pin (no ``>=``/``~=``/``<`` ranges);
* every pinned requirement carries at least one ``--hash=sha256:`` digest;
* no editable (``-e``) or VCS/URL requirements leak in;
* the expected runtime essentials are present in ``ci.lock``.

Any violation exits non-zero. Standard library only; no network.

    python tools/validate_lockfiles.py
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
LOCK_DIR = ROOT / "requirements"
EXPECTED_LOCKS = ("ci.lock", "dev.lock", "fuzz.lock", "security.lock")
CI_ESSENTIALS = ("numpy", "scipy", "statsmodels")

_PIN_RE = re.compile(r"^(?P<name>[A-Za-z0-9._-]+)==(?P<ver>[^\s;]+)")
_RANGE_RE = re.compile(r"^[A-Za-z0-9._-]+\s*(>=|<=|~=|!=|<|>)(?![=])")


def _parse_lock(path: str) -> tuple[dict[str, list[str]], list[str]]:
    """Return ({package==version: [hashes]}, [violations]) for one lock file."""
    text = (LOCK_DIR / path).read_text(encoding="utf-8")
    pins: dict[str, list[str]] = {}
    violations: list[str] = []
    current: str | None = None
    for raw in text.splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith("-e ") or "git+" in line or "://" in line:
            violations.append(f"{path}: non-hermetic requirement: {line}")
            continue
        pin = _PIN_RE.match(line)
        if pin:
            current = f"{pin.group('name')}=={pin.group('ver')}"
            pins.setdefault(current, [])
            continue
        if line.startswith("--hash="):
            if current is not None:
                pins[current].append(line.split("--hash=", 1)[1].rstrip(" \\"))
            continue
        if _RANGE_RE.match(line) and "--hash" not in line:
            violations.append(f"{path}: unpinned (ranged) requirement: {line}")
    return pins, violations


def main() -> int:
    failures: list[str] = []
    if not LOCK_DIR.is_dir():
        print("requirements/ directory is missing")
        return 1
    for lock in EXPECTED_LOCKS:
        if not (LOCK_DIR / lock).is_file():
            failures.append(f"missing lock file: requirements/{lock}")
            continue
        pins, violations = _parse_lock(lock)
        failures.extend(violations)
        if not pins:
            failures.append(f"{lock}: no pinned requirements found")
        for pin, hashes in pins.items():
            if not hashes:
                failures.append(f"{lock}: requirement is not hashed: {pin}")
    # ci.lock must carry the runtime essentials, pinned.
    ci_pins, _ = _parse_lock("ci.lock")
    ci_names = {p.split("==", 1)[0].lower().replace("_", "-") for p in ci_pins}
    for essential in CI_ESSENTIALS:
        if essential not in ci_names:
            failures.append(f"ci.lock: runtime essential missing: {essential}")

    if failures:
        print("Lock integrity FAILED:")
        for item in failures:
            print(f"- {item}")
        return 1
    total = sum(len(_parse_lock(lock)[0]) for lock in EXPECTED_LOCKS)
    print(f"Lock integrity: PASS ({len(EXPECTED_LOCKS)} locks, {total} pinned+hashed requirements)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
