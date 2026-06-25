# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (c) 2026 Yaroslav Vasylenko / neuron7xLab
"""Tests for the formal OpenAI-2026 eval contract.

The eval contract is the task -> grader -> threshold -> evidence backbone. These
tests pin that the schema is enforced, the committed contract grades green against
real evidence, every eval is fully specified, and the executable grader actually
discriminates pass from fail (it is not a rubber stamp).
"""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import jsonschema
import pytest
import yaml

ROOT = Path(__file__).resolve().parents[1]
CONTRACT = ROOT / "contracts" / "openai_2026_eval_contract.yaml"
SCHEMA = ROOT / "schemas" / "openai_2026_eval.schema.json"

_REQUIRED_EVAL_FIELDS = {
    "id",
    "risk_class",
    "task_definition",
    "test_inputs",
    "ground_truth_or_expected_behavior",
    "grader",
    "threshold",
    "failure_mode",
    "evidence_artifact",
    "result_analysis",
}


def _load_tool():
    spec = importlib.util.spec_from_file_location(
        "validate_openai_2026_eval_contract",
        ROOT / "tools" / "validate_openai_2026_eval_contract.py",
    )
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


@pytest.fixture(scope="module")
def contract() -> dict:
    return yaml.safe_load(CONTRACT.read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def schema() -> dict:
    return json.loads(SCHEMA.read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def tool():
    return _load_tool()


def test_schema_is_valid(schema: dict) -> None:
    jsonschema.Draft202012Validator.check_schema(schema)


def test_committed_contract_matches_schema(contract: dict, schema: dict) -> None:
    errors = list(jsonschema.Draft202012Validator(schema).iter_errors(contract))
    assert errors == [], [e.message for e in errors]


def test_every_eval_is_fully_specified(contract: dict) -> None:
    for ev in contract["evals"]:
        assert _REQUIRED_EVAL_FIELDS <= set(ev), f"{ev.get('id')} missing fields"
        assert ev["grader"]["artifact"], ev["id"]
        assert ev["evidence_artifact"], ev["id"]


def test_contract_grades_green_against_real_evidence(tool) -> None:
    report = tool.run()
    assert report["verdict"] == "PASS", report["failures"]
    assert report["evals_passed"] == report["evals_total"] > 0


def test_grader_discriminates(tool) -> None:
    # ge / le / eq / eq_field / is_true behave as real comparisons, not rubber stamps.
    assert tool._grade({"op": "ge", "metric": "x", "value": 1.0}, {"x": 1.0})[0] is True
    assert tool._grade({"op": "ge", "metric": "x", "value": 1.0}, {"x": 0.99})[0] is False
    assert tool._grade({"op": "le", "metric": "x", "value": 0.05}, {"x": 0.2})[0] is False
    assert tool._grade({"op": "eq", "metric": "v", "value": "PASS"}, {"v": "FAIL"})[0] is False
    assert tool._grade({"op": "is_true", "metric": "ok"}, {"ok": False})[0] is False
    assert (
        tool._grade({"op": "eq_field", "metric": "a", "field": "b"}, {"a": 3, "b": 4})[0] is False
    )
    assert tool._grade({"op": "eq_field", "metric": "a", "field": "b"}, {"a": 4, "b": 4})[0] is True


def test_missing_metric_fails_closed(tool) -> None:
    ok, detail = tool._grade({"op": "ge", "metric": "absent.path", "value": 1.0}, {"present": 1})
    assert ok is False
    assert "absent.path" in detail


def test_contract_missing_required_field_is_rejected(contract: dict, schema: dict) -> None:
    bad = json.loads(json.dumps(contract))  # deep copy
    del bad["evals"][0]["grader"]
    assert list(jsonschema.Draft202012Validator(schema).iter_errors(bad))
