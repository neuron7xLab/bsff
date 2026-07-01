# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (c) 2026 Yaroslav Vasylenko / neuron7xLab
"""R6/R7 claim-registry guardrails."""

from __future__ import annotations

import json
import re
from pathlib import Path

from bsff.statistics.contracts import assert_valid_claim_registry

ROOT = Path(__file__).resolve().parents[1]

# Any token in a reproduction_command that names a script file: the file must
# exist so a reviewer running the mandated command never hits file-not-found.
# CLI commands (`bsff ...`) and `pip install` lines carry no such token and are
# guarded by the CLI-subcommand and packaging gates instead.
_SCRIPT_TOKEN = re.compile(r"[A-Za-z0-9_./-]+\.(?:py|sh)")


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


def test_every_reproduction_command_script_exists():
    """Each claim's executable falsification path must be runnable, not dead."""
    dead: list[str] = []
    for claim_id, claim in _load_registry()["claims"].items():
        command = claim.get("reproduction_command", "")
        for token in _SCRIPT_TOKEN.findall(command):
            if not (ROOT / token).is_file():
                dead.append(f"{claim_id}: reproduction_command references missing {token!r}")
    assert not dead, "dead reproduction path(s): " + "; ".join(dead)
