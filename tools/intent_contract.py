#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (c) 2026 Yaroslav Vasylenko / neuron7xLab
"""Intent-contract gate — close the first edge: chaos -> definition.

The meta-verification layer proves *implementation matches specification*. It
does NOT prove that the specification matches the *intent* — that edge is a
fluent human->spec translation, unverified. This gate mechanizes meaning-closure
over that edge, per three invariants a ratified intent must satisfy:

  1. FALSIFIABLE   — the intent names a verification (gate + negative-control
                     nodeid) that provably FAILS on the negation of the intent;
                     the nodeid must resolve to a real, top-level (pytest-
                     collectable) AST-defined test function -- a def nested
                     inside another function is uncollectable and rejected.
  2. RATIFIED      — the intent carries an explicit ``ratified_by`` (a human
                     oracle pre-committed to it), i.e. it is not self-asserted.
  3. BOUND         — the verification gate file actually exists on disk, AND the
                     negative-control test FILE statically references the gate
                     module it falsifies (import or string), so the control
                     cannot point at an unrelated ``assert True`` test. This
                     linkage is necessary-not-sufficient: full behavioral proof
                     (the control actually FAILS the gate) is delegated to the
                     ``test-py*`` CI run that executes the suite.

An intent that is unratified, or whose verification does not resolve or does not
link to its gate, FAILs closed. This transfers the trust point from the tool's
fluency to the operator's ratification: everything after ratification is
mechanized.
"""

from __future__ import annotations

import argparse
import ast
import json
import sys
from pathlib import Path

SCHEMA = "bsff.intent_contract/v1"
ROOT = Path(__file__).resolve().parents[1]
REGISTRY_RELPATH = "intents/registry.json"


def _load_registry(root: Path) -> dict:
    path = root / REGISTRY_RELPATH
    if not path.is_file():
        return {"intents": {}}
    data = json.loads(path.read_text(encoding="utf-8"))
    data.setdefault("intents", {})
    return data


def _resolves_top_level(tree: ast.Module, func_spec: str) -> bool:
    """True iff ``func_spec`` names a test pytest can collect at the top level.

    ``func_spec`` is the nodeid segment after the file (``test_foo`` or
    ``TestBar::test_baz``). Only functions defined directly in the module body,
    and methods defined directly in the body of a top-level class, resolve. A
    def NESTED inside another function is uncollectable by pytest and MUST NOT
    resolve (previously ``ast.walk`` descended into inner defs and wrongly
    resolved them).
    """
    parts = [p for p in func_spec.split("::") if p]
    if len(parts) == 1:
        name = parts[0]
        return any(
            isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef)) and n.name == name
            for n in tree.body
        )
    if len(parts) == 2:
        cls_name, meth_name = parts
        for n in tree.body:
            if isinstance(n, ast.ClassDef) and n.name == cls_name:
                return any(
                    isinstance(m, (ast.FunctionDef, ast.AsyncFunctionDef)) and m.name == meth_name
                    for m in n.body
                )
    return False


def _nodeid_resolves(root: Path, nodeid: object) -> bool:
    """True iff ``file::func`` names a real file AND a top-level, pytest-
    collectable AST-defined function (a nested/inner def does NOT resolve)."""
    if not isinstance(nodeid, str) or "::" not in nodeid:
        return False
    rel, _, func = nodeid.partition("::")
    path = root / rel
    base = func.split("[", 1)[0].strip()
    if not path.is_file() or not base:
        return False
    try:
        tree = ast.parse(path.read_text(encoding="utf-8"))
    except (OSError, SyntaxError):
        return False
    return _resolves_top_level(tree, base)


def _test_references_gate(root: Path, nodeid: object, gate: object) -> bool:
    """True if the negative-control test FILE references the gate module.

    Static linkage: the test source must mention the gate module name (import or
    string) so the control cannot point at an unrelated ``assert True`` test.
    Necessary-not-sufficient; behavioral proof is delegated to the CI test run.
    """
    if not isinstance(nodeid, str) or "::" not in nodeid or not isinstance(gate, str):
        return False
    stem = Path(gate).stem
    rel = nodeid.partition("::")[0]
    path = root / rel
    if not stem or not path.is_file():
        return False
    try:
        return stem in path.read_text(encoding="utf-8")
    except OSError:
        return False


def _evaluate_intent(root: Path, intent_id: str, intent: object) -> list[str]:
    errors: list[str] = []
    if not isinstance(intent, dict):
        return [f"{intent_id}: intent is not an object"]
    if not str(intent.get("statement", "")).strip():
        errors.append(f"{intent_id}: missing falsifiable statement")
    # RATIFIED
    if not str(intent.get("ratified_by", "")).strip() or intent.get("status") != "ratified":
        errors.append(f"{intent_id}: not ratified (needs ratified_by + status=ratified)")
    # FALSIFIABLE + BOUND
    verification = intent.get("verification")
    if not isinstance(verification, dict):
        errors.append(f"{intent_id}: missing verification block")
        return errors
    gate = verification.get("gate")
    if not isinstance(gate, str) or not (root / gate).is_file():
        errors.append(f"{intent_id}: verification gate missing: {gate!r}")
    negative_control = verification.get("negative_control")
    if not _nodeid_resolves(root, negative_control):
        errors.append(
            f"{intent_id}: negative_control does not resolve to a defined test: "
            f"{negative_control!r}"
        )
    elif not _test_references_gate(root, negative_control, gate):
        errors.append(
            f"{intent_id}: negative_control test does not reference gate "
            f"{gate!r} (decorative link): {negative_control!r}"
        )
    return errors


def evaluate(root: Path | str = ROOT) -> dict:
    root = Path(root)
    registry = _load_registry(root)
    intents = registry.get("intents", {})
    violations: list[str] = []
    ratified = 0
    for intent_id in sorted(intents):
        errs = _evaluate_intent(root, intent_id, intents[intent_id])
        if errs:
            violations.extend(errs)
        else:
            ratified += 1
    if not intents:
        violations.append("no intent contracts registered")
    return {
        "schema": SCHEMA,
        "intents_total": len(intents),
        "ratified": ratified,
        "violations": violations,
        "status": "PASS" if not violations else "FAIL",
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="exit 1 if any intent is unclosed")
    parser.add_argument("--root", type=Path, default=ROOT)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)

    report = evaluate(args.root)
    if args.json:
        print(json.dumps(report, indent=2, sort_keys=True))
    else:
        print(f"INTENT_CONTRACT: {report['status']}")
        print(f"  ratified: {report['ratified']}/{report['intents_total']}")
        for v in report["violations"]:
            print(f"  - {v}")
    return 1 if args.check and report["status"] != "PASS" else 0


if __name__ == "__main__":
    sys.exit(main())
