# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (c) 2026 Yaroslav Vasylenko / neuron7xLab
"""Claim-safety gate: forbidden + state-contingent claims are enforced."""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def _vfc():
    spec = importlib.util.spec_from_file_location(
        "vfc", ROOT / "tools" / "validate_forbidden_claims.py"
    )
    mod = importlib.util.module_from_spec(spec)
    sys.modules["vfc"] = mod
    spec.loader.exec_module(mod)
    return mod


def test_repo_passes_claim_safety(tmp_path):
    assert _vfc().main(["--output", str(tmp_path / "r.json")]) == 0


def test_forbidden_patterns_present():
    v = _vfc()
    blob = " ".join(p for p, _ in v.FOREVER_FORBIDDEN)
    for needle in ("clinical", "medical", "seizure", "regulatory", "authority", "brain"):
        assert needle in blob.lower()


def test_bnci_validated_blocked_without_pass():
    import json

    truth = json.loads((ROOT / "artifacts" / "release" / "CURRENT_TRUTH.json").read_text())
    # canonical state must NOT be BNCI passed (so 'BNCI validated' is forbidden)
    assert truth["bnci_execution_state"] != "BNCI_CONFIRMATORY_PASSED"
    assert truth["multi_dataset_replication_state"] == "NOT_DONE"
