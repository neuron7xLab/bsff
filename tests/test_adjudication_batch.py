# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (c) 2026 Yaroslav Vasylenko / neuron7xLab
"""Batch corpus adjudication + extraction accountability."""

from bsff.adjudication import (
    BatchItem,
    ProposedClaim,
    SourceDocument,
    TruthLedger,
    adjudicate_batch,
)

SOURCE_A = (
    "Decoding accuracy was 84% (p < 0.01). Clinicians should adopt the protocol. "
    "Consciousness is defined as integrated information."
)
SOURCE_B = "The premotor signal leads to motor output across trials in every subject tested."


def _item(source_id, text, claims):
    src = SourceDocument.from_text(source_id=source_id, kind="text", uri="", text=text)
    return BatchItem(source=src, claims=claims)


def test_batch_consolidates_corpus():
    items = [
        _item(
            "A",
            SOURCE_A,
            [
                ProposedClaim("a1", "Decoding accuracy was 84% (p < 0.01)", "human:y"),
                ProposedClaim("a2", "Clinicians should adopt the protocol", "human:y"),
                ProposedClaim(
                    "a3", "Consciousness is defined as integrated information", "human:y"
                ),
            ],
        ),
        _item(
            "B",
            SOURCE_B,
            [ProposedClaim("b1", "The premotor signal leads to motor output", "human:y")],
        ),
    ]
    report = adjudicate_batch(items)
    assert report["n_sources"] == 2
    assert report["n_claims"] == 4
    assert report["corpus_summary"]["dispositions"]["QUARANTINED_NORMATIVE"] == 1
    assert report["corpus_summary"]["anchor_failure_rate"] == 0.0
    assert report["artifact_sha256"]
    assert "TRUE" not in report["corpus_summary"]["dispositions"]


def test_batch_ledger_integrity(tmp_path):
    items = [
        _item("A", SOURCE_A, [ProposedClaim("a1", "Decoding accuracy was 84%", "human:y")]),
    ]
    led = TruthLedger(tmp_path / "led.jsonl")
    adjudicate_batch(items, ledger=led)
    assert led.verify()["ok"]


def test_batch_flags_fabricating_source_and_proposer():
    # Three claims, none of which occur in the source -> fabrication.
    fabricated = [
        ProposedClaim("f1", "the brain emits telepathy at gigahertz frequencies", "llm:rogue"),
        ProposedClaim("f2", "neurons run on quantum gravity microtubule collapse", "llm:rogue"),
        ProposedClaim("f3", "consciousness is stored in the pineal crystal lattice", "llm:rogue"),
    ]
    items = [_item("A", SOURCE_A, fabricated)]
    report = adjudicate_batch(items)

    assert report["corpus_summary"]["anchor_failure_rate"] == 1.0
    kinds = {f["kind"] for f in report["integrity_flags"]}
    assert "HIGH_UNANCHORED_RATE" in kinds
    assert "PROPOSER_FABRICATION" in kinds
    acct = report["proposer_accountability"]["llm:rogue"]
    assert acct["unanchored_rate"] == 1.0


def test_batch_proposer_low_falsifiability_flag():
    text = "X should be adopted. Y is defined as Z. The best approach is W to use everywhere."
    claims = [
        ProposedClaim("n1", "X should be adopted", "human:opinion"),
        ProposedClaim("n2", "Y is defined as Z", "human:opinion"),
        ProposedClaim("n3", "The best approach is W to use everywhere", "human:opinion"),
    ]
    report = adjudicate_batch([_item("A", text, claims)])
    kinds = {f["kind"] for f in report["integrity_flags"]}
    assert "PROPOSER_LOW_FALSIFIABILITY" in kinds
