#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (c) 2026 Yaroslav Vasylenko / neuron7xLab
"""Generate (or --check) artifacts/MANIFEST.json as generated truth, fail-closed."""

from __future__ import annotations

import argparse
import json
import os
import re
from pathlib import Path

try:
    import tomllib
except ModuleNotFoundError:  # pragma: no cover - py3.10 fallback
    import tomli as tomllib  # type: ignore[no-redef]

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "artifacts" / "MANIFEST.json"

RELEASE_GATES = [
    "truth_contract",
    "architecture_contract",
    "status_sync",
    "status_count_strict_sync",
    "manifest_sync",
    "ip_provenance",
    "secret_scan",
    "release_check_strict",
    "codeql_high",
]


def _version() -> str:
    data = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    return str(data["project"]["version"])


def _test_count() -> int:
    m = re.search(
        r"committed_test_count \| \*\*(\d+)\*\*",
        (ROOT / "STATUS.md").read_text(encoding="utf-8"),
    )
    if not m:
        raise SystemExit("could not read committed_test_count from STATUS.md")
    return int(m.group(1))


def build_core() -> dict:
    return {
        "schema_version": "bsff.manifest/v1",
        "artifact_type": "release_manifest",
        "package": "bsff",
        "generator": "tools/generate_manifest.py",
        "version": _version(),
        "test_count": _test_count(),
        "release_gates": RELEASE_GATES,
        "inputs": ["pyproject.toml", "STATUS.md"],
        "outputs": ["artifacts/MANIFEST.json"],
        "verdict": "GENERATED",
        "source_of_truth": "pyproject.toml + STATUS.md; strict count sync enforced separately",
    }


def _with_ci(core: dict) -> dict:
    return {
        **core,
        "commit_sha": os.environ.get("GITHUB_SHA", ""),
        "workflow_run_id": os.environ.get("GITHUB_RUN_ID", ""),
        "generated_at_utc": os.environ.get("BSFF_BUILD_UTC", ""),
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true")
    parser.add_argument("--ci", action="store_true", help="augment with commit/run/timestamp env")
    args = parser.parse_args(argv)

    core = build_core()
    if args.check:
        if not OUT.is_file():
            print("artifacts/MANIFEST.json missing — run: python tools/generate_manifest.py")
            return 1
        committed = json.loads(OUT.read_text(encoding="utf-8"))
        committed_core = {k: committed.get(k) for k in core}
        if committed_core != core:
            print(
                "MANIFEST.json is STALE vs pyproject/STATUS — run: python tools/generate_manifest.py"
            )
            print(f"  expected: version={core['version']} test_count={core['test_count']}")
            print(
                f"  found:    version={committed.get('version')} test_count={committed.get('test_count')}"
            )
            return 1
        print(f"MANIFEST.json: in sync (version {core['version']}, {core['test_count']} tests)")
        return 0

    payload = _with_ci(core) if args.ci else core
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    print(f"Wrote {OUT.relative_to(ROOT)} (version {core['version']}, {core['test_count']} tests)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
