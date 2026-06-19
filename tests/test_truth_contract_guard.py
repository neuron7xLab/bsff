# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (c) 2026 Yaroslav Vasylenko / neuron7xLab
"""The truth-contract guard must actually fire on affirmative over-claims.

Two of the forbidden patterns carry capitals ("TISEAN validated", "proves BCI
claims"). Scanned case-sensitively against a lower-cased corpus they could never
match — a guard that only looked strict. These tests pin that affirmative claims
are caught while the legitimate negated disclosures are not false-positived.
"""

from __future__ import annotations

import sys
from pathlib import Path

TOOLS = Path(__file__).resolve().parents[1] / "tools"
sys.path.insert(0, str(TOOLS))

from validate_truth_contract import find_forbidden_claims  # noqa: E402


def test_affirmative_overclaims_are_caught_case_insensitively():
    assert find_forbidden_claims("BSFF proves BCI claims on every dataset.")
    assert find_forbidden_claims("This engine is TISEAN validated.")
    assert find_forbidden_claims("The kernel is Clinically Validated.")
    assert find_forbidden_claims("A regulatory-ready BCI verdict.")


def test_negated_disclosures_are_not_false_positives():
    assert find_forbidden_claims("BSFF does **not** prove BCI claims.") == []
    assert find_forbidden_claims("It is not externally validated against TISEAN.") == []
    # Non-goal phrasing from docs/ARCHITECTURE.md.
    assert find_forbidden_claims("BSFF does not:\n- prove BCI claims true,") == []


def test_repo_corpus_is_clean():
    root = Path(__file__).resolve().parents[1]
    corpus = "\n".join(
        p.read_text(encoding="utf-8")
        for p in [root / "README.md", root / "VERDICT.md", *sorted((root / "docs").glob("*.md"))]
        if p.exists()
    )
    assert find_forbidden_claims(corpus) == []
