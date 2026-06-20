# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (c) 2026 Yaroslav Vasylenko / neuron7xLab
"""BSFF adjudication kernel: falsify the claims of an external source, fail-closed.

Turns BSFF from a signal falsifier into a publication-claim engine. A source is
ingested with byte-level provenance; each proposed claim is anchored to verbatim
text (or quarantined as fabricated), classified by falsifiability tier, routed to
the matching adjudicator, and chained into an append-only truth ledger. No claim
is ever promoted to "true".
"""

from __future__ import annotations

from .argument import ArgumentReport, ArgumentStructure, lint_argument
from .claim import AnchoredClaim, ProposedClaim
from .falsifiability import Classification, FalsifiabilityTier, classify
from .kernel import AdjudicationRecord, adjudicate, adjudicate_claim
from .ledger import GENESIS_HASH, TruthLedger
from .source import SourceDocument, Span, locate

__all__ = [
    "GENESIS_HASH",
    "AdjudicationRecord",
    "AnchoredClaim",
    "ArgumentReport",
    "ArgumentStructure",
    "Classification",
    "FalsifiabilityTier",
    "ProposedClaim",
    "SourceDocument",
    "Span",
    "TruthLedger",
    "adjudicate",
    "adjudicate_claim",
    "classify",
    "lint_argument",
    "locate",
]
