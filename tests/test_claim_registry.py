# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (c) 2026 Yaroslav Vasylenko / neuron7xLab
"""R6/R7 claim-registry guardrails."""

from __future__ import annotations

import json
from pathlib import Path

from bsff.statistics.contracts import assert_valid_claim_registry

ROOT = Path(__file__).resolve().parents[1]


def _load_registry() -> dict:
    # claims.yaml is written as JSON-compatible YAML so the base test gate has no
    # PyYAML dependency. YAML tooling can still consume it as a valid YAML document.
    return json.loads((ROOT / "claims.yaml").read_text(encoding="utf-8"))


def test_claim_registry_is_shape_valid():
    registry = _load_registry()
    assert registry["schema_version"] == "2026.06"
    assert_valid_claim_registry(registry["claims"])


def test_claim_registry_has_rank_boundary_claim():
    claims = _load_registry()["claims"]
    boundary_claim = claims["BSFF-CLAIM-004"]
    assert "not yet R6/R7" in boundary_claim["statement"]
    assert boundary_claim["status"] == ["unverified"]
    assert "external reproduction" in boundary_claim["failure_condition"].lower()


def test_claims_document_references_all_registered_claims():
    claims_doc = (ROOT / "CLAIMS.md").read_text(encoding="utf-8")
    for claim_id in _load_registry()["claims"]:
        assert claim_id in claims_doc
