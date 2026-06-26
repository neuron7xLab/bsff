# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (c) 2026 Yaroslav Vasylenko / neuron7xLab
"""Autonomous suite-integrity calibrator: the tests and gates police themselves.

A green badge is worthless if the gates behind it are degenerate. This meta-gate
falsifies its own test/CI surface, deterministically and offline:

* no vacuous test (every ``test_*`` makes an assertion, directly or via a helper /
  raises-on-failure call);
* no swallowed CI failure (no ``continue-on-error: true``, no ``|| true`` etc.);
* no ``skip``/``xfail`` smuggled onto a core test;
* the test-count instrument is adaptive (matches an independent measurement), so the
  earlier degenerate "first-match" regress cannot return;
* the critical verdict/engine/API surface is actually referenced by tests.
"""

from __future__ import annotations

import ast
import importlib.util
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TESTS = ROOT / "tests"
WORKFLOWS = ROOT / ".github" / "workflows"

# Substrings of call names that raise on failure and therefore ARE assertions
# (covers np.testing.assert_*, Draft*Validator.check_schema, *.validate, etc.).
_ASSERTION_SUBSTRINGS = ("assert", "validate", "check", "verify", "raises", "warns")


def _test_files() -> list[Path]:
    return sorted(p for p in TESTS.rglob("test_*.py"))


def _funcs_with_assert(tree: ast.Module) -> set[str]:
    out: set[str] = set()
    for node in tree.body:
        if isinstance(node, ast.FunctionDef) and any(
            isinstance(n, ast.Assert) for n in ast.walk(node)
        ):
            out.add(node.name)
    return out


def _call_names(node: ast.AST) -> set[str]:
    names: set[str] = set()
    for n in ast.walk(node):
        if isinstance(n, ast.Call):
            f = n.func
            if isinstance(f, ast.Attribute):
                names.add(f.attr)
            elif isinstance(f, ast.Name):
                names.add(f.id)
    return names


def _is_non_vacuous(fn: ast.FunctionDef, helpers_with_assert: set[str]) -> bool:
    # An `assert` statement or an explicit `raise` (e.g. `raise AssertionError(...)`).
    for n in ast.walk(fn):
        if isinstance(n, (ast.Assert, ast.Raise)):
            return True
    calls = _call_names(fn)
    # A call whose name carries a raises-on-failure substring is an assertion.
    if any(sub in name.lower() for name in calls for sub in _ASSERTION_SUBSTRINGS):
        return True
    # Or it delegates to a same-file helper that itself asserts.
    return bool(calls & helpers_with_assert)


def test_no_vacuous_tests():
    offenders: list[str] = []
    for path in _test_files():
        tree = ast.parse(path.read_text(encoding="utf-8"))
        helpers = _funcs_with_assert(tree)
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef) and node.name.startswith("test_"):
                if not _is_non_vacuous(node, helpers):
                    offenders.append(f"{path.name}::{node.name}")
    assert not offenders, f"vacuous tests (no assertion): {offenders}"


def test_no_swallowed_failures_in_ci():
    offenders: list[str] = []
    for wf in sorted(WORKFLOWS.glob("*.yml")):
        text = wf.read_text(encoding="utf-8")
        if re.search(r"continue-on-error:\s*true", text):
            offenders.append(f"{wf.name}: continue-on-error: true")
        for m in re.finditer(r"\|\|\s*(true|:|exit\s+0)\b", text):
            offenders.append(f"{wf.name}: swallow `{m.group(0)}`")
    assert not offenders, f"degenerate CI gates that swallow failure: {offenders}"


def test_no_skip_or_xfail_on_core_tests():
    offenders: list[str] = []
    for path in _test_files():
        text = path.read_text(encoding="utf-8")
        for pat in (
            r"mark\.skip\b",
            r"mark\.xfail\b",
            r"pytest\.skip\(",
            r"pytest\.xfail\(",  # inline xfail hides a real failure just like the decorator form
            r"@unittest\.skip",
        ):
            if re.search(pat, text):
                offenders.append(f"{path.name}: {pat}")
    assert not offenders, f"skip/xfail smuggled onto core tests: {offenders}"


def test_count_instrument_is_adaptive():
    spec = importlib.util.spec_from_file_location(
        "update_status", ROOT / "tools" / "update_status.py"
    )
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = mod
    spec.loader.exec_module(mod)
    reported = mod.collect_test_count()
    # Independent measurement: parse the collect-only summary ourselves.
    out = subprocess.run(
        [sys.executable, "-m", "pytest", "tests/", "--collect-only", "-p", "no:cacheprovider"],
        cwd=ROOT,
        capture_output=True,
        text=True,
    ).stdout
    truth = int(re.findall(r"(\d+)\s+tests?\s+collected\s+in\b", out)[-1])
    assert reported == truth, f"count instrument is non-adaptive: reports {reported}, real {truth}"
    assert reported > 100, "count instrument returned an implausibly small frozen value"


def test_critical_surface_is_referenced_by_tests():
    corpus = "\n".join(p.read_text(encoding="utf-8") for p in _test_files())
    required = [
        "evaluate_claim_pipeline",
        "rank_order_surrogate_test",
        "miaaft_surrogate",
        "check_stationarity",
        "validate_verdict_json",
        "generate_evidence_manifest",
    ]
    missing = [name for name in required if name not in corpus]
    assert not missing, f"critical surface not exercised by any test: {missing}"
