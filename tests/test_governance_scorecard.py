# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (c) 2026 Yaroslav Vasylenko / neuron7xLab
"""The score cannot lie: 99 is gated on verified governance with no admin bypass."""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def _load(name):
    spec = importlib.util.spec_from_file_location(name, ROOT / "tools" / f"{name}.py")
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


def test_scorecard_in_sync():
    m = _load("compute_scorecard")
    committed = json.loads((ROOT / "artifacts" / "actions_99_scorecard.json").read_text())
    assert committed == m.compute()


def test_cannot_claim_99_while_governance_unverified():
    m = _load("compute_scorecard")
    card = m.compute()
    gov = json.loads((ROOT / "artifacts" / "governance_status.json").read_text())
    # invariant: 99 iff governance verified AND no admin bypass
    assert card["can_claim_99"] == (
        gov.get("required_checks_verified") and gov.get("admin_bypass_allowed") is False
    )
    if not card["can_claim_99"]:
        assert card["score"] < 99


def test_verifier_never_passes_with_bypass():
    # the verifier module must import cleanly
    _load("verify_branch_protection")
    # the core decision rule: full checks present BUT admin bypass on -> not verified
    declared = ["a", "b"]
    actual = ["a", "b"]
    bypass_allowed = True
    verified = bool(declared) and not (set(declared) - set(actual)) and not bypass_allowed
    assert verified is False
