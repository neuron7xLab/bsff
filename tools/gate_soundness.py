# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (c) 2026 Yaroslav Vasylenko / neuron7xLab
"""Meta-verification gate: prove that BSFF's gates are instruments, not labels.

The repo ships ~34 gate/validator tools under ``tools/`` (``validate_*.py``,
``check_*.py``, ``verify_*.py``). A gate is only an *instrument* if there exists
a **negative control**: a test that feeds it a known-bad input and asserts it
FAILS. A gate with only "passes on the real repo" tests is decorative -- it
could be replaced by ``print("PASS")`` and no test would notice.

This tool reads ``gate_soundness_registry.json`` (the curated map of gate tool
-> negative-control nodeid, plus a frozen ``unproven`` debt list), discovers the
live set of gate tools, and reports which gates are proven. As a CLI with
``--check`` it enforces a **ratchet**: the set of unproven gates may shrink but
never GROW beyond the committed frozen list. A newly added gate must ship a
negative control (registry entry whose test file exists) or be explicitly added
to the frozen ``unproven`` list -- otherwise ``--check`` fails closed (exit 1).

The honest ``unproven`` list is the finding: it is the map of decorative-risk
gates, not a bug to be hidden.
"""

from __future__ import annotations

import argparse
import ast
import json
import re
from pathlib import Path

SCHEMA = "bsff.gate_soundness/v1"

# Gate tools are the audited surface: validators, checkers, verifiers.
# Gate tools: the classic validate_/check_/verify_ family PLUS the
# meta-verification layer (its own gates must sit inside the soundness surface,
# not audit everyone else from outside it).
_GATE_NAME_RE = re.compile(r"^(validate_|check_|verify_).*\.py$|.*(_gate|_probe)\.py$")
_EXTRA_GATES = frozenset({"lint_fail_open.py", "claim_coverage.py", "quality_dashboard.py"})

# This meta-tool audits gates; it is not itself an audited gate.
_SELF = "gate_soundness.py"

_DEFAULT_ROOT = Path(__file__).resolve().parents[1]
_REGISTRY_RELPATH = "tools/gate_soundness_registry.json"


def discover_gates(root: Path) -> list[str]:
    """Return sorted repo-relative paths of every gate tool under ``tools/``."""
    tools_dir = root / "tools"
    if not tools_dir.is_dir():
        return []
    gates: list[str] = []
    for p in sorted(tools_dir.glob("*.py")):
        if p.name == _SELF:
            continue
        if _GATE_NAME_RE.match(p.name) or p.name in _EXTRA_GATES:
            gates.append(f"tools/{p.name}")
    return sorted(gates)


def load_registry(root: Path) -> dict:
    """Load the committed registry, or an empty one if it is absent.

    An empty registry (no ``gates``, no frozen ``unproven``) is the correct
    baseline for a synthetic tree: every discovered gate is then unproven and
    also unaccounted-for, so the ratchet fails closed.
    """
    reg_path = root / _REGISTRY_RELPATH
    if not reg_path.is_file():
        return {"gates": {}, "unproven": []}
    data = json.loads(reg_path.read_text(encoding="utf-8"))
    data.setdefault("gates", {})
    data.setdefault("unproven", [])
    return data


def _nodeid_function_defined(path: Path, func: str) -> bool:
    """True if ``func`` is defined as a top-level test function in ``path``.

    Uses AST so a decorative nodeid whose function does not actually exist (a
    renamed/deleted test) cannot count as a negative control. The leading
    segment before any ``[param]`` is matched, so parametrized tests resolve.
    """
    base = func.split("[", 1)[0]
    try:
        tree = ast.parse(path.read_text(encoding="utf-8"))
    except (OSError, SyntaxError):
        return False
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name == base:
            return True
    return False


def _is_proven(root: Path, entry: object) -> bool:
    """A gate is proven only if its negative-control nodeid resolves to a real,
    defined test function — not merely an existing file.

    Defeats two decorative-entry failure modes: a nodeid pointing at a deleted
    file, AND a nodeid naming a function that does not exist in an existing file.
    """
    if not isinstance(entry, dict):
        return False
    nodeid = entry.get("negative_control_test")
    if not isinstance(nodeid, str) or "::" not in nodeid:
        return False
    test_file, _, func = nodeid.partition("::")
    path = root / test_file
    if not path.is_file() or not func.strip():
        return False
    return _nodeid_function_defined(path, func.strip())


def evaluate(root: Path | str) -> dict:
    """Audit the gate surface of ``root`` against its registry.

    Returns a deterministic dict with the schema, gate counts, the current
    ``unproven`` list, the ``new_unproven`` gates that have appeared beyond the
    frozen debt list, and an overall ratchet ``status``.
    """
    root = Path(root)
    registry = load_registry(root)
    gates = discover_gates(root)
    reg_gates = registry.get("gates", {})
    frozen_unproven = set(registry.get("unproven", []))

    unproven: list[str] = []
    proven_count = 0
    for gate in gates:
        if gate in reg_gates and _is_proven(root, reg_gates[gate]):
            proven_count += 1
        else:
            unproven.append(gate)

    unproven = sorted(unproven)
    # Ratchet: any unproven gate not grandfathered into the frozen list is new.
    new_unproven = sorted(set(unproven) - frozen_unproven)
    status = "PASS" if not new_unproven else "FAIL"

    return {
        "schema": SCHEMA,
        "total_gates": len(gates),
        "proven": proven_count,
        "unproven": unproven,
        "new_unproven": new_unproven,
        "status": status,
    }


def _print_summary(result: dict, root: Path) -> None:
    print(f"gate_soundness [{result['schema']}] root={root}")
    print(
        f"  gates: {result['total_gates']}  "
        f"proven: {result['proven']}  "
        f"unproven: {len(result['unproven'])}"
    )
    if result["unproven"]:
        print("  unproven (frozen debt -- no negative control found):")
        for gate in result["unproven"]:
            print(f"    - {gate}")
    if result["new_unproven"]:
        print("  NEW unproven (ratchet violation -- ship a negative control):")
        for gate in result["new_unproven"]:
            print(f"    ! {gate}")
    print(f"  status: {result['status']}")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--root",
        type=Path,
        default=_DEFAULT_ROOT,
        help="Repository root to audit (default: this repo).",
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help="Fail (exit 1) if any gate is unproven beyond the frozen list.",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Emit the deterministic result as JSON instead of a summary.",
    )
    args = parser.parse_args(argv)

    result = evaluate(args.root)

    if args.json:
        print(json.dumps(result, sort_keys=True, indent=2))
    else:
        _print_summary(result, args.root.resolve())

    if args.check and result["status"] != "PASS":
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
