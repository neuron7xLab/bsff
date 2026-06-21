#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (c) 2026 Yaroslav Vasylenko / neuron7xLab
"""Validate governed JSON artifacts against the canonical schema, fail-closed.

An artifact is *governed* once it declares ``schema_version``. Governed artifacts
must carry a non-empty schema_version and may not contradict the single sources of
truth: a ``version``/``package_version`` field must equal pyproject's version and a
``test_count`` field must equal STATUS.md's live count. This is the generic form of
the stale-MANIFEST defect (0.1.4 vs 0.4.0): any governed artifact that drifts from
truth fails here.

Ungoverned artifacts (no schema_version yet) are reported for coverage visibility,
never silently passed off as governed.

    python tools/validate_artifact_schema.py
"""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

try:
    import tomllib
except ModuleNotFoundError:  # pragma: no cover
    import tomli as tomllib  # type: ignore[no-redef]

ROOT = Path(__file__).resolve().parents[1]
ARTIFACT_DIR = ROOT / "artifacts"

# Full governed-artifact descriptor: a governed artifact must describe itself.
REQUIRED_GOVERNED_FIELDS = ("schema_version", "artifact_type", "package", "generator", "verdict")
# Volatile provenance — required only for artifacts that declare ci_emitted=true,
# so the committed deterministic core stays --check-able.
CI_PROVENANCE_FIELDS = ("commit_sha", "workflow_run_id", "generated_at_utc")


def _pyproject_version() -> str:
    data = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    return str(data["project"]["version"])


def _status_count() -> int | None:
    m = re.search(
        r"Live test count \| \*\*(\d+)\*\*", (ROOT / "STATUS.md").read_text(encoding="utf-8")
    )
    return int(m.group(1)) if m else None


def validate() -> dict:
    version = _pyproject_version()
    count = _status_count()
    governed: list[str] = []
    ungoverned: list[str] = []
    failures: list[str] = []

    for path in sorted(ARTIFACT_DIR.glob("*.json")):
        rel = path.relative_to(ROOT).as_posix() if ROOT in path.parents else path.name
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            failures.append(f"{rel}: invalid JSON")
            continue
        if not isinstance(data, dict) or not data.get("schema_version"):
            ungoverned.append(rel)
            continue
        governed.append(rel)
        for field in REQUIRED_GOVERNED_FIELDS:
            if not data.get(field):
                failures.append(f"{rel}: governed artifact missing required field '{field}'")
        if data.get("ci_emitted"):
            for field in CI_PROVENANCE_FIELDS:
                if not data.get(field):
                    failures.append(f"{rel}: ci_emitted artifact missing provenance '{field}'")
        for vkey in ("version", "package_version"):
            if vkey in data and str(data[vkey]) != version:
                failures.append(f"{rel}: {vkey}={data[vkey]} != pyproject {version}")
        if "test_count" in data and count is not None and int(data["test_count"]) != count:
            failures.append(f"{rel}: test_count={data['test_count']} != STATUS {count}")

    return {
        "governed": governed,
        "ungoverned": ungoverned,
        "failures": failures,
        "ok": not failures,
    }


def main(argv: list[str] | None = None) -> int:
    argparse.ArgumentParser(description=__doc__).parse_args(argv)
    r = validate()
    print(f"artifact schema: {len(r['governed'])} governed, {len(r['ungoverned'])} ungoverned")
    for f in r["failures"]:
        print(f"  FAIL: {f}")
    if r["ungoverned"]:
        print("  (ungoverned, not yet schema-bound: " + ", ".join(r["ungoverned"]) + ")")
    if not r["ok"]:
        return 1
    print("artifact schema: every governed artifact matches pyproject + STATUS.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
