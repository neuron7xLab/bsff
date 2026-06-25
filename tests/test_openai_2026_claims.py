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


def _forbidden(gate):
    import yaml

    return yaml.safe_load((ROOT / "claims" / "openai_2026_forbidden_claims.yml").read_text())[
        "forbidden"
    ]


def _compiled(gate):
    return [(f["id"], gate._compile(f["pattern"]), "") for f in _forbidden(gate)]


@pytest.mark.parametrize(
    "text,must_catch",
    [
        ("BSFF is not certified by OpenAI.", False),  # adjacent disclaimer
        ("BSFF is NOT an official OpenAI benchmark.", False),  # adjacent disclaimer
        ("There is no doubt that BSFF is certified by OpenAI.", True),  # far-neg trick (#2)
        ("BSFF is certified  by  OpenAI.", True),  # double-space (#4)
        ("Without question, BSFF is openai-approved.", True),  # far-neg trick
    ],
)
def test_negation_adjacency_and_whitespace(gate, text: str, must_catch: bool) -> None:
    """Audit fixes #2/#4: negation only exempts when ADJACENT; whitespace can't evade."""
    hits = gate._scan_text(gate._normalize(text), "t", _compiled(gate))
    assert bool(hits) == must_catch, (text, hits)


def test_multiline_split_is_caught(gate, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Audit fix #3: a forbidden phrase wrapped across lines is caught by the collapsed pass."""
    surface = tmp_path / "WRAP.md"
    surface.write_text("BSFF is certified\nby OpenAI today.\n")
    monkeypatch.setattr(gate, "_iter_surfaces", lambda: [surface])
    import yaml

    fb = yaml.safe_load((ROOT / "claims" / "openai_2026_forbidden_claims.yml").read_text())
    assert gate._scan_forbidden(fb["forbidden"]), "wrapped forbidden phrase must be caught"


def test_scan_covers_rst_and_python_surfaces(gate) -> None:
    """Audit fix #1: coverage is not limited to *.md — .rst and src/*.py ship publicly."""
    surfaces = {str(p.relative_to(ROOT)) for p in gate._iter_surfaces()}
    suffixes = {Path(s).suffix for s in surfaces}
    assert ".py" in suffixes and ".md" in suffixes
    # The test corpus (which embeds forbidden fixtures) must NOT be scanned.
    assert not any(s.startswith("tests/") for s in surfaces)
    assert not any(s.startswith("claims/") for s in surfaces)


def test_evidence_pointer_to_unrelated_file_is_rejected(gate) -> None:
    """Audit fix #5: a resolvable-but-unrelated evidence pointer must fail."""
    doc = {
        "require_evidence_pointer": True,
        "allowed": [
            {
                "id": "x",
                "evidence": "LICENSE",
                "evidence_must_contain": "OpenAI-2026 Validation Grid",
            }
        ],
    }
    gaps = gate._check_evidence_pointers(doc)
    assert gaps and gaps[0]["id"] == "x"


def test_allowed_claims_have_resolvable_evidence(gate) -> None:
    import yaml

    allowed = yaml.safe_load((ROOT / "claims" / "openai_2026_allowed_claims.yml").read_text())
    assert gate._check_evidence_pointers(allowed) == []
