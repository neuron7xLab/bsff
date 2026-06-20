# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (c) 2026 Yaroslav Vasylenko / neuron7xLab
"""Proposed and anchored claims.

A :class:`ProposedClaim` is an assertion *attributed to a source*, together with
who proposed extracting it. The proposer may be a person or an LLM, but the
proposer never adjudicates: its only power is to point at a verbatim span. An
:class:`AnchoredClaim` is a proposed claim that has been confirmed to occur in
its source; only anchored claims reach the routing layer.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from .source import Span

_MIN_QUOTE_CHARS = 12


@dataclass(frozen=True)
class ProposedClaim:
    """One assertion attributed to a source, awaiting anchoring + adjudication."""

    claim_id: str
    quote: str
    proposer: str
    operationalization: dict[str, Any] | None = None
    note: str = ""

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> ProposedClaim:
        allowed = {"claim_id", "quote", "proposer", "operationalization", "note"}
        unknown = set(data) - allowed
        if unknown:
            raise ValueError(
                f"unknown claim field(s): {sorted(unknown)}; allowed: {sorted(allowed)}"
            )
        claim = cls(
            claim_id=str(data["claim_id"]),
            quote=str(data["quote"]),
            proposer=str(data["proposer"]),
            operationalization=data.get("operationalization"),
            note=str(data.get("note", "")),
        )
        claim.validate()
        return claim

    def validate(self) -> None:
        if not self.claim_id:
            raise ValueError("claim_id must be non-empty")
        if len(self.quote.strip()) < _MIN_QUOTE_CHARS:
            raise ValueError(
                f"quote must be >= {_MIN_QUOTE_CHARS} chars; a fragment cannot be anchored"
            )
        if not self.proposer:
            raise ValueError("proposer must be non-empty (who proposed this claim: human/llm id)")
        if self.operationalization is not None and not isinstance(self.operationalization, dict):
            raise ValueError("operationalization must be a mapping when provided")

    def to_dict(self) -> dict[str, Any]:
        return {
            "claim_id": self.claim_id,
            "quote": self.quote,
            "proposer": self.proposer,
            "operationalization": self.operationalization,
            "note": self.note,
        }


@dataclass(frozen=True)
class AnchoredClaim:
    """A proposed claim confirmed to occur verbatim in its source."""

    claim: ProposedClaim
    source_id: str
    span: Span
    fields: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "claim": self.claim.to_dict(),
            "source_id": self.source_id,
            "span": self.span.to_dict(),
        }
