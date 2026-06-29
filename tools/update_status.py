#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (c) 2026 Yaroslav Vasylenko / neuron7xLab
"""Regenerate or verify BSFF STATUS.md from repository metadata."""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from pathlib import Path

try:
    import tomllib
except ModuleNotFoundError:  # pragma: no cover - Python 3.10 fallback
    import tomli as tomllib  # type: ignore[no-redef]

ROOT = Path(__file__).resolve().parents[1]
PYPROJECT = ROOT / "pyproject.toml"
CLI = ROOT / "src" / "bsff" / "cli.py"
STATUS = ROOT / "STATUS.md"
TRUTH = ROOT / "artifacts" / "release" / "CURRENT_TRUTH.json"
CI_WORKFLOW = ".github/workflows/ci.yml"
RELEASE_EVIDENCE_PATH = "docs/PR_109_EVIDENCE.md"
STRICT_COUNT_GATE = "tools/update_status.py --verify-count --strict-status"


def read_version() -> str:
    data = tomllib.loads(PYPROJECT.read_text(encoding="utf-8"))
    version = data["project"]["version"]
    if not isinstance(version, str):
        raise SystemExit("pyproject version is not a string")
    return version


def read_current_truth_state() -> str:
    truth = json.loads(TRUTH.read_text(encoding="utf-8"))
    state = truth["latest_validation_state"]
    if not isinstance(state, str) or not state:
        raise SystemExit("CURRENT_TRUTH latest_validation_state is not a string")
    return state


def read_extras() -> list[str]:
    data = tomllib.loads(PYPROJECT.read_text(encoding="utf-8"))
    extras = data.get("project", {}).get("optional-dependencies", {})
    return sorted(extras)


def detect_cli_subcommands() -> list[str]:
    source = CLI.read_text(encoding="utf-8")
    return re.findall(r"""add_parser\(\s*["']([a-z][a-z0-9-]*)["']""", source)


def collect_test_count() -> int:
    proc = subprocess.run(
        [
            sys.executable,
            "-m",
            "pytest",
            "tests/",
            "--collect-only",
            "-p",
            "no:cacheprovider",
        ],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    if proc.returncode != 0:
        raise SystemExit(
            "pytest --collect-only failed; cannot compute test count "
            f"(exit {proc.returncode}).\n{proc.stdout}\n{proc.stderr}"
        )
    matches = re.findall(r"(\d+)\s+tests?\s+collected\s+in\b", proc.stdout)
    if not matches:
        raise SystemExit(
            "could not parse '<N> tests collected in ...' from pytest output"
        )
    return int(matches[-1])


def render_status(
    version: str,
    canonical_state: str,
    test_count: int,
    extras: list[str],
    subcommands: list[str],
) -> str:
    extras_line = ", ".join(f"`{name}`" for name in extras) if extras else "_none declared_"
    rows = [
        "| Field | Value |",
        "|---|---|",
        f"| package_version | `{version}` |",
        f"| canonical_state | `{canonical_state}` |",
        f"| committed_test_count | **{test_count}** |",
        f"| live_collection_gate | `{STRICT_COUNT_GATE}` |",
        "| live_collection_count_source | `pytest tests/ --collect-only -p no:cacheprovider` |",
        f"| cli_subcommand_count | {len(subcommands)} |",
        f"| optional_extras | {extras_line} |",
        "| truth_artifact_path | `artifacts/release/CURRENT_TRUTH.json` |",
        f"| workflow_authority | `{CI_WORKFLOW}` and GitHub Actions for the exact commit |",
        f"| release_evidence_path | `{RELEASE_EVIDENCE_PATH}` |",
        "| current_truth_gate | `tools/validate_current_truth.py` |",
        "| status_sync_gate | `tools/update_status.py --check` |",
        f"| strict_count_sync_gate | `{STRICT_COUNT_GATE}` |",
    ]
    return "\n".join(
        [
            "<!-- SPDX-License-Identifier: CC-BY-4.0 -->",
            "<!-- Copyright (c) 2026 Yaroslav Vasylenko / neuron7xLab -->",
            "<!-- GENERATED FILE -->",
            "",
            "# BSFF status register",
            "",
            *rows,
            "",
        ]
    )


def generate(*, test_count: int | None = None) -> str:
    resolved_count = collect_test_count() if test_count is None else test_count
    return render_status(
        read_version(),
        read_current_truth_state(),
        resolved_count,
        read_extras(),
        detect_cli_subcommands(),
    )


def _read_status_count(text: str) -> int:
    match = re.search(r"committed_test_count \| \*\*(\d+)\*\*", text)
    if not match:
        raise ValueError("STATUS.md is missing committed_test_count")
    count = int(match.group(1))
    if count <= 0:
        raise ValueError("STATUS.md committed_test_count must be positive")
    return count


def _require_contains(text: str, needle: str, label: str) -> None:
    if needle not in text:
        raise ValueError(f"STATUS.md missing {label}: {needle}")


def check_status() -> int:
    if not STATUS.exists():
        print("STATUS.md is missing — run: python tools/update_status.py")
        return 1
    text = STATUS.read_text(encoding="utf-8")
    try:
        _read_status_count(text)
        _require_contains(text, f"| package_version | `{read_version()}` |", "version")
        _require_contains(
            text,
            f"| canonical_state | `{read_current_truth_state()}` |",
            "canonical state",
        )
        _require_contains(
            text,
            f"| cli_subcommand_count | {len(detect_cli_subcommands())} |",
            "CLI subcommand count",
        )
        extras_line = ", ".join(f"`{name}`" for name in read_extras())
        _require_contains(text, f"| optional_extras | {extras_line} |", "extras")
        _require_contains(
            text,
            f"| strict_count_sync_gate | `{STRICT_COUNT_GATE}` |",
            "strict count sync gate",
        )
    except ValueError as exc:
        print(str(exc))
        return 1
    print("STATUS.md: metadata in sync")
    return 0


def verify_count(*, strict_status: bool) -> int:
    live = collect_test_count()
    print(f"pytest collect-only: {live} tests collected")
    if not STATUS.exists():
        print("STATUS.md is missing — cannot compare committed_test_count")
        return 1 if strict_status else 0
    try:
        committed = _read_status_count(STATUS.read_text(encoding="utf-8"))
    except ValueError as exc:
        print(str(exc))
        return 1
    print(f"STATUS.md committed_test_count: {committed}")
    if strict_status and live != committed:
        print(f"STATUS.md strict count mismatch: live={live} committed={committed}")
        return 1
    if strict_status:
        print("STATUS.md strict count sync: PASS")
    else:
        print("pytest collection availability: PASS")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Regenerate / verify BSFF STATUS.md.")
    parser.add_argument("--check", action="store_true")
    parser.add_argument("--verify-count", action="store_true")
    parser.add_argument("--strict-status", action="store_true")
    args = parser.parse_args(argv)

    if args.check and args.verify_count:
        print("choose either --check or --verify-count, not both")
        return 2
    if args.strict_status and not args.verify_count:
        print("--strict-status requires --verify-count")
        return 2
    if args.verify_count:
        return verify_count(strict_status=args.strict_status)
    if args.check:
        return check_status()

    STATUS.write_text(generate(), encoding="utf-8")
    print(f"Wrote {STATUS.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
