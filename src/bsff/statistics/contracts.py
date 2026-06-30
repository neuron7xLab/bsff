# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (c) 2026 Yaroslav Vasylenko / neuron7xLab
"""Minimal R6/R7 scientific-validity contract helpers.

These helpers intentionally stay dependency-free. They validate the shape of the
claim and dataset registries without requiring PyYAML, pandas, sklearn, or any
external data package. The goal is a lightweight CI gate that makes scientific
overclaiming harder before heavier reproduction infrastructure is added.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any

CLAIM_STATUSES = frozenset(
    {"unverified", "internally_verified", "externally_reproduced", "peer_reviewed"}
)
DATASET_STATUSES = frozenset(
    {"available", "committed_evidence", "preregistered", "external_required"}
)

REQUIRED_CLAIM_FIELDS = (
    "statement",
    "scientific_scope",
    "excluded_scope",
    "forbidden_overclaims",
    "required_datasets",
    "required_null_models",
    "required_metrics",
    "uncertainty_method",
    "failure_condition",
    "reproduction_command",
    "evidence_artifacts",
    "reviewer_note",
    "status",
)

REQUIRED_DATASET_FIELDS = (
    "status",
    "source",
    "license",
    "access_date",
    "immutable_hash",
    "artifact_hash_reference",
    "inclusion_criteria",
    "exclusion_criteria",
    "preprocessing_steps",
    "subject_session_split",
    "leakage_audit",
    "expected_artifact_outputs",
    "reproducibility_command",
)

REQUIRED_METRIC_FIELDS = (
    "metric_id",
    "effect_measure",
    "null_model",
    "uncertainty_method",
    "failure_threshold",
    "interpretation_boundary",
)


class ContractError(ValueError):
    """Raised when a scientific-validity contract is malformed."""


def _is_non_empty_text(value: object) -> bool:
    return isinstance(value, str) and bool(value.strip())


def _is_non_empty_sequence(value: object) -> bool:
    return (
        isinstance(value, Sequence)
        and not isinstance(value, (str, bytes))
        and bool(value)
    )


def _validate_required_mapping_fields(
    record_id: str,
    record: Mapping[str, Any],
    required_fields: Sequence[str],
) -> list[str]:
    errors: list[str] = []
    for field in required_fields:
        if field not in record:
            errors.append(f"{record_id}: missing required field {field!r}")
            continue
        value = record[field]
        if value is None:
            errors.append(f"{record_id}: field {field!r} is null")
        elif isinstance(value, str) and not value.strip():
            errors.append(f"{record_id}: field {field!r} is empty")
        elif (
            isinstance(value, Sequence)
            and not isinstance(value, (str, bytes))
            and not value
        ):
            errors.append(f"{record_id}: field {field!r} is an empty sequence")
    return errors


def validate_claim_record(claim_id: str, record: Mapping[str, Any]) -> list[str]:
    """Return validation errors for one claim registry record."""

    errors = _validate_required_mapping_fields(claim_id, record, REQUIRED_CLAIM_FIELDS)

    list_fields = (
        "forbidden_overclaims",
        "required_datasets",
        "required_null_models",
        "required_metrics",
        "evidence_artifacts",
        "status",
    )
    for field in list_fields:
        if field in record and not _is_non_empty_sequence(record[field]):
            errors.append(f"{claim_id}: field {field!r} must be a non-empty list")

    statuses = record.get("status", [])
    if _is_non_empty_sequence(statuses):
        invalid = sorted(
            str(status) for status in statuses if status not in CLAIM_STATUSES
        )
        if invalid:
            errors.append(f"{claim_id}: invalid status value(s): {', '.join(invalid)}")

    command = record.get("reproduction_command")
    if command is not None and not _is_non_empty_text(command):
        errors.append(f"{claim_id}: reproduction_command must be a non-empty string")

    failure_condition = record.get("failure_condition")
    if failure_condition is not None and not _is_non_empty_text(failure_condition):
        errors.append(f"{claim_id}: failure_condition must be a non-empty string")

    return errors


def validate_dataset_record(dataset_id: str, record: Mapping[str, Any]) -> list[str]:
    """Return validation errors for one dataset provenance record."""

    errors = _validate_required_mapping_fields(
        dataset_id, record, REQUIRED_DATASET_FIELDS
    )

    status = record.get("status")
    if status is not None and status not in DATASET_STATUSES:
        errors.append(f"{dataset_id}: invalid dataset status {status!r}")

    if "preprocessing_steps" in record and not _is_non_empty_sequence(
        record["preprocessing_steps"]
    ):
        errors.append(f"{dataset_id}: preprocessing_steps must be a non-empty list")

    if "expected_artifact_outputs" in record:
        outputs = record["expected_artifact_outputs"]
        if not isinstance(outputs, Sequence) or isinstance(outputs, (str, bytes)):
            errors.append(f"{dataset_id}: expected_artifact_outputs must be a list")

    return errors


def validate_metric_contract(record: Mapping[str, Any]) -> list[str]:
    """Return validation errors for one statistical metric contract."""

    metric_id = str(record.get("metric_id", "<unknown_metric>"))
    errors = _validate_required_mapping_fields(
        metric_id, record, REQUIRED_METRIC_FIELDS
    )

    boundary = str(record.get("interpretation_boundary", "")).lower()
    forbidden_positive_language = (
        "proved",
        "confirmed",
        "diagnostic",
        "therapeutic",
    )
    if any(term in boundary for term in forbidden_positive_language):
        errors.append(
            f"{metric_id}: interpretation boundary uses forbidden positive language"
        )

    return errors


def assert_valid_claim_registry(registry: Mapping[str, Mapping[str, Any]]) -> None:
    """Raise ContractError if any claim record is malformed."""

    errors: list[str] = []
    for claim_id, record in registry.items():
        errors.extend(validate_claim_record(claim_id, record))
    if errors:
        raise ContractError("; ".join(errors))


def assert_valid_dataset_registry(registry: Mapping[str, Mapping[str, Any]]) -> None:
    """Raise ContractError if any dataset record is malformed."""

    errors: list[str] = []
    for dataset_id, record in registry.items():
        errors.extend(validate_dataset_record(dataset_id, record))
    if errors:
        raise ContractError("; ".join(errors))
