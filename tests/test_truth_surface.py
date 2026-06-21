# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (c) 2026 Yaroslav Vasylenko / neuron7xLab
"""Truth surface: the contract scans every public claim surface and catches overclaim."""

from __future__ import annotations

import importlib.util
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def _load(name):
    spec = importlib.util.spec_from_file_location(name, ROOT / "tools" / f"{name}.py")
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


def test_truth_contract_passes_on_repo():
    r = subprocess.run(
        [sys.executable, str(ROOT / "tools" / "validate_truth_contract.py")],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )
    assert r.returncode == 0, r.stdout + r.stderr


def test_truth_surface_doc_declares_surfaces():
    text = (ROOT / "docs" / "TRUTH_SURFACE.md").read_text()
    for surface in ("README", "STATUS", "pyproject", "release notes", "DECISION"):
        assert surface in text


def test_new_blocked_phrases_are_caught():
    m = _load("validate_truth_contract")
    for bad in (
        "proves EEG claims",
        "scientifically proven",
        "real EEG validated",
        "regulatory grade",
        "external validation complete",
    ):
        assert m.find_forbidden_claims(f"BSFF {bad} today"), bad


def test_release_notes_validator_catches_overclaim():
    m = _load("validate_truth_contract")
    assert m.find_forbidden_claims("This release is clinically validated")


def test_release_notes_tool_runs():
    r = subprocess.run(
        [sys.executable, str(ROOT / "tools" / "validate_release_notes.py")],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )
    assert r.returncode == 0, r.stdout + r.stderr
