#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (c) 2026 Yaroslav Vasylenko / neuron7xLab
from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
sys.path.insert(0, str(SRC))

from bsff.validation import assert_phase1_artifact, load_json  # noqa: E402

FORBIDDEN_UNQUALIFIED_CLAIMS = [
    r"clinically validated",
    r"regulatory[- ]ready",
    r"TISEAN validated",
    r"proves? BCI claims?",
]
REQUIRED_LIMIT_DISCLOSURES = [
    "not externally validated against TISEAN",
    "not regulatory validation",
    "does **not** prove BCI claims",
]
# Explicitly enumerated negated/non-goal uses of an otherwise-forbidden lexeme.
# Every legitimate occurrence is listed and reviewable; any NEW affirmative use
# (e.g. "BSFF proves BCI claims") that is not on this list trips the gate.
ALLOWED_NEGATED_PHRASES = [
    "prove BCI claims true",  # docs/ARCHITECTURE.md "Non-goals: BSFF does not: ..."
]


def find_forbidden_claims(corpus: str) -> list[str]:
    """Return forbidden affirmative claims present in ``corpus``.

    Negated disclosures and explicitly enumerated non-goal phrasings are stripped
    first so a legitimate "does not prove BCI claims" sentence is not mistaken for
    the affirmative "proves BCI claims"; matching is case-insensitive so
    capitalised patterns ("TISEAN validated", "proves BCI claims") actually
    enforce instead of silently never firing against a lower-cased corpus.
    """
    scan = corpus.lower()
    for phrase in (*REQUIRED_LIMIT_DISCLOSURES, *ALLOWED_NEGATED_PHRASES):
        scan = scan.replace(phrase.lower(), " ")
    return [
        claim for claim in FORBIDDEN_UNQUALIFIED_CLAIMS if re.search(claim, scan, re.IGNORECASE)
    ]


def main() -> int:
    failures: list[str] = []
    artifact = ROOT / "artifacts" / "bsff_phase1_validation.json"
    if artifact.exists():
        try:
            assert_phase1_artifact(load_json(artifact))
        except Exception as exc:
            failures.append(f"phase1 artifact invalid: {exc}")
    else:
        failures.append("missing artifacts/bsff_phase1_validation.json")

    corpus = "\n".join(
        p.read_text(encoding="utf-8")
        for p in [ROOT / "README.md", ROOT / "VERDICT.md", *sorted((ROOT / "docs").glob("*.md"))]
        if p.exists()
    )
    for claim in find_forbidden_claims(corpus):
        failures.append(f"forbidden unqualified claim present: {claim}")
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    for disclosure in REQUIRED_LIMIT_DISCLOSURES:
        if disclosure not in readme:
            failures.append(f"missing disclosure: {disclosure}")
    if failures:
        print("Truth contract failures:")
        for failure in failures:
            print(f"- {failure}")
        return 1
    print("Truth contract: PASS")
    return 0


if __name__ == "__main__":
    sys.exit(main())
