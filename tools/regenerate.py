#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (c) 2026 Yaroslav Vasylenko / neuron7xLab
"""Convergent regeneration — one declarative, idempotent orchestrator.

The generated surfaces (STATUS, MANIFEST, scorecard, DEMONSTRATION, DECISION,
CORE) form a dependency DAG: each reads truth produced upstream. Running them by
hand in the wrong order is the bug class behind several earlier slips. This
encodes the order once and applies two first principles from desired-state
configuration management (Microsoft DSC, Terraform, Ansible):

  * **topological order** — a generator runs only after its inputs are fresh;
  * **idempotence / fixpoint** — after one pass every ``--check`` must pass; a
    second pass must change nothing. We verify convergence rather than assume it.

Generators whose tool is absent are skipped (forward-compatible: scorecard joins
automatically once it lands). One command replaces a fragile manual chain.

    python tools/regenerate.py            # bring every generated surface to fixpoint
    python tools/regenerate.py --check     # assert the whole system is already at fixpoint
    python tools/regenerate.py --verify-idempotent   # prove a second pass changes nothing
"""

from __future__ import annotations

import argparse
import hashlib
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


@dataclass(frozen=True)
class Generator:
    name: str
    tool: str  # tools/<tool>.py
    outputs: tuple[str, ...]  # generated paths (for idempotence hashing)


# Declared in topological order: inputs of each are produced by those above it.
DAG: tuple[Generator, ...] = (
    Generator("status", "update_status", ("STATUS.md",)),
    Generator("manifest", "generate_manifest", ("artifacts/MANIFEST.json",)),
    Generator("scorecard", "compute_scorecard", ("artifacts/actions_99_scorecard.json",)),
    Generator(
        "demonstration",
        "build_demonstration",
        ("DEMONSTRATION.md", "artifacts/demonstration/demonstration.json"),
    ),
    Generator("decision", "decision_gate", ("DECISION.md", "artifacts/decision/decision.json")),
    Generator("core", "build_core", ("CORE.md",)),
)


def _present(g: Generator) -> bool:
    return (ROOT / "tools" / f"{g.tool}.py").is_file()


def _run(tool: str, *args: str) -> int:
    return subprocess.run(
        [sys.executable, str(ROOT / "tools" / f"{tool}.py"), *args],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    ).returncode


def _fingerprint() -> str:
    h = hashlib.sha256()
    for g in DAG:
        if not _present(g):
            continue
        for rel in g.outputs:
            p = ROOT / rel
            h.update(rel.encode())
            h.update(p.read_bytes() if p.is_file() else b"\0")
    return h.hexdigest()


def check() -> list[str]:
    """Return the names of generators whose output is stale (system not at fixpoint)."""
    stale = []
    for g in DAG:
        if _present(g) and _run(g.tool, "--check") != 0:
            stale.append(g.name)
    return stale


def regenerate(max_iter: int = 3) -> int:
    """Run generators in topological order until a fixpoint; return iterations used."""
    for iteration in range(1, max_iter + 1):
        for g in DAG:
            if _present(g):
                _run(g.tool)
        if not check():
            return iteration
    return max_iter


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--check", action="store_true")
    p.add_argument("--verify-idempotent", action="store_true")
    args = p.parse_args(argv)
    active = [g.name for g in DAG if _present(g)]

    if args.check:
        stale = check()
        print(
            f"regeneration fixpoint: {len(active)} generators; "
            + ("at fixpoint" if not stale else f"STALE: {stale}")
        )
        return 0 if not stale else 1

    if args.verify_idempotent:
        regenerate()
        before = _fingerprint()
        for g in DAG:
            if _present(g):
                _run(g.tool)
        after = _fingerprint()
        ok = before == after
        print(
            f"idempotence: second pass {'changed nothing' if ok else 'CHANGED OUTPUT'} "
            f"({before[:12]} -> {after[:12]})"
        )
        return 0 if ok else 1

    iters = regenerate()
    stale = check()
    print(
        f"regenerated {len(active)} surfaces in topological order; "
        f"converged in {iters} pass(es); "
        + ("fixpoint reached" if not stale else f"STALE: {stale}")
    )
    return 0 if not stale else 1


if __name__ == "__main__":
    raise SystemExit(main())
