# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (c) 2026 Yaroslav Vasylenko / neuron7xLab
"""The exported JSON Schemas must validate real contracts and reject malformed ones."""

from __future__ import annotations

import pytest
from jsonschema import Draft202012Validator
from jsonschema.exceptions import ValidationError

from bsff.json_schema import claim_spec_schema, verdict_json_schema
from bsff.schemas import ClaimSpec, VerdictJSON


def _spec() -> ClaimSpec:
    return ClaimSpec(
        claim_id="c",
        signal_type="EEG",
        task_type="classification",
        sampling_rate_hz=250.0,
        n_channels=8,
        n_samples=4096,
        statistic="lagged_quadratic",
    )


def test_schemas_are_valid_draft_2020_12():
    Draft202012Validator.check_schema(claim_spec_schema())
    Draft202012Validator.check_schema(verdict_json_schema())


def test_required_fields_match_dataclass_no_default_fields():
    required = claim_spec_schema()["required"]
    assert required == [
        "claim_id",
        "signal_type",
        "task_type",
        "sampling_rate_hz",
        "n_channels",
        "n_samples",
        "statistic",
    ]


def test_literal_becomes_enum():
    schema = claim_spec_schema()
    assert schema["properties"]["signal_type"]["enum"] == ["EEG", "ECoG", "sEEG", "spike", "LFP"]
    assert verdict_json_schema()["properties"]["verdict"]["enum"] == [
        "REFUTED",
        "UNSUPPORTED",
        "SURVIVED",
    ]


def test_optional_field_is_nullable():
    assert verdict_json_schema()["properties"]["p_value"]["type"] == ["number", "null"]


def test_real_claimspec_validates():
    Draft202012Validator(claim_spec_schema()).validate(_spec().to_dict())


def test_real_verdict_validates():
    verdict = VerdictJSON(
        claim_id="c",
        verdict="SURVIVED",
        p_value=0.01,
        original_statistic=0.5,
        surrogate_min=0.0,
        surrogate_max=0.2,
        leakage_flags={},
        evidence={},
        caveats=["synthetic-only"],
    )
    Draft202012Validator(verdict_json_schema()).validate(verdict.to_dict())


def test_invalid_enum_value_is_rejected():
    bad = _spec().to_dict()
    bad["signal_type"] = "MEG"  # not in the SignalType literal
    with pytest.raises(ValidationError):
        Draft202012Validator(claim_spec_schema()).validate(bad)


def test_missing_required_field_is_rejected():
    bad = _spec().to_dict()
    del bad["claim_id"]
    errors = list(Draft202012Validator(claim_spec_schema()).iter_errors(bad))
    assert any("claim_id" in e.message for e in errors)


def test_additional_top_level_field_is_rejected():
    bad = _spec().to_dict()
    bad["smuggled"] = "extra"
    errors = list(Draft202012Validator(claim_spec_schema()).iter_errors(bad))
    assert errors  # additionalProperties: false
