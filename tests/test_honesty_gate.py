# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (c) 2026 Yaroslav Vasylenko / neuron7xLab
"""The honesty gate runs in CI: decorative lies cannot merge."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

pytest.importorskip("yaml")  # the gate runs YAML-backed registry validators

ROOT = Path(__file__).resolve().parents[1]


def test_claim_audit_validator_rejects_a_decorative_verified(tmp_path):
    # a VERIFIED row with no command must be rejected (the anti-decoration floor).
    bad = tmp_path / "CLAIM_AUDIT.md"
    bad.write_text(
        "## Governing rule (status coupling)\n\n"
        "| # | Claim | Evidence | Command | Value / hash | Status |\n"
        "|---|-------|----------|---------|--------------|--------|\n"
        "| 1 | something | none | none | none | **VERIFIED** |\n",
        encoding="utf-8",
    )
    r = subprocess.run(
        [
            sys.executable,
            str(ROOT / "tools" / "validate_claim_audit.py"),
            "--input",
            str(bad),
            "--output",
            str(tmp_path / "r.json"),
        ],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )
    assert r.returncode == 1
    assert "VERIFIED without a command" in r.stdout


def test_claim_audit_validator_rejects_soft_state(tmp_path):
    bad = tmp_path / "CLAIM_AUDIT.md"
    bad.write_text(
        "## status coupling\n\n| # | Claim | Evidence | Command | Value / hash | Status |\n"
        "|---|---|---|---|---|---|\n"
        "| 1 | x | e | `cmd` | v | **LIKELY** |\n",
        encoding="utf-8",
    )
    r = subprocess.run(
        [
            sys.executable,
            str(ROOT / "tools" / "validate_claim_audit.py"),
            "--input",
            str(bad),
            "--output",
            str(tmp_path / "r.json"),
        ],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )
    assert r.returncode == 1


def test_real_claim_audit_passes():
    r = subprocess.run(
        [sys.executable, str(ROOT / "tools" / "validate_claim_audit.py")],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )
    assert r.returncode == 0, r.stdout + r.stderr


@pytest.mark.slow
def test_honesty_gate_passes():
    r = subprocess.run(
        [sys.executable, str(ROOT / "tools" / "verify_honesty.py")],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )
    assert r.returncode == 0, r.stdout + r.stderr
    out = json.loads((ROOT / "artifacts" / "honesty" / "HONESTY_GATE.json").read_text())
    assert out["all_ok"] is True
    assert len(out["checks"]) >= 6
