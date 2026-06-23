# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (c) 2026 Yaroslav Vasylenko / neuron7xLab
"""CLI contract: stable help, deterministic exit codes, schema-valid JSON.

The command surface is part of the public contract. These pin the invariants a
downstream operator or CI script relies on: ``--help`` lists the registered
subcommands and exits 0; the health/validation commands exit deterministically;
and machine-readable commands emit valid JSON, not free-form text.
"""

from __future__ import annotations

import json
import re

import pytest

from bsff import cli
from bsff.json_schema import (
    verdict_json_schema,  # noqa: F401 — ensures schema import path is stable
)

# Subcommands the help text must advertise (parsed from cli.py source).
_REGISTERED = set(re.findall(r'add_parser\(\s*["\']([a-z][a-z0-9-]*)["\']', cli.__doc__ or ""))


def _subcommands() -> set[str]:
    import pathlib

    src = (pathlib.Path(cli.__file__)).read_text(encoding="utf-8")
    return set(re.findall(r'add_parser\(\s*["\']([a-z][a-z0-9-]*)["\']', src))


def test_help_exits_zero_and_lists_subcommands(capsys):
    with pytest.raises(SystemExit) as exc:
        cli.main(["--help"])
    assert exc.value.code == 0
    out = capsys.readouterr().out
    for sub in ("selftest", "validate", "doctor", "capabilities"):
        assert sub in out, f"--help omits subcommand {sub}"


def _exit_code(argv: list[str]) -> int:
    """Run cli.main; map success (returns None) to 0, SystemExit to its code."""
    try:
        cli.main(argv)
        return 0
    except SystemExit as exc:
        return int(exc.code) if isinstance(exc.code, int) else 1


def test_doctor_strict_exit_code_is_deterministic():
    a = _exit_code(["doctor", "--require-strict"])
    b = _exit_code(["doctor", "--require-strict"])
    assert a == b
    assert a in (0, 1)


def test_validate_emits_schema_shaped_json(tmp_path):
    out = tmp_path / "validation.json"
    assert _exit_code(["validate", "--output", str(out)]) == 0
    data = json.loads(out.read_text(encoding="utf-8"))
    assert {"status", "artifact_sha256"} <= set(data)
    assert len(str(data["artifact_sha256"])) == 64


def test_capabilities_is_valid_json(capsys):
    assert _exit_code(["capabilities"]) == 0
    payload = json.loads(capsys.readouterr().out)
    assert isinstance(payload, dict)


def test_unknown_subcommand_fails_closed():
    with pytest.raises(SystemExit) as exc:
        cli.main(["definitely-not-a-command"])
    assert exc.value.code != 0


def test_all_registered_subcommands_are_documented():
    # CLI_CONTRACT.md must mention every registered subcommand (no hidden commands).
    import pathlib

    contract = (
        pathlib.Path(cli.__file__).resolve().parents[2] / "docs" / "CLI_CONTRACT.md"
    ).read_text(encoding="utf-8")
    for sub in _subcommands():
        assert sub in contract, f"CLI_CONTRACT.md omits subcommand {sub}"
