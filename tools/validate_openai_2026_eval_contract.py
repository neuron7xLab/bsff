#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (c) 2026 Yaroslav Vasylenko / neuron7xLab
"""Formal eval-contract gate for the OpenAI-2026 Validation Grid.

Validates contracts/openai_2026_eval_contract.yaml against
schemas/openai_2026_eval.schema.json, then EXECUTES each eval's grader against its
real evidence artifact: a metric is read from the named JSON artifact (dotted path)
and compared to a threshold. An eval PASSes only if the evidence artifact resolves
AND the grader is satisfied. This turns "tests passed" into
task -> grader -> threshold -> evidence -> result, the formal backbone an
OpenAI-grade research-validation TARGET requires (NOT an external OpenAI
certification). Emits artifacts/eval/eval_contract_report.json.

    python tools/validate_openai_2026_eval_contract.py [--json] [--check]

Exit 0 iff every eval PASSes; nonzero otherwise. No network.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
CONTRACT = ROOT / "contracts" / "openai_2026_eval_contract.yaml"
SCHEMA = ROOT / "schemas" / "openai_2026_eval.schema.json"
REPORT = ROOT / "artifacts" / "eval" / "eval_contract_report.json"


def _load_yaml(path: Path) -> dict:
    import yaml

    return yaml.safe_load(path.read_text(encoding="utf-8")) or {}


def _read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _dotted(obj: Any, path: str) -> Any:
    cur = obj
    for part in path.split("."):
        if not isinstance(cur, dict) or part not in cur:
            raise KeyError(f"metric path '{path}' missing at '{part}'")
        cur = cur[part]
    return cur


def _grade(grader: dict, artifact_obj: Any) -> tuple[bool, str]:
    """Run one grader against a loaded artifact; return (passed, detail)."""
    op = grader["op"]
    metric = grader["metric"]
    try:
        actual = _dotted(artifact_obj, metric)
    except KeyError as exc:
        return False, str(exc)

    if op == "ge":
        ok = isinstance(actual, (int, float)) and float(actual) >= float(grader["value"])
        return ok, f"{metric}={actual} >= {grader['value']}? {ok}"
    if op == "le":
        ok = isinstance(actual, (int, float)) and float(actual) <= float(grader["value"])
        return ok, f"{metric}={actual} <= {grader['value']}? {ok}"
    if op == "eq":
        ok = actual == grader["value"]
        return ok, f"{metric}={actual!r} == {grader['value']!r}? {ok}"
    if op == "is_true":
        ok = actual is True
        return ok, f"{metric}={actual!r} is true? {ok}"
    if op == "len_ge":
        ok = hasattr(actual, "__len__") and len(actual) >= int(grader["value"])
        return (
            ok,
            f"len({metric})={getattr(actual, '__len__', lambda: '?')() if hasattr(actual, '__len__') else '?'} >= {grader['value']}? {ok}",
        )
    if op == "eq_field":
        try:
            other = _dotted(artifact_obj, grader["field"])
        except KeyError as exc:
            return False, str(exc)
        ok = actual == other
        return ok, f"{metric}={actual!r} == {grader['field']}={other!r}? {ok}"
    return False, f"unknown op {op!r}"


def _schema_errors(contract: dict) -> list[str]:
    schema = _read_json(SCHEMA)
    try:
        import jsonschema
    except ImportError:
        req = schema.get("required", [])
        return [f"missing required key: {k}" for k in req if k not in contract]
    validator = jsonschema.Draft202012Validator(schema)
    return [f"schema: {e.message}" for e in validator.iter_errors(contract)]


def run() -> dict:
    contract = _load_yaml(CONTRACT)
    failures: list[str] = []
    schema_errs = _schema_errors(contract)
    failures += schema_errs

    results: list[dict] = []
    for ev in contract.get("evals", []):
        eid = ev.get("id", "?")
        artifact_path = ROOT / ev["grader"]["artifact"]
        evidence_path = ROOT / ev["evidence_artifact"]
        if not evidence_path.exists():
            results.append(
                {
                    "id": eid,
                    "verdict": "FAIL",
                    "detail": f"evidence missing: {ev['evidence_artifact']}",
                }
            )
            failures.append(f"{eid}: evidence missing")
            continue
        try:
            artifact_obj = _read_json(artifact_path)
        except (OSError, json.JSONDecodeError) as exc:
            results.append({"id": eid, "verdict": "FAIL", "detail": f"artifact unreadable: {exc}"})
            failures.append(f"{eid}: artifact unreadable")
            continue
        passed, detail = _grade(ev["grader"], artifact_obj)
        results.append(
            {
                "id": eid,
                "risk_class": ev.get("risk_class"),
                "verdict": "PASS" if passed else "FAIL",
                "threshold": ev.get("threshold"),
                "failure_mode": ev.get("failure_mode"),
                "evidence_artifact": ev["evidence_artifact"],
                "detail": detail,
            }
        )
        if not passed:
            failures.append(f"{eid}: grader failed ({detail})")

    total = len(results)
    passed_n = sum(1 for r in results if r["verdict"] == "PASS")
    return {
        "gate": "openai-2026-eval-contract",
        "contract_id": contract.get("contract_id"),
        "verdict": "PASS" if not failures and total > 0 else "FAIL",
        "evals_total": total,
        "evals_passed": passed_n,
        "schema_errors": schema_errs,
        "results": results,
        "failures": failures,
    }


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--json", action="store_true", help="emit the report to stdout")
    ap.add_argument(
        "--check", action="store_true", help="also write artifacts/eval/eval_contract_report.json"
    )
    args = ap.parse_args(argv)
    report = run()
    REPORT.parent.mkdir(parents=True, exist_ok=True)
    REPORT.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    if args.json:
        print(json.dumps(report, indent=2, sort_keys=True))
    else:
        for r in report["results"]:
            print(f"[{r['verdict']}] {r['id']}: {r.get('detail', '')}")
        print(
            f"eval-contract: {report['verdict']} "
            f"({report['evals_passed']}/{report['evals_total']} evals)"
        )
        if report["failures"]:
            for f in report["failures"]:
                print(f"  FAIL: {f}", file=sys.stderr)
    return 0 if report["verdict"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
