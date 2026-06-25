# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (c) 2026 Yaroslav Vasylenko / neuron7xLab
"""Grounding gate: every load-bearing number in prose must match its artifact.

A number typed into a document is text — it can drift or lie. A number that
re-derives from a generated artifact is a verifiable fact. This gate binds the
two: for each registered fact it reads the asserted value from a doc AND the live
value from its source artifact, and fails closed if they differ. After this gate
passes, those statements are not prose; they are checkable facts.

    python tools/verify_grounding.py
"""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

# Each fact: a value asserted in `doc` must equal round(source[key], dp).
# `context` (optional) anchors the assertion to its claim site: the derived value
# must appear as a standalone numeric token ON THE SAME LINE as `context`. Without
# it a bare substring check fails open — a wrong asserted value (gap = 0.999) still
# "grounds" as long as the correct number appears anywhere else in the doc (e.g. a
# neighbouring fact, a filter spec like "10.204 dB", or a superstring like 0.2041).
GROUNDED_FACTS = [
    {
        "label": "MANUSCRIPT LOSO within-subject",
        "doc": "docs/MANUSCRIPT.md",
        "source": "research/bci_generalization/result_bnci2014_001_sub1-2.json",
        "key": "within_mean",
        "dp": 3,
        "context": "WithinSession",
    },
    {
        "label": "MANUSCRIPT LOSO cross-subject",
        "doc": "docs/MANUSCRIPT.md",
        "source": "research/bci_generalization/result_bnci2014_001_sub1-2.json",
        "key": "cross_subject_loso_mean",
        "dp": 3,
        "context": "CrossSubject",
    },
    {
        "label": "MANUSCRIPT LOSO gap",
        "doc": "docs/MANUSCRIPT.md",
        "source": "research/bci_generalization/result_bnci2014_001_sub1-2.json",
        "key": "loso_gap",
        "dp": 3,
        "context": "generalization gap",
    },
    {
        "label": "FINDING_N9 within-subject (n=9)",
        "doc": "docs/FINDING_N9.md",
        "source": "research/bci_generalization/result_eegbci_loso_n9.json",
        "key": "within_subject_mean",
        "dp": 3,
        "context": "within-subject mean",
    },
    {
        "label": "FINDING_N9 cross-subject LOSO (n=9)",
        "doc": "docs/FINDING_N9.md",
        "source": "research/bci_generalization/result_eegbci_loso_n9.json",
        "key": "cross_subject_loso_mean",
        "dp": 3,
        "context": "cross-subject (LOSO) mean",
    },
    {
        "label": "FINDING_N9 gap (n=9)",
        "doc": "docs/FINDING_N9.md",
        "source": "research/bci_generalization/result_eegbci_loso_n9.json",
        "key": "loso_gap",
        "dp": 3,
        "context": "generalization gap",
    },
]


def _derive(source: str, key: str, dp: int) -> str:
    data = json.loads((ROOT / source).read_text(encoding="utf-8"))
    return str(round(float(data[key]), dp))


def _token_re(value: str) -> re.Pattern[str]:
    # Standalone numeric token: reject letter/digit/underscore/dot on either side so
    # "0.204" does not match inside "10.204", "a0.204f", or "0.2041".
    return re.compile(rf"(?<![\w.]){re.escape(value)}(?![\w])")


def _grounded(doc_text: str, derived: str, context: str | None) -> bool:
    token = _token_re(derived)
    if context is None:
        # No claim-site anchor: still require a standalone token (kills substring/
        # superstring drift), but cannot bind to a specific assertion.
        return token.search(doc_text) is not None
    # Anchored: the value must be a standalone token on a line that names the claim.
    ctx = context.lower()
    return any(ctx in line.lower() and token.search(line) for line in doc_text.splitlines())


def check(facts: list[dict] | None = None, *, readme_check: bool = True) -> list[str]:
    facts = GROUNDED_FACTS if facts is None else facts
    failures: list[str] = []
    for fact in facts:
        derived = _derive(fact["source"], fact["key"], fact["dp"])
        doc_text = (ROOT / fact["doc"]).read_text(encoding="utf-8")
        if not _grounded(doc_text, derived, fact.get("context")):
            where = f"near '{fact['context']}'" if fact.get("context") else f"in {fact['doc']}"
            failures.append(
                f"{fact['label']}: artifact says {derived} ({fact['source']}::{fact['key']}) "
                f"but no standalone-token match {where} — ungrounded/stale"
            )

    # README's test count must be grounded BY REFERENCE to STATUS.md, never a hardcoded badge.
    if readme_check:
        readme = (ROOT / "README.md").read_text(encoding="utf-8")
        if re.search(r"tests-\d+%2F\d+", readme):
            failures.append("README test badge hardcodes a count; ground it to STATUS.md instead")
    return failures


def main(argv: list[str] | None = None) -> int:
    argparse.ArgumentParser(description=__doc__).parse_args(argv)
    failures = check()
    print(f"grounding: {len(GROUNDED_FACTS)} registered facts + README badge check")
    for f in failures:
        print(f"  UNGROUNDED: {f}")
    if failures:
        return 1
    print(
        "grounding: every registered number matches its artifact; README badge references STATUS.md."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
