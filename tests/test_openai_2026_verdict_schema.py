# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (c) 2026 Yaroslav Vasylenko / neuron7xLab
"""Contract tests for schemas/openai_2026_verdict.schema.json (v2).

The schema is the fail-closed evidence contract: PASS is forbidden if any required
key is absent or any machine-derived sub-verdict is not green. These tests pin that
contract so a future loosening is caught.
"""

from __future__ import annotations

import json
from pathlib import Path

import jsonschema
import pytest

ROOT = Path(__file__).resolve().parents[1]
SCHEMA_PATH = ROOT / "schemas" / "openai_2026_verdict.schema.json"

_REQUIRED_KEYS = {
    "workflow_name",
    "project",
    "verdict",
    "grid_version",
    "head_sha",
    "run_context",
    "python_version",
    "dependency_lock_hashes",
    "gate_results",
    "artifact_digests",
    "dataset_manifest",
    "seed_manifest",
    "mutation_report",
    "power_profile",
    "red_team_summary",
    "claim_audit",
    "blocking_failures",
    "evidence_complete",
    "network_denied",
    "replayable",
    "mutation_score",
    "statistical_power",
    "artifact_digests_present",
    "claim_integrity",
}


@pytest.fixture(scope="module")
def schema() -> dict:
    return json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def validator(schema: dict) -> jsonschema.Draft202012Validator:
    jsonschema.Draft202012Validator.check_schema(schema)
    return jsonschema.Draft202012Validator(schema)


def _pass_skeleton() -> dict:
    """A minimal fully-green verdict that MUST validate."""
    digest = "a" * 64
    return {
        "workflow_name": "OpenAI-2026 Validation Grid",
        "project": "bsff",
        "verdict": "PASS",
        "grid_version": "2026.1",
        "head_sha": "0123abc",
        "run_context": "ci",
        "python_version": "3.12.3",
        "dependency_lock_hashes": {"ci.lock": digest},
        "gate_results": {"01-lock-integrity": "PASS"},
        "artifact_digests": {"mutation_kill_report": digest},
        "dataset_manifest": {"datasets": []},
        "seed_manifest": {"seeds": [2026, 7, 1337]},
        "mutation_report": {
            "mutation_score": 1.0,
            "mutants_total": 8,
            "survivors": [],
            "verdict": "PASS",
        },
        "power_profile": {"verdict": "PASS"},
        "red_team_summary": {"verdict": "PASS", "categories_total": 14, "categories_killed": 14},
        "claim_audit": {"verdict": "PASS", "forbidden_violations": []},
        "blocking_failures": [],
        "evidence_complete": True,
        "network_denied": True,
        "replayable": True,
        "mutation_score": 1.0,
        "statistical_power": "PASS",
        "artifact_digests_present": True,
        "claim_integrity": "PASS",
    }


def test_required_keys_are_frozen(schema: dict) -> None:
    assert set(schema["required"]) == _REQUIRED_KEYS


def test_pass_skeleton_validates(validator: jsonschema.Draft202012Validator) -> None:
    assert list(validator.iter_errors(_pass_skeleton())) == []


@pytest.mark.parametrize("missing", sorted(_REQUIRED_KEYS))
def test_missing_any_required_key_forbids_validation(
    validator: jsonschema.Draft202012Validator, missing: str
) -> None:
    bad = _pass_skeleton()
    del bad[missing]
    assert list(validator.iter_errors(bad)), f"removing {missing} should invalidate the verdict"


def test_pass_with_nonempty_blocking_failures_is_rejected(
    validator: jsonschema.Draft202012Validator,
) -> None:
    bad = _pass_skeleton()
    bad["blocking_failures"] = ["something failed"]
    assert list(validator.iter_errors(bad))


@pytest.mark.parametrize(
    "key,value",
    [
        ("mutation_score", 0.99),
        ("statistical_power", "FAIL"),
        ("claim_integrity", "FAIL"),
        ("evidence_complete", False),
        ("network_denied", False),
        ("replayable", False),
        ("artifact_digests_present", False),
    ],
)
def test_pass_requires_every_subverdict_green(
    validator: jsonschema.Draft202012Validator, key: str, value: object
) -> None:
    bad = _pass_skeleton()
    bad[key] = value
    assert list(validator.iter_errors(bad)), f"PASS with {key}={value!r} must be rejected"


def test_workflow_name_is_frozen(validator: jsonschema.Draft202012Validator) -> None:
    bad = _pass_skeleton()
    bad["workflow_name"] = "Some Other Grid"
    assert list(validator.iter_errors(bad))


@pytest.mark.parametrize(
    "mutate",
    [
        lambda v: v["gate_results"].update({"06-mutation-kill": "FAIL"}),
        lambda v: v["mutation_report"].update({"verdict": "FAIL"}),
        lambda v: v["red_team_summary"].update({"verdict": "FAIL"}),
        lambda v: v["power_profile"].update({"verdict": "FAIL"}),
        lambda v: v["claim_audit"].update({"verdict": "FAIL"}),
        lambda v: v["claim_audit"].update({"forbidden_violations": [{"id": "x"}]}),
    ],
)
def test_pass_forbids_nested_fail_summaries(
    validator: jsonschema.Draft202012Validator, mutate
) -> None:
    """Audit fix #6: a top-level PASS over a nested FAIL summary must be rejected."""
    bad = _pass_skeleton()
    bad.setdefault("gate_results", {"01-lock-integrity": "PASS"})
    mutate(bad)
    assert list(validator.iter_errors(bad)), "nested FAIL under a PASS verdict must be rejected"


def test_committed_verdict_matches_schema(validator: jsonschema.Draft202012Validator) -> None:
    """The committed verdict artifact must itself be schema-valid (it is committed)."""
    path = ROOT / "artifacts" / "final" / "openai_2026_validation_verdict.json"
    assert path.is_file(), "committed verdict artifact is missing"
    payload = json.loads(path.read_text(encoding="utf-8"))
    assert list(validator.iter_errors(payload)) == []
