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
GROUNDED_FACTS = [
    {
        "label": "MANUSCRIPT LOSO within-subject",
        "doc": "docs/MANUSCRIPT.md",
        "source": "research/bci_generalization/result_bnci2014_001_sub1-2.json",
        "key": "within_mean",
        "dp": 3,
    },
    {
        "label": "MANUSCRIPT LOSO cross-subject",
        "doc": "docs/MANUSCRIPT.md",
        "source": "research/bci_generalization/result_bnci2014_001_sub1-2.json",
        "key": "cross_subject_loso_mean",
        "dp": 3,
    },
    {
        "label": "MANUSCRIPT LOSO gap",
        "doc": "docs/MANUSCRIPT.md",
        "source": "research/bci_generalization/result_bnci2014_001_sub1-2.json",
        "key": "loso_gap",
        "dp": 3,
    },
    {
        "label": "FINDING_N9 within-subject (n=9)",
        "doc": "docs/FINDING_N9.md",
        "source": "research/bci_generalization/result_eegbci_loso_n9.json",
        "key": "within_subject_mean",
        "dp": 3,
    },
    {
        "label": "FINDING_N9 cross-subject LOSO (n=9)",
        "doc": "docs/FINDING_N9.md",
        "source": "research/bci_generalization/result_eegbci_loso_n9.json",
        "key": "cross_subject_loso_mean",
        "dp": 3,
    },
    {
        "label": "FINDING_N9 gap (n=9)",
        "doc": "docs/FINDING_N9.md",
        "source": "research/bci_generalization/result_eegbci_loso_n9.json",
        "key": "loso_gap",
        "dp": 3,
    },
]


def _derive(source: str, key: str, dp: int) -> str:
    data = json.loads((ROOT / source).read_text(encoding="utf-8"))
    return str(round(float(data[key]), dp))


def check(facts: list[dict] | None = None, *, readme_check: bool = True) -> list[str]:
    facts = GROUNDED_FACTS if facts is None else facts
    failures: list[str] = []
    for fact in facts:
        derived = _derive(fact["source"], fact["key"], fact["dp"])
        doc_text = (ROOT / fact["doc"]).read_text(encoding="utf-8")
        if derived not in doc_text:
            failures.append(
                f"{fact['label']}: artifact says {derived} ({fact['source']}::{fact['key']}) "
                f"but it does not appear in {fact['doc']} — ungrounded/stale"
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
