# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (c) 2026 Yaroslav Vasylenko / neuron7xLab
"""Tests for arXiv source ingestion (offline, injected fetcher)."""

import pytest

from bsff.adjudication import (
    ProposedClaim,
    adjudicate_claim,
    fetch_arxiv,
    normalize_arxiv_id,
    parse_arxiv_atom,
)
from bsff.adjudication.ingest import _ARXIV_API

_ATOM_OK = b"""<?xml version="1.0" encoding="UTF-8"?>
<feed xmlns="http://www.w3.org/2005/Atom">
  <entry>
    <id>http://arxiv.org/abs/1706.03762v5</id>
    <title>Attention Is All You Need</title>
    <summary>The dominant sequence transduction models are based on complex recurrent
    or convolutional neural networks. We propose the Transformer, based solely on
    attention mechanisms. Our model achieves 28.4 BLEU on the WMT 2014 task.</summary>
  </entry>
</feed>"""

_ATOM_ERROR = b"""<?xml version="1.0" encoding="UTF-8"?>
<feed xmlns="http://www.w3.org/2005/Atom">
  <entry>
    <id>http://arxiv.org/api/errors</id>
    <title>Error</title>
    <summary></summary>
  </entry>
</feed>"""

_ATOM_EMPTY = b"""<?xml version="1.0" encoding="UTF-8"?>
<feed xmlns="http://www.w3.org/2005/Atom"></feed>"""


def test_normalize_arxiv_id_strips_prefix():
    assert normalize_arxiv_id("arXiv:1706.03762") == "1706.03762"
    assert normalize_arxiv_id("  1706.03762v5 ") == "1706.03762v5"


def test_normalize_arxiv_id_rejects_empty():
    with pytest.raises(ValueError, match="non-empty"):
        normalize_arxiv_id("arXiv:")


def test_parse_arxiv_atom_builds_provenanced_source():
    src = parse_arxiv_atom(_ATOM_OK, "1706.03762")
    src.validate()  # provenance hash must match assembled text
    assert src.source_id == "arXiv:1706.03762"
    assert src.kind == "arxiv"
    assert src.uri == "http://arxiv.org/abs/1706.03762v5"
    assert src.text.startswith("Attention Is All You Need")
    assert "28.4 BLEU" in src.text


def test_parse_arxiv_atom_error_entry_rejected():
    with pytest.raises(ValueError, match="no abstract"):
        parse_arxiv_atom(_ATOM_ERROR, "0000.00000")


def test_parse_arxiv_atom_no_entry_rejected():
    with pytest.raises(ValueError, match="no entry"):
        parse_arxiv_atom(_ATOM_EMPTY, "0000.00000")


def test_parse_arxiv_atom_bad_xml_rejected():
    with pytest.raises(ValueError, match="not valid XML"):
        parse_arxiv_atom(b"<not xml", "x")


def test_fetch_arxiv_uses_injected_fetcher():
    seen = {}

    def fake_fetch(url: str) -> bytes:
        seen["url"] = url
        return _ATOM_OK

    src = fetch_arxiv("arXiv:1706.03762", fetch=fake_fetch)
    assert seen["url"] == _ARXIV_API.format(id="1706.03762")
    assert src.source_id == "arXiv:1706.03762"


def test_fetch_arxiv_empty_response_rejected():
    with pytest.raises(ValueError, match="empty response"):
        fetch_arxiv("1706.03762", fetch=lambda url: b"")


def test_ingested_source_drives_adjudication():
    src = fetch_arxiv("1706.03762", fetch=lambda url: _ATOM_OK)
    # a claim quoting the abstract verbatim anchors and classifies as empirical-statistical
    claim = ProposedClaim(
        claim_id="bleu",
        quote="Our model achieves 28.4 BLEU on the WMT 2014 task",
        proposer="human:y",
    )
    rec = adjudicate_claim(src, claim)
    assert rec.anchored is True
    assert rec.tier == "EMPIRICAL_STATISTICAL"
    assert rec.disposition == "PENDING_EVIDENCE"  # no data attached -> honestly pending

    # a fabricated claim the abstract does not contain is quarantined
    fake = ProposedClaim(
        claim_id="fake", quote="the Transformer was trained on Martian telemetry", proposer="llm:x"
    )
    assert adjudicate_claim(src, fake).disposition == "QUARANTINED_UNANCHORED"
