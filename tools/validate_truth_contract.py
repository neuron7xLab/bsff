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
    r"regulatory[- ](ready|grade)",
    r"TISEAN validated",
    r"proves? BCI claims?",
    r"proves? EEG claims?",
    r"real EEG validated",
    r"external replication complete",
    r"external validation complete",
    r"scientifically proven",
    r"medical validation",
    r"production clinical use",
]
REQUIRED_LIMIT_DISCLOSURES = [
    "not externally validated against TISEAN",
    "not regulatory validation",
    "does **not** prove BCI claims",
]
# Explicitly enumerated negated/non-goal uses of an otherwise-forbidden lexeme.
# Every legitimate occurrence is listed and reviewable; any NEW affirmative use
# (e.g. "BSFF proves BCI claims") that is not on this list trips the gate.
# Truth-defining surfaces (the contract doc, validation tiers) necessarily quote
# the forbidden phrases to forbid them; those quotations are allow-listed here.
ALLOWED_NEGATED_PHRASES = [
    "prove BCI claims true",  # docs/ARCHITECTURE.md "Non-goals: BSFF does not: ..."
    "does not prove BCI claims",  # STATUS.md plain-text limitation disclosure
]

# Every public claim surface scanned by the contract. Declared so the truth
# surface is itself auditable (see docs/TRUTH_SURFACE.md). Files that define the
# forbidden vocabulary are scanned with the allow-list applied.
SURFACE_FILES = (
    "README.md",
    "VERDICT.md",
    "STATUS.md",
    "DEMONSTRATION.md",
    "CORE.md",
    "DECISION.md",
    "CLAIM_AUDIT.md",
    "pyproject.toml",
)
# Files whose PURPOSE is to enumerate the forbidden phrases (to forbid them); the
# affirmative-claim scan would self-trip on their negative examples, so they are
# checked structurally (must exist) rather than phrase-scanned.
CONTRACT_DEFINING_FILES = {
    "docs/TRUTH_SURFACE.md",
    "docs/VALIDATION_TIERS.md",
    "docs/TISEAN_EXTERNAL_PROTOCOL.md",
    "docs/REAL_EEG_ESCALATION_PLAN.md",
    "docs/INDEPENDENT_REPLICATION_PROTOCOL.md",
}


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


def build_corpus(root: Path = ROOT) -> str:
    """The canonical scanned corpus: public surfaces + docs/*.md, EXCEPT the
    contract-defining files that legitimately quote the forbidden vocabulary.

    Single source of truth for both main() and the guard test, so the two cannot
    drift apart on which surfaces are enforced.
    """
    docs_md = [
        p
        for p in sorted((root / "docs").glob("*.md"))
        if p.relative_to(root).as_posix() not in CONTRACT_DEFINING_FILES
    ]
    surfaces = [root / name for name in SURFACE_FILES] + docs_md
    return "\n".join(p.read_text(encoding="utf-8") for p in surfaces if p.exists())


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

    for claim in find_forbidden_claims(build_corpus()):
        failures.append(f"forbidden unqualified claim present: {claim}")
    # the contract-defining files must exist (the surface must be declared)
    for rel in ("docs/TRUTH_SURFACE.md", "docs/VALIDATION_TIERS.md"):
        if not (ROOT / rel).exists():
            failures.append(f"missing contract surface: {rel}")
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
