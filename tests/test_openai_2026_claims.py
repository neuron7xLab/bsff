# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (c) 2026 Yaroslav Vasylenko / neuron7xLab
"""Tests for the OpenAI-2026 claim-integrity gate (tools/validate_openai_2026_claims.py).

The grid is an INTERNAL OpenAI-grade research-validation target, NOT an external
OpenAI certification. These tests pin that a forbidden relationship claim is caught,
a negated mention is allowed, and the live repository surfaces are clean.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]


def _load_gate():
    spec = importlib.util.spec_from_file_location(
        "validate_openai_2026_claims", ROOT / "tools" / "validate_openai_2026_claims.py"
    )
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


@pytest.fixture(scope="module")
def gate():
    return _load_gate()


def test_live_surfaces_are_claim_clean(gate) -> None:
    result = gate.run()
    assert result["verdict"] == "PASS", result["forbidden_violations"]
    assert result["forbidden_violations"] == []


def test_forbidden_pattern_is_detected(
    gate, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    surface = tmp_path / "BAD_DOC.md"
    surface.write_text("BSFF is certified by OpenAI and is an official OpenAI benchmark.\n")
    monkeypatch.setattr(gate, "_iter_surfaces", lambda: [surface])
    import yaml

    forbidden = yaml.safe_load((ROOT / "claims" / "openai_2026_forbidden_claims.yml").read_text())
    violations = gate._scan_forbidden(forbidden["forbidden"])
    ids = {v["id"] for v in violations}
    assert "certified-by-openai" in ids
    assert "official-openai-benchmark" in ids


def test_negated_mention_is_allowed(gate, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    surface = tmp_path / "OK_DOC.md"
    surface.write_text(
        "BSFF is NOT certified by OpenAI; this is not an official OpenAI benchmark.\n"
    )
    monkeypatch.setattr(gate, "_iter_surfaces", lambda: [surface])
    import yaml

    forbidden = yaml.safe_load((ROOT / "claims" / "openai_2026_forbidden_claims.yml").read_text())
    assert gate._scan_forbidden(forbidden["forbidden"]) == []


def test_allowed_claims_have_resolvable_evidence(gate) -> None:
    import yaml

    allowed = yaml.safe_load((ROOT / "claims" / "openai_2026_allowed_claims.yml").read_text())
    assert gate._check_evidence_pointers(allowed) == []
