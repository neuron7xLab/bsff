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

Scope and known limitations
---------------------------
Detecting fail-open code over arbitrary Python is **undecidable**: whether a
handler can reach a success exit on a live path is a reachability/dataflow
question no purely-syntactic walker can settle in general. This module is a
*best-effort ratchet*, not a proof of fail-closed-ness. It deliberately does
NOT claim completeness. Concretely, the following shapes are known to evade
detection and are accepted as residual gaps:

  * ``except ...: pass`` where the swallowed error later reaches a
    fall-through ``return 0`` elsewhere in a non-gate helper. The handler
    itself contains no success exit, and cross-statement dataflow (does the
    swallow feed the later success?) is not modelled.
  * A success value laundered through computation, e.g. ``return len(errors)``
    where ``errors`` is provably always empty. Only literal / trivially
    name-resolved constants are recognised; arithmetic and container state
    are not evaluated.
  * Exceptions swallowed by a *decorator* (e.g. a ``@suppress_errors`` wrapper)
    rather than by an in-body ``except``. The linter never follows into
    decorator implementations.

What *is* recognised (best-effort): success ``return``/``sys.exit`` inside an
``except`` handler, including a returned module-level ``NAME = 0`` constant;
gate functions with only constant-success exits; and it correctly treats
``sys.exit(1)``/``sys.exit(2)`` as genuine failure exits (escape hatches) while
ignoring obviously-dead decoy guards (``assert True``, ``if False:``/``if 0:``)
so a live-path success exit is still flagged.
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


def _is_success_value(val: object) -> bool:
    """True if ``val`` is a hard-coded success sentinel (``0`` or ``True``)."""
    if val is True:
        return True
    return type(val) is int and val == 0


def _is_success_return(node: ast.Return, consts: dict[str, object] | None = None) -> bool:
    """True if ``node`` returns a hard-coded success value (0 or True).

    ``consts`` maps module-level ``NAME = <constant>`` bindings, so a bare
    ``return EXIT_SUCCESS`` where ``EXIT_SUCCESS = 0`` also counts (Hole 2).
    """
    value = node.value
    if value is None:
        return False
    if isinstance(value, ast.Constant):
        return _is_success_value(value.value)
    if consts is not None and isinstance(value, ast.Name) and value.id in consts:
        return _is_success_value(consts[value.id])
    return False


def _module_constants(tree: ast.Module) -> dict[str, object]:
    """Resolve simple module-level ``NAME = <constant>`` bindings.

    Only top-level, single-target assignments to a literal are captured; a
    name reassigned more than once is dropped (ambiguous). This is a shallow
    resolver, not a dataflow engine (see module docstring on limitations).
    """
    seen: dict[str, int] = {}
    consts: dict[str, object] = {}
    for stmt in tree.body:
        if not isinstance(stmt, ast.Assign):
            continue
        if len(stmt.targets) != 1 or not isinstance(stmt.targets[0], ast.Name):
            continue
        if not isinstance(stmt.value, ast.Constant):
            continue
        name = stmt.targets[0].id
        seen[name] = seen.get(name, 0) + 1
        consts[name] = stmt.value.value
    return {k: v for k, v in consts.items() if seen.get(k, 0) == 1}


def _is_success_exit(node: ast.AST) -> bool:
    """True if ``node`` is a success ``sys.exit``/``exit``/``os._exit`` call.

    A no-arg ``exit()`` or an ``exit(0)``/``exit(None)`` terminates the process
    reporting success; inside an ``except`` handler that is a fail-open (Hole 3).
    """
    if not isinstance(node, ast.Call):
        return False
    func = node.func
    name = None
    if isinstance(func, ast.Name):
        name = func.id
    elif isinstance(func, ast.Attribute):
        name = func.attr
    if name not in ("exit", "_exit"):
        return False
    if not node.args:
        return True
    arg = node.args[0]
    if isinstance(arg, ast.Constant):
        v = arg.value
        return v is None or (type(v) is int and v == 0)
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
        # Dead-branch pruning: a constant-tested ``if`` executes only one arm,
        # so a decoy escape hatch buried in the unreachable arm (``if False:
        # sys.exit(1)``) must not mask a live-path fail-open (Hole 4).
        if isinstance(node, ast.If) and isinstance(node.test, ast.Constant):
            children: list[ast.AST] = list(node.body if node.test.value else node.orelse)
        else:
            children = list(ast.iter_child_nodes(node))
        for child in children:
            if isinstance(
                child,
                (ast.FunctionDef, ast.AsyncFunctionDef, ast.Lambda, ast.ClassDef),
            ):
                continue
            stack.append(child)


def _has_escape_hatch(nodes: list[ast.AST]) -> bool:
    """True if any node is a genuine failure exit (escape hatch).

    A raise, a failing ``assert``, or a nonzero/non-constant ``sys.exit``
    counts. ``assert True`` (a no-op that can never fail) does not, so it
    cannot be used as a decoy fail-closed guard (Hole 4).
    """
    for node in nodes:
        if isinstance(node, ast.Raise):
            return True
        if isinstance(node, ast.Assert):
            # ``assert True`` / ``assert 1`` never fires; only a fallible
            # assertion is a real escape hatch.
            if isinstance(node.test, ast.Constant) and node.test.value:
                continue
            return True
        if isinstance(node, ast.Call):
            func = node.func
            name = None
            if isinstance(func, ast.Name):
                name = func.id
            elif isinstance(func, ast.Attribute):
                name = func.attr
            if name in ("exit", "_exit"):
                # sys.exit()/exit()/os._exit(): only exit code 0/None is a
                # *success* exit. Anything else -- including sys.exit(1) and
                # sys.exit(2) -- is a genuine failure exit / escape hatch.
                # Guard with ``type(v) is int`` because Python evaluates
                # ``1 == True``, which previously misclassified sys.exit(1)
                # as success (Bug 7).
                if not node.args:
                    continue  # exit() == exit(0): a success exit, not a hatch.
                arg = node.args[0]
                if isinstance(arg, ast.Constant):
                    v = arg.value
                    if not (v is None or (type(v) is int and v == 0)):
                        return True
                else:
                    return True
    return False


def _snippet(lines: list[str], lineno: int) -> str:
    if 1 <= lineno <= len(lines):
        return lines[lineno - 1].strip()
    return ""


def _check_except(
    handler: ast.ExceptHandler,
    lines: list[str],
    consts: dict[str, object] | None = None,
) -> dict | None:
    body_nodes = list(_walk_local(handler.body))
    if _has_escape_hatch(body_nodes):
        return None  # re-raises or exits nonzero => fail closed.
    for node in body_nodes:
        if isinstance(node, ast.Return) and _is_success_return(node, consts):
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
        # A success process-exit inside the handler is itself fail-open (Hole 3).
        if isinstance(node, ast.Expr) and _is_success_exit(node.value):
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
    consts = _module_constants(tree)
    findings: list[dict] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.ExceptHandler):
            found = _check_except(node, lines, consts)
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
