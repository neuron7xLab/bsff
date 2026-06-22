# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (c) 2026 Yaroslav Vasylenko / neuron7xLab
"""The release dry-run workflow exists, is PR-triggered, and declares the gate job."""

from __future__ import annotations

from pathlib import Path

import pytest

yaml = pytest.importorskip("yaml")
ROOT = Path(__file__).resolve().parents[1]
WF = ROOT / ".github" / "workflows" / "release-dry-run.yml"


def test_workflow_exists_and_valid():
    assert WF.is_file()
    yaml.safe_load(WF.read_text(encoding="utf-8"))


def test_triggers_on_pull_request_and_names_the_gate_job():
    data = yaml.safe_load(WF.read_text(encoding="utf-8"))
    triggers = data.get(True) or data.get("on")  # PyYAML maps bare `on:` to True
    assert "pull_request" in triggers
    assert "release-gate-dry-run" in data["jobs"]


def test_governance_doc_requires_dry_run_not_tag_only_gate():
    doc = (ROOT / "docs" / "GOVERNANCE_REQUIRED_CHECKS.md").read_text(encoding="utf-8")
    assert "release-gate-dry-run" in doc
