# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (c) 2026 Yaroslav Vasylenko / neuron7xLab
"""Static analyzer: gate/validator tools MUST fail closed.

A recurring defect in this repository is *fail-open* code: an exception
handler, or an unconditional gate function, that reports success
(``return 0`` / ``return True`` / a ``PASS`` print) instead of surfacing
the failure. This module walks the AST of every ``tools/*.py`` file (and,
opt-in, ``src/bsff/**``) and flags two families of fail-open shape:

  * ``fail_open_except`` — an ``except`` handler whose body swallows the
    error into success: it returns ``0``/``True`` (or prints ``...PASS...``)
    and never re-raises / ``sys.exit``s with a nonzero code.
  * ``unfailable_gate`` — a gate-named function (``main``, ``check*``,
    ``validate*``, ``verify*``) whose every exit is a constant success and
    which contains no branch, raise, assert, or nonzero exit that could
    ever fail. A gate that cannot fail is not a gate.

The check is a *ratchet*: legitimate cases (a ``main`` that genuinely
always succeeds) are recorded, one ``relpath:rule`` per line, in
``tools/fail_open_allowlist.txt``. Real fail-open bugs must NOT be
allowlisted.

    python tools/lint_fail_open.py            # print JSON report
    python tools/lint_fail_open.py --check    # CI: exit 1 on new findings
"""

from __future__ import annotations

import argparse
import ast
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ALLOWLIST = ROOT / "tools" / "fail_open_allowlist.txt"

SCHEMA = "bsff.fail_open_lint/v1"
RULE_EXCEPT = "fail_open_except"
RULE_GATE = "unfailable_gate"

_GATE_PREFIXES = ("check", "validate", "verify")
_GATE_EXACT = ("main",)


def _is_gate_name(name: str) -> bool:
    return name in _GATE_EXACT or name.startswith(_GATE_PREFIXES)


def _is_success_return(node: ast.Return) -> bool:
    """True if ``node`` returns a hard-coded success value (0 or True)."""
    value = node.value
    if value is None:
        return False
    if isinstance(value, ast.Constant):
        val = value.value
        if val is True:
            return True
        return isinstance(val, int) and not isinstance(val, bool) and val == 0
    return False


def _is_pass_print(node: ast.AST) -> bool:
    """True if ``node`` is ``print("...PASS...")`` (case-insensitive)."""
    if not isinstance(node, ast.Call):
        return False
    func = node.func
    if not (isinstance(func, ast.Name) and func.id == "print"):
        return False
    for arg in node.args:
        if isinstance(arg, ast.Constant) and isinstance(arg.value, str):
            if "pass" in arg.value.lower():
                return True
    return False


def _walk_local(body: list[ast.stmt]):
    """Yield nodes in ``body`` without descending into nested def/class.

    Returns / raises belong to the enclosing function, so nested function
    and class bodies (which have their own control flow) are not traversed.
    """
    stack: list[ast.AST] = list(body)
    while stack:
        node = stack.pop()
        yield node
        for child in ast.iter_child_nodes(node):
            if isinstance(
                child,
                (ast.FunctionDef, ast.AsyncFunctionDef, ast.Lambda, ast.ClassDef),
            ):
                continue
            stack.append(child)


def _has_escape_hatch(nodes: list[ast.AST]) -> bool:
    """True if any node is a raise or a nonzero ``sys.exit``/``exit``/assert."""
    for node in nodes:
        if isinstance(node, (ast.Raise, ast.Assert)):
            return True
        if isinstance(node, ast.Call):
            func = node.func
            name = None
            if isinstance(func, ast.Name):
                name = func.id
            elif isinstance(func, ast.Attribute):
                name = func.attr
            if name in ("exit", "_exit"):
                # sys.exit()/exit()/os._exit(): nonzero or non-constant => can fail.
                if not node.args:
                    continue
                arg = node.args[0]
                if isinstance(arg, ast.Constant):
                    if arg.value not in (0, None, True):
                        return True
                else:
                    return True
    return False


def _snippet(lines: list[str], lineno: int) -> str:
    if 1 <= lineno <= len(lines):
        return lines[lineno - 1].strip()
    return ""


