#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (c) 2026 Yaroslav Vasylenko / neuron7xLab
"""Regenerate or verify BSFF STATUS.md from repository metadata.

``--check`` is intentionally cheap: it validates committed metadata without
running pytest collection. ``--verify-count`` is the explicit slow collection gate.
"""

from __future__ import annotations

import argparse
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
CI_WORKFLOW = ".github/workflows/ci.yml"


def read_version() -> str:
    data = tomllib.loads(PYPROJECT.read_text(encoding="utf-8"))
    version = data["project"]["version"]
    if not isinstance(version, str):
        raise SystemExit("pyproject version is not a string")
    return version


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
        raise SystemExit("could not parse '<N> tests collected in ...' from pytest output")
    return int(matches[-1])


def render_status(
    version: str,
    test_count: int,
    extras: list[str],
    subcommands: list[str],
) -> str:
    extras_line = ", ".join(f"`{name}`" for name in extras) if extras else "_none declared_"
    sub_rows = "\n".join(f"| `bsff {name}` |" for name in subcommands)
    return "\n".join(
        [
            "<!-- SPDX-License-Identifier: CC-BY-4.0 -->",
            "<!-- Copyright (c) 2026 Yaroslav Vasylenko / neuron7xLab -->",
            "<!-- GENERATED FILE — edit tools/update_status.py, then run it. Do not edit by hand. -->",
            "",
            "# BSFF status",
            "",
            "Single source of truth for release status. Generated from repository metadata by",
            "`python tools/update_status.py`. CI enforces deterministic sync with",
            "`python tools/update_status.py --check`.",
            "",
            "## Current state",
            "",
            "| Field | Value |",
            "|---|---|",
            f"| Package version | `{version}` |",
            f"| Live test count | **{test_count}** (collected by `pytest tests/`) |",
            f"| CLI subcommands | {len(subcommands)} (parsed from `src/bsff/cli.py`) |",
            f"| Optional extras | {extras_line} |",
            "",
            "## CI state",
            "",
            f"CI is defined by [`{CI_WORKFLOW}`]({CI_WORKFLOW}).",
            "The GitHub Actions run for the relevant commit is authoritative.",
            "",
            "## CLI surface",
            "",
            "| Command |",
            "|---|",
            sub_rows,
            "",
        ]
    )


def generate(*, test_count: int | None = None) -> str:
    resolved_count = collect_test_count() if test_count is None else test_count
    return render_status(read_version(), resolved_count, read_extras(), detect_cli_subcommands())


def _read_status_count(text: str) -> int:
    match = re.search(r"Live test count \| \*\*(\d+)\*\*", text)
    if not match:
        raise ValueError("STATUS.md is missing a live test count")
    count = int(match.group(1))
    if count <= 0:
        raise ValueError("STATUS.md live test count must be positive")
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
        _require_contains(text, f"| Package version | `{read_version()}` |", "version")
        _require_contains(
            text,
            f"| CLI subcommands | {len(detect_cli_subcommands())}",
            "CLI subcommand count",
        )
        extras_line = ", ".join(f"`{name}`" for name in read_extras())
        _require_contains(text, f"| Optional extras | {extras_line} |", "extras")
    except ValueError as exc:
        print(str(exc))
        return 1
    print("STATUS.md: in sync")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Regenerate / verify BSFF STATUS.md.")
    parser.add_argument("--check", action="store_true")
    parser.add_argument("--verify-count", action="store_true")
    args = parser.parse_args(argv)

    if args.check and args.verify_count:
        print("choose either --check or --verify-count, not both")
        return 2
    if args.verify_count:
        count = collect_test_count()
        print(f"pytest collect-only: {count} tests collected")
        if STATUS.exists():
            try:
                print(f"STATUS.md committed live count: {_read_status_count(STATUS.read_text(encoding='utf-8'))}")
            except ValueError as exc:
                print(str(exc))
                return 1
        return 0
    if args.check:
        return check_status()

    STATUS.write_text(generate(), encoding="utf-8")
    print(f"Wrote {STATUS.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
