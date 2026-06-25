# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (c) 2026 Yaroslav Vasylenko / neuron7xLab
"""Meta-validation: the verdict SCHEMA must reject known-bad PASS verdicts.

A verdict schema that green-lights a self-contradictory PASS (survivors present,
mutation < 1.0, power FAIL, missing required key) is broken. Each case below is a
deliberately invalid verdict; ``iter_errors`` must be non-empty. The control proves
the validator still accepts a fully-correct PASS, so rejection is not vacuous.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path
from typing import Any

import jsonschema

_SK_PATH = Path(__file__).resolve().parent / "_skeleton.py"
_spec = importlib.util.spec_from_file_location("_meta_skeleton", _SK_PATH)
assert _spec is not None and _spec.loader is not None
_sk = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_sk)


def _errors(bad: dict[str, Any]) -> list[jsonschema.ValidationError]:
    schema = _sk.load_schema()
    return list(jsonschema.Draft202012Validator(schema).iter_errors(bad))


def test_control_valid_pass_skeleton_validates_clean() -> None:
    """Control: a fully-correct PASS verdict must validate with zero errors."""
    assert _errors(_sk.valid_pass_skeleton()) == []


def test_pass_with_nonempty_blocking_failures_rejected() -> None:
    """PASS + non-empty blocking_failures violates the allOf maxItems:0 rule."""
    bad = _sk.valid_pass_skeleton()
    bad["blocking_failures"] = ["gate 06-mutation-kill FAIL"]
    assert _errors(bad), "schema accepted PASS with blocking_failures present"


def test_pass_with_partial_mutation_score_rejected() -> None:
    """mutation_score 0.97 with verdict PASS must fail (allOf const 1.0)."""
    bad = _sk.valid_pass_skeleton()
    bad["mutation_score"] = 0.97
    bad["mutation_report"]["mutation_score"] = 0.97
    assert _errors(bad), "schema accepted PASS with mutation_score < 1.0"


def test_pass_with_failed_statistical_power_rejected() -> None:
    """statistical_power FAIL with verdict PASS must fail (allOf const PASS)."""
    bad = _sk.valid_pass_skeleton()
    bad["statistical_power"] = "FAIL"
    assert _errors(bad), "schema accepted PASS with statistical_power FAIL"


def test_pass_with_failed_claim_integrity_rejected() -> None:
    """claim_integrity FAIL with verdict PASS must fail (allOf const PASS)."""
    bad = _sk.valid_pass_skeleton()
    bad["claim_integrity"] = "FAIL"
    assert _errors(bad), "schema accepted PASS with claim_integrity FAIL"


def test_pass_with_evidence_incomplete_rejected() -> None:
    """evidence_complete false with verdict PASS must fail (allOf const true)."""
    bad = _sk.valid_pass_skeleton()
    bad["evidence_complete"] = False
    assert _errors(bad), "schema accepted PASS with evidence_complete false"


def test_missing_required_key_rejected() -> None:
    """Dropping a required key (head_sha) must fail the schema's required check."""
    bad = _sk.valid_pass_skeleton()
    del bad["head_sha"]
    errors = _errors(bad)
    assert errors, "schema accepted a verdict missing the required head_sha key"
    assert any("head_sha" in e.message for e in errors)