def _check_except(handler: ast.ExceptHandler, lines: list[str]) -> dict | None:
    body_nodes = list(_walk_local(handler.body))
    if _has_escape_hatch(body_nodes):
        return None  # re-raises or exits nonzero => fail closed.
    for node in body_nodes:
        if isinstance(node, ast.Return) and _is_success_return(node):
            return {
                "line": node.lineno,
                "rule": RULE_EXCEPT,
                "snippet": _snippet(lines, node.lineno),
            }
        if isinstance(node, ast.Expr) and _is_pass_print(node.value):
            return {
                "line": node.lineno,
                "rule": RULE_EXCEPT,
                "snippet": _snippet(lines, node.lineno),
            }
    return None


def _check_gate(func: ast.FunctionDef | ast.AsyncFunctionDef, lines: list[str]) -> dict | None:
    if not _is_gate_name(func.name):
        return None
    body_nodes = list(_walk_local(func.body))
    if _has_escape_hatch(body_nodes):
        return None
    returns = [n for n in body_nodes if isinstance(n, ast.Return)]
    if not returns:
        return None
    for ret in returns:
        # A non-constant return (call/name/expr) can propagate a failure code.
        if ret.value is not None and not isinstance(ret.value, ast.Constant):
            return None
        # A constant nonzero / False return is a real failure path.
        if isinstance(ret.value, ast.Constant):
            val = ret.value.value
            if val is False or (isinstance(val, int) and val not in (0,) and val is not True):
                return None
    # Every return is a constant success and nothing here can ever fail.
    if not any(_is_success_return(r) for r in returns):
        return None
    return {
        "line": func.lineno,
        "rule": RULE_GATE,
        "snippet": _snippet(lines, func.lineno),
    }


def analyze_source(source: str) -> list[dict]:
    """Return findings (line/rule/snippet) for one source string."""
    tree = ast.parse(source)
    lines = source.splitlines()
    findings: list[dict] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.ExceptHandler):
            found = _check_except(node, lines)
            if found is not None:
                findings.append(found)
        elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            found = _check_gate(node, lines)
            if found is not None:
                findings.append(found)
    return findings


def _iter_targets(root: Path, include_src: bool) -> list[Path]:
    targets: list[Path] = sorted((root / "tools").glob("*.py"))
    if include_src:
        targets += sorted((root / "src" / "bsff").rglob("*.py"))
    return [p for p in targets if p.name != "__init__.py" and "__pycache__" not in p.parts]


def evaluate(root: Path, include_src: bool = False) -> dict:
    """Analyze the repo; return the deterministic report dict."""
    root = Path(root)
    findings: list[dict] = []
    for path in _iter_targets(root, include_src):
        if path.resolve() == Path(__file__).resolve():
            continue  # never lint the linter itself
        try:
            source = path.read_text(encoding="utf-8")
        except OSError:
            continue
        try:
            local = analyze_source(source)
        except SyntaxError:
            continue
        rel = path.relative_to(root).as_posix()
        for item in local:
            findings.append(
                {
                    "file": rel,
                    "line": item["line"],
                    "rule": item["rule"],
                    "snippet": item["snippet"],
                }
            )
    findings.sort(key=lambda f: (f["file"], f["line"], f["rule"]))
    return {
        "schema": SCHEMA,
        "findings": findings,
        "status": "FAIL" if findings else "PASS",
    }


def _load_allowlist(path: Path) -> set[str]:
    if not path.exists():
        return set()
    keys: set[str] = set()
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        keys.add(line)
    return keys


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--check", action="store_true", help="exit 1 on findings beyond the allowlist"
    )
    parser.add_argument("--include-src", action="store_true", help="also scan src/bsff/**")
    args = parser.parse_args(argv)

    report = evaluate(ROOT, include_src=args.include_src)
    allowed = _load_allowlist(ALLOWLIST)
    residual = [f for f in report["findings"] if f"{f['file']}:{f['rule']}" not in allowed]

    print(json.dumps(report, indent=2, sort_keys=True))

    if args.check:
        if residual:
            print(
                f"\nfail-open lint: {len(residual)} finding(s) beyond allowlist",
                file=sys.stderr,
            )
            for f in residual:
                print(f"  {f['file']}:{f['line']} [{f['rule']}] {f['snippet']}", file=sys.stderr)
            return 1
        print("\nfail-open lint: OK", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
