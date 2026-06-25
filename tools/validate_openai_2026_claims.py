#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (c) 2026 Yaroslav Vasylenko / neuron7xLab
"""Claim-integrity gate for the OpenAI-2026 Validation Grid.

The grid is an INTERNAL OpenAI-grade research-validation target, NOT an external
OpenAI certification. This gate fails CI if any public surface asserts a forbidden
OpenAI-relationship claim (certified/validated/approved/endorsed/official benchmark/
partnership) without a negating qualifier, or if an evidence-bearing allowed claim
lacks a resolvable evidence pointer.

    python tools/validate_openai_2026_claims.py [--json]

Exit code 0 ⇒ clean; 1 ⇒ violations. With --json the machine summary
({"verdict", "forbidden_violations", "surfaces_scanned", ...}) is printed to stdout.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CLAIMS = ROOT / "claims"

# Surfaces scanned for forbidden claims. Definition files (claims/, this tool) are
# deliberately excluded — they CONTAIN the forbidden patterns by design.
_SURFACE_GLOBS = ("*.md", "docs/**/*.md", "docs/reviewer_packet/*.md")
_EXCLUDE_DIRS = ("claims", "tools", ".git", "node_modules", "dist", "build")

_NEG = re.compile(
    r"\bno\b|\bnot\b|\bnever\b|\bneither\b|n't|without|forbidden|do not claim|is not|are not",
    re.IGNORECASE,
)


def _rel(path: Path) -> str:
    """Display path relative to ROOT when possible, else the bare path.

    A scanned surface is normally under ROOT, but callers (and tests) may inject a
    surface elsewhere; never let a path outside ROOT crash the gate.
    """
    try:
        return str(path.relative_to(ROOT))
    except ValueError:
        return str(path)


def _load_yaml(path: Path) -> dict:
    import yaml  # local import: yaml is an extra

    return yaml.safe_load(path.read_text(encoding="utf-8")) or {}


def _iter_surfaces() -> list[Path]:
    seen: set[Path] = set()
    for glob in _SURFACE_GLOBS:
        for p in ROOT.glob(glob):
            if not p.is_file():
                continue
            rel_parts = p.relative_to(ROOT).parts
            if rel_parts and rel_parts[0] in _EXCLUDE_DIRS:
                continue
            seen.add(p)
    return sorted(seen)


def _scan_forbidden(forbidden: list[dict]) -> list[dict]:
    compiled = [
        (f["id"], re.compile(f["pattern"], re.IGNORECASE), f.get("reason", "")) for f in forbidden
    ]
    violations: list[dict] = []
    for surface in _iter_surfaces():
        try:
            lines = surface.read_text(encoding="utf-8").splitlines()
        except OSError:
            continue
        for lineno, line in enumerate(lines, start=1):
            if _NEG.search(line):
                continue  # negated / disclaimed mention is allowed
            for cid, rx, reason in compiled:
                if rx.search(line):
                    violations.append(
                        {
                            "id": cid,
                            "surface": _rel(surface),
                            "line": lineno,
                            "text": line.strip()[:200],
                            "reason": reason,
                        }
                    )
    return violations


def _check_evidence_pointers(allowed_doc: dict) -> list[dict]:
    if not allowed_doc.get("require_evidence_pointer", False):
        return []
    missing: list[dict] = []
    for claim in allowed_doc.get("allowed", []):
        ev = claim.get("evidence")
        if not ev:
            missing.append(
                {"id": claim.get("id"), "reason": "allowed claim has no evidence pointer"}
            )
            continue
        if not (ROOT / ev).exists():
            missing.append(
                {"id": claim.get("id"), "reason": f"evidence pointer does not resolve: {ev}"}
            )
    return missing


def run() -> dict:
    forbidden_doc = _load_yaml(CLAIMS / "openai_2026_forbidden_claims.yml")
    allowed_doc = _load_yaml(CLAIMS / "openai_2026_allowed_claims.yml")
    forbidden_violations = _scan_forbidden(forbidden_doc.get("forbidden", []))
    evidence_gaps = _check_evidence_pointers(allowed_doc)
    all_violations = forbidden_violations + evidence_gaps
    return {
        "gate": "openai-2026-claim-integrity",
        "verdict": "PASS" if not all_violations else "FAIL",
        "forbidden_violations": all_violations,
        "surfaces_scanned": [_rel(p) for p in _iter_surfaces()],
        "allowed_claims": [c.get("id") for c in allowed_doc.get("allowed", [])],
    }


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--json", action="store_true", help="emit machine summary to stdout")
    args = ap.parse_args(argv)
    result = run()
    if args.json:
        print(json.dumps(result, indent=2, sort_keys=True))
    else:
        for v in result["forbidden_violations"]:
            print(
                f"CLAIM VIOLATION [{v.get('id')}] {v.get('surface', '')}:{v.get('line', '')} "
                f"{v.get('reason', '')}",
                file=sys.stderr,
            )
        print(
            f"claim-integrity: {result['verdict']} "
            f"({len(result['forbidden_violations'])} violations, "
            f"{len(result['surfaces_scanned'])} surfaces scanned)"
        )
    return 0 if result["verdict"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
