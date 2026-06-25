#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (c) 2026 Yaroslav Vasylenko / neuron7xLab
"""Claim-integrity gate for the OpenAI-2026 Validation Grid.

The grid is an INTERNAL OpenAI-grade research-validation target, NOT an external
OpenAI certification. This gate fails CI if any public surface asserts a forbidden
OpenAI-relationship claim (certified/validated/approved/endorsed/official benchmark/
partnership) without an ADJACENT negating qualifier, or if an evidence-bearing
allowed claim lacks a resolvable evidence pointer whose content actually supports it.

Hardened against the red-team audit (2026-06): scans every tracked public text
surface (md/rst/py docstrings/pyproject/cff/zenodo/paper/examples), not just *.md;
normalizes Unicode (NFKC) and zero-width/whitespace so homoglyph and double-space
evasion fail; matches across line wraps; and only exempts a match when the negation
is ADJACENT (not anywhere on the line), so "no doubt BSFF is certified by OpenAI"
is still caught.

    python tools/validate_openai_2026_claims.py [--json] [--check]

Exit code 0 ⇒ clean; 1 ⇒ violations. --check also writes
artifacts/claim/claim_integrity_report.json (the fresh report the eval contract
grades, so no consumer trusts a committed/forgeable roll-up).
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
import unicodedata
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CLAIMS = ROOT / "claims"
REPORT = ROOT / "artifacts" / "claim" / "claim_integrity_report.json"

# Text surfaces that ship publicly (render on GitHub/PyPI or are packaged in the
# wheel). Definition files (claims/, this tool) and the test corpus (which embeds
# the forbidden phrases as fixtures) are excluded.
_SCAN_SUFFIXES = {".md", ".rst", ".cff", ".py", ".toml"}
_EXTRA_FILES = (".zenodo.json",)
_EXCLUDE_PREFIXES = (
    "claims/",
    "tools/validate_openai_2026_claims.py",
    "tests/",
    "dist/",
    "build/",
    "node_modules/",
)

# Adjacent-negation window: a forbidden match is exempt only when a negation token
# appears within this many characters BEFORE it (a real disclaimer), not merely
# somewhere on the line.
_NEG_WINDOW = 18
_NEG_TOKENS = re.compile(
    r"\b(?:no|not|never|neither|nor|without|n't|forbidden|excluded)\b|do not claim|is not|are not",
    re.IGNORECASE,
)
_ZERO_WIDTH = re.compile(r"[​‌‍﻿]")


def _rel(path: Path) -> str:
    try:
        return str(path.relative_to(ROOT))
    except ValueError:
        return str(path)


def _normalize(text: str) -> str:
    """NFKC fold, strip zero-width chars, collapse whitespace runs to one space."""
    text = unicodedata.normalize("NFKC", text)
    text = _ZERO_WIDTH.sub("", text)
    return text


def _load_yaml(path: Path) -> dict:
    import yaml  # local import: yaml is an extra

    return yaml.safe_load(path.read_text(encoding="utf-8")) or {}


def _tracked_files() -> list[str]:
    proc = subprocess.run(
        ["git", "ls-files"], cwd=ROOT, capture_output=True, text=True, check=False
    )
    if proc.returncode != 0:
        return []
    return proc.stdout.splitlines()


def _iter_surfaces() -> list[Path]:
    surfaces: list[Path] = []
    for rel in _tracked_files():
        if any(rel.startswith(pref) for pref in _EXCLUDE_PREFIXES):
            continue
        suffix = Path(rel).suffix
        if (
            suffix in _SCAN_SUFFIXES
            or rel.endswith(_EXTRA_FILES)
            or Path(rel).name == "pyproject.toml"
        ):
            p = ROOT / rel
            if p.is_file():
                surfaces.append(p)
    return sorted(set(surfaces))


def _compile(pattern: str) -> re.Pattern[str]:
    # Literal spaces in a forbidden phrase match any whitespace run, so
    # "certified  by  OpenAI" cannot evade.
    return re.compile(pattern.replace(" ", r"\s+"), re.IGNORECASE)


def _is_negated(text: str, start: int) -> bool:
    window = text[max(0, start - _NEG_WINDOW) : start]
    return _NEG_TOKENS.search(window) is not None


def _scan_text(
    text: str, surface: str, compiled: list[tuple[str, re.Pattern[str], str]]
) -> list[dict]:
    """Scan one normalized text (line-numbered if it has newlines, else collapsed)."""
    violations: list[dict] = []
    lines = text.splitlines() or [text]
    for lineno, raw in enumerate(lines, start=1):
        for cid, rx, reason in compiled:
            for m in rx.finditer(raw):
                if _is_negated(raw, m.start()):
                    continue
                violations.append(
                    {
                        "id": cid,
                        "surface": surface,
                        "line": lineno,
                        "text": raw.strip()[:200],
                        "reason": reason,
                    }
                )
    return violations


def _scan_forbidden(forbidden: list[dict]) -> list[dict]:
    compiled = [(f["id"], _compile(f["pattern"]), f.get("reason", "")) for f in forbidden]
    violations: list[dict] = []
    seen: set[tuple[str, str, int]] = set()
    for surface in _iter_surfaces():
        try:
            raw_text = surface.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            continue
        norm = _normalize(raw_text)
        rel = _rel(surface)
        # Per-line pass (precise line numbers).
        for v in _scan_text(norm, rel, compiled):
            key = (v["id"], v["surface"], v["line"])
            if key not in seen:
                seen.add(key)
                violations.append(v)
        # Collapsed pass catches phrases split across line wraps.
        collapsed = re.sub(r"\s+", " ", norm)
        for v in _scan_text(collapsed, rel, compiled):
            key = (v["id"], v["surface"], -1)
            if key not in seen:
                seen.add(key)
                v["line"] = -1  # multiline/collapsed match
                violations.append(v)
    return violations


def _check_evidence_pointers(allowed_doc: dict) -> list[dict]:
    if not allowed_doc.get("require_evidence_pointer", False):
        return []
    missing: list[dict] = []
    for claim in allowed_doc.get("allowed", []):
        cid = claim.get("id")
        ev = claim.get("evidence")
        if not ev:
            missing.append({"id": cid, "reason": "allowed claim has no evidence pointer"})
            continue
        target = ROOT / ev
        if not target.is_file():
            missing.append({"id": cid, "reason": f"evidence pointer does not resolve: {ev}"})
            continue
        try:
            content = re.sub(r"\s+", " ", _normalize(target.read_text(encoding="utf-8")))
        except (OSError, UnicodeDecodeError) as exc:
            missing.append({"id": cid, "reason": f"evidence unreadable: {exc}"})
            continue
        # Content check: the evidence must actually SUPPORT the claim, so a pointer
        # to LICENSE or an empty file cannot satisfy it. Whitespace is collapsed so
        # a phrase wrapped across lines still matches.
        needle = claim.get("evidence_must_contain")
        if not needle:
            missing.append({"id": cid, "reason": "allowed claim missing evidence_must_contain"})
            continue
        if re.sub(r"\s+", " ", _normalize(needle)).lower() not in content.lower():
            missing.append({"id": cid, "reason": f"evidence {ev} does not contain {needle!r}"})
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
    ap.add_argument(
        "--check", action="store_true", help="write artifacts/claim/claim_integrity_report.json"
    )
    args = ap.parse_args(argv)
    result = run()
    if args.check:
        REPORT.parent.mkdir(parents=True, exist_ok=True)
        REPORT.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
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
