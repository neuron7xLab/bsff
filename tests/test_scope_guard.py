# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (c) 2026 Yaroslav Vasylenko / neuron7xLab
"""Tests for the unsupported-scope quarantine (P1.3).

The single invariant under test: no out-of-scope claim can ever return
SURVIVED. Every out-of-scope category is checked for (a) correct routing to
UNSUPPORTED/QUARANTINED, and (b) downgrade of a proposed SURVIVED. One
legitimate in-scope EEG nonlinear-structure claim must stay IN_SCOPE.
"""

from __future__ import annotations

import pytest

from bsff.schemas import ClaimSpec
from bsff.scope_guard import (
    OutOfScopeCategory,
    ScopeError,
    ScopeVerdict,
    classify_scope,
    enforce_scope,
    guard_verdict,
)

# Each case: (label, claim metadata dict, expected category, expected disposition).
OUT_OF_SCOPE_CASES: list[tuple[str, dict[str, object], OutOfScopeCategory, str]] = [
    (
        "clinical",
        {"text": "This headset diagnoses depression from the EEG.", "is_time_series": True},
        OutOfScopeCategory.CLINICAL,
        "QUARANTINED",
    ),
    (
        "regulatory",
        {"text": "Our device is FDA-approved and GDPR-compliant.", "is_time_series": True},
        OutOfScopeCategory.REGULATORY,
        "QUARANTINED",
    ),
    (
        "emotion_without_signal",
        {
            "text": "The app reads your emotions and detects sadness.",
            "has_signal": False,
            "is_time_series": True,
        },
        OutOfScopeCategory.EMOTION_WITHOUT_SIGNAL,
        "UNSUPPORTED",
    ),
    (
        "non_time_series",
        {"text": "Survey scores correlate across subjects.", "is_time_series": False},
        OutOfScopeCategory.NON_TIME_SERIES,
        "UNSUPPORTED",
    ),
    (
        "causal_without_route",
        {
            "text": "Alpha power causes improved memory.",
            "has_signal": True,
            "has_causal_route": False,
            "is_time_series": True,
        },
        OutOfScopeCategory.CAUSAL_WITHOUT_ROUTE,
        "UNSUPPORTED",
    ),
    (
        "logical_without_data",
        {
            "text": "By definition the theorem holds: 2 + 2 equals 4.",
            "has_signal": False,
            "is_time_series": True,
        },
        OutOfScopeCategory.LOGICAL_WITHOUT_DATA,
        "UNSUPPORTED",
    ),
]


@pytest.mark.parametrize("label,meta,category,disposition", OUT_OF_SCOPE_CASES)
def test_out_of_scope_routes_to_quarantine(
    label: str,
    meta: dict[str, object],
    category: OutOfScopeCategory,
    disposition: str,
) -> None:
    verdict = classify_scope(meta)
    assert verdict.in_scope is False, label
    assert verdict.disposition in {"UNSUPPORTED", "QUARANTINED"}, label
    assert verdict.disposition == disposition, label
    assert verdict.category == category.value, label
    assert verdict.caveat, label


@pytest.mark.parametrize("label,meta,category,disposition", OUT_OF_SCOPE_CASES)
def test_guard_verdict_downgrades_survived(
    label: str,
    meta: dict[str, object],
    category: OutOfScopeCategory,
    disposition: str,
) -> None:
    verdict = classify_scope(meta)
    guarded = guard_verdict(verdict, "SURVIVED")
    assert guarded != "SURVIVED", label
    assert guarded == disposition, label


@pytest.mark.parametrize("label,meta,category,disposition", OUT_OF_SCOPE_CASES)
def test_enforce_scope_raises_out_of_scope(
    label: str,
    meta: dict[str, object],
    category: OutOfScopeCategory,
    disposition: str,
) -> None:
    with pytest.raises(ScopeError) as exc:
        enforce_scope(meta)
    assert exc.value.scope_verdict.category == category.value, label


def test_property_no_out_of_scope_returns_survived() -> None:
    """For every out-of-scope category, SURVIVED is never returned."""
    for label, meta, _category, _disposition in OUT_OF_SCOPE_CASES:
        verdict = classify_scope(meta)
        for proposed in ("SURVIVED", "REFUTED", "UNSUPPORTED"):
            guarded = guard_verdict(verdict, proposed)
            if proposed == "SURVIVED":
                assert guarded != "SURVIVED", (label, proposed)


def _in_scope_eeg_spec() -> ClaimSpec:
    return ClaimSpec(
        claim_id="eeg-nonlinear-001",
        signal_type="EEG",
        task_type="nonlinear_structure",
        sampling_rate_hz=256.0,
        n_channels=8,
        n_samples=2048,
        statistic="time_reversibility",
        metadata={"text": "EEG exhibits nonlinear deterministic structure beyond a linear null."},
    )


def test_legitimate_eeg_claim_stays_in_scope() -> None:
    verdict = classify_scope(_in_scope_eeg_spec())
    assert verdict.in_scope is True
    assert verdict.disposition == "IN_SCOPE"
    assert verdict.category is None


def test_in_scope_verdict_passes_through_unchanged() -> None:
    verdict = classify_scope(_in_scope_eeg_spec())
    assert guard_verdict(verdict, "SURVIVED") == "SURVIVED"
    assert guard_verdict(verdict, "REFUTED") == "REFUTED"
    assert guard_verdict(verdict, "UNSUPPORTED") == "UNSUPPORTED"


def test_in_scope_enforce_does_not_raise() -> None:
    assert enforce_scope(_in_scope_eeg_spec()) is None


def test_claimspec_emotion_metadata_override_quarantines() -> None:
    """A ClaimSpec can be flagged out-of-scope via metadata override."""
    spec = ClaimSpec(
        claim_id="emo-001",
        signal_type="EEG",
        task_type="classification",
        sampling_rate_hz=128.0,
        n_channels=4,
        n_samples=1024,
        statistic="auc",
        metadata={"text": "Detects your mood.", "has_signal": False},
    )
    verdict = classify_scope(spec)
    assert verdict.in_scope is False
    assert verdict.category == OutOfScopeCategory.EMOTION_WITHOUT_SIGNAL.value
    assert guard_verdict(verdict, "SURVIVED") == "UNSUPPORTED"


def test_emotion_with_signal_basis_is_in_scope() -> None:
    """An emotion claim WITH a declared signal basis is not category-rejected."""
    verdict = classify_scope(
        {
            "text": "Affective valence decoded from EEG nonlinear structure.",
            "has_signal": True,
            "is_time_series": True,
        }
    )
    assert verdict.in_scope is True


def test_scope_verdict_to_dict_roundtrip() -> None:
    verdict: ScopeVerdict = classify_scope(OUT_OF_SCOPE_CASES[0][1])
    payload = verdict.to_dict()
    assert payload["in_scope"] is False
    assert payload["disposition"] == "QUARANTINED"
    assert payload["category"] == OutOfScopeCategory.CLINICAL.value
    assert isinstance(payload["caveat"], str)
