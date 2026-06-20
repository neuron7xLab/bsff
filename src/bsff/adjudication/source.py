# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (c) 2026 Yaroslav Vasylenko / neuron7xLab
"""Source documents and verbatim claim anchoring.

A claim entering the adjudication kernel must be tied to text that actually
exists in its source. The proposer of a claim (a human, or an LLM acting only
as a parser) can therefore never inject a sentence the source does not contain:
:func:`locate` returns ``None`` for any quote absent from the document, and the
kernel fail-closes that claim to ``QUARANTINED/UNANCHORED`` rather than judging
it. This is the anti-fabrication floor of the whole system.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any

from ..validation import sha256_bytes

ALLOWED_KINDS = ("arxiv", "doi", "url", "pdf", "text")
_WS = re.compile(r"\s+")


@dataclass(frozen=True)
class Span:
    """Character offsets of a located quote within a source's original text."""

    start: int
    end: int
    method: str  # "exact" | "whitespace_normalized"
    matched_text: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "start": self.start,
            "end": self.end,
            "method": self.method,
            "matched_text": self.matched_text,
        }


@dataclass(frozen=True)
class SourceDocument:
    """A retrieved source with byte-level provenance over its extracted text."""

    source_id: str
    kind: str
    uri: str
    text: str
    retrieved_sha256: str

    @classmethod
    def from_text(cls, source_id: str, kind: str, uri: str, text: str) -> SourceDocument:
        digest = sha256_bytes(text.encode("utf-8"))
        doc = cls(source_id=source_id, kind=kind, uri=uri, text=text, retrieved_sha256=digest)
        doc.validate()
        return doc

    def validate(self) -> None:
        if not self.source_id:
            raise ValueError("source_id must be non-empty")
        if self.kind not in ALLOWED_KINDS:
            raise ValueError(f"unsupported source kind '{self.kind}'; expected {ALLOWED_KINDS}")
        if not self.text.strip():
            raise ValueError("source text must be non-empty")
        if self.retrieved_sha256 != sha256_bytes(self.text.encode("utf-8")):
            raise ValueError("retrieved_sha256 does not match source text; provenance broken")

    def provenance(self) -> dict[str, Any]:
        return {
            "source_id": self.source_id,
            "kind": self.kind,
            "uri": self.uri,
            "retrieved_sha256": self.retrieved_sha256,
            "text_length": len(self.text),
        }


def locate(text: str, quote: str) -> Span | None:
    """Return the :class:`Span` of ``quote`` inside ``text``, or ``None``.

    An exact substring match is preferred. Failing that, a whitespace-tolerant,
    case-insensitive match is attempted so a quote copied across line wraps still
    anchors with real offsets into the original text. A quote that matches under
    neither test is treated as absent — the caller must refuse to adjudicate it.
    """
    if not quote.strip():
        return None
    idx = text.find(quote)
    if idx != -1:
        return Span(start=idx, end=idx + len(quote), method="exact", matched_text=quote)

    tokens = [re.escape(tok) for tok in quote.split()]
    if not tokens:
        return None
    pattern = re.compile(r"\s+".join(tokens), re.IGNORECASE)
    match = pattern.search(text)
    if match is None:
        return None
    return Span(
        start=match.start(),
        end=match.end(),
        method="whitespace_normalized",
        matched_text=match.group(0),
    )
