# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (c) 2026 Yaroslav Vasylenko / neuron7xLab
"""Human-readable report rendering (Markdown + HTML)."""

import pytest

from bsff.adjudication import (
    BatchItem,
    ProposedClaim,
    SourceDocument,
    adjudicate,
    adjudicate_batch,
    render_html,
    render_markdown,
)

TEXT = (
    "Decoding accuracy was 84% (p < 0.01). Clinicians should adopt it. "
    "The <script> tag is defined as markup."
)


def _single():
    src = SourceDocument.from_text(source_id="paperA", kind="text", uri="", text=TEXT)
    claims = [
        ProposedClaim("c1", "Decoding accuracy was 84% (p < 0.01)", "human:y"),
        ProposedClaim("c2", "Clinicians should adopt it", "human:y"),
    ]
    return adjudicate(src, claims)


def _batch():
    src = SourceDocument.from_text(source_id="paperA", kind="text", uri="", text=TEXT)
    claims = [
        ProposedClaim("f1", "the brain emits telepathy waves at scale", "llm:rogue"),
        ProposedClaim("f2", "neurons compute via pineal crystal resonance", "llm:rogue"),
        ProposedClaim("f3", "consciousness is a fifth fundamental force field", "llm:rogue"),
    ]
    return adjudicate_batch([BatchItem(source=src, claims=claims)])


def test_markdown_escapes_table_injection_in_proposer_id():
    # Regression: render_markdown interpolated attacker-controlled ids raw, so a
    # proposer like "honest | 9 | 0.00 | 0.00 |\n| <!--" forged a clean accountability
    # row and detached the real fabrication rate from the actor. Pipes/newlines must
    # be neutralised so one proposer renders exactly one row.
    from bsff.adjudication.report_render import BATCH_SCHEMA

    forged = "honest | 9 | 0.00 | 0.00 |\n| <!--"
    report = {
        "schema": BATCH_SCHEMA,
        "integrity_flags": [
            {"kind": "PROPOSER_FABRICATION", "subject": forged, "rate": 1.0, "detail": "x|y"}
        ],
        "proposer_accountability": {
            forged: {"proposed": 3, "unanchored_rate": 1.0, "quarantine_rate": 1.0}
        },
        "artifact_sha256": "0" * 64,
    }
    md = render_markdown(report)
    # The forged content survives only as escaped text on a single line — never as a
    # second table row (no unescaped pipe, no injected newline splitting the row).
    assert "honest \\| 9 \\| 0.00" in md
    for line in md.splitlines():
        # No data row may present a forged clean count for the fabricating proposer.
        assert not line.strip().startswith("| honest | 9 |")


def test_single_markdown_has_verdicts():
    md = render_markdown(_single())
    assert "# BSFF adjudication report" in md
    assert "c1" in md and "QUARANTINED_NORMATIVE" in md
    assert "not 'true'" in md or "PENDING_EVIDENCE" in md


def test_single_html_is_self_contained():
    htm = render_html(_single())
    assert htm.startswith("<!doctype html>")
    assert "<style>" in htm and "artifact" in htm


def test_html_escapes_content():
    # the source text contains a <script> fragment; rendered HTML must escape it
    htm = render_html(_single())
    assert "<script>" not in htm  # raw tag must not leak
    # but the source_id and dispositions are present
    assert "paperA" in htm


def test_batch_render_surfaces_integrity_flags():
    report = _batch()
    md = render_markdown(report)
    assert "corpus adjudication" in md
    assert "PROPOSER_FABRICATION" in md or "HIGH_UNANCHORED_RATE" in md
    htm = render_html(report)
    assert "Extraction integrity" in htm
    assert "llm:rogue" in htm


def test_unrenderable_schema_rejected():
    with pytest.raises(ValueError, match="unrenderable report schema"):
        render_markdown({"schema": "bogus/v9"})
    with pytest.raises(ValueError, match="unrenderable report schema"):
        render_html({"schema": "bogus/v9"})
