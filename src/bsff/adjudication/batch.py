# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (c) 2026 Yaroslav Vasylenko / neuron7xLab
"""Batch adjudication across a corpus of sources, with extraction accountability.

Running BSFF against one paper is a spot check; running it against a corpus is the
intended use. :func:`adjudicate_batch` adjudicates many sources into one shared
truth ledger and consolidates the result — but it also turns the lens back on the
*extraction process*. A source whose claims are mostly unanchored, or a proposer
whose proposals are mostly fabricated or quarantined, is flagged: the integrity
of the claims is no stronger than the integrity of whoever proposed them, and a
corpus report that hid that would be lying by omission.
"""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass, field
from typing import Any

from .. import __version__
from ..evidence import stable_sha256
from .claim import ProposedClaim
from .kernel import adjudicate
from .ledger import TruthLedger
from .source import SourceDocument

BATCH_SCHEMA = "bsff.adjudication.batch/v1"

# A source/proposer is flagged once it has enough claims to be meaningful and at
# least half of them failed to anchor (likely fabrication) or were quarantined.
_MIN_CLAIMS_FOR_FLAG = 3
_UNANCHORED_FLAG_RATE = 0.5
_QUARANTINE_FLAG_RATE = 0.5


@dataclass(frozen=True)
class BatchItem:
    source: SourceDocument
    claims: list[ProposedClaim] = field(default_factory=list)


def _rate(n: int, total: int) -> float:
    return float(n / total) if total else 0.0


def _is_unanchored(record: dict[str, Any]) -> bool:
    return bool(record["disposition"] == "QUARANTINED_UNANCHORED")


def _is_quarantined(record: dict[str, Any]) -> bool:
    return bool(record["disposition"].startswith("QUARANTINED_"))


def adjudicate_batch(
    items: list[BatchItem],
    *,
    ledger: TruthLedger | None = None,
) -> dict[str, Any]:
    """Adjudicate a corpus and consolidate dispositions plus accountability."""
    source_reports: list[dict[str, Any]] = []
    all_records: list[dict[str, Any]] = []
    per_source: list[dict[str, Any]] = []
    proposer_stats: dict[str, Counter[str]] = {}

    for item in items:
        report = adjudicate(item.source, item.claims, ledger=ledger)
        source_reports.append(report)
        records = report["records"]
        all_records.extend(records)

        n = len(records)
        unanchored = sum(_is_unanchored(r) for r in records)
        quarantined = sum(_is_quarantined(r) for r in records)
        per_source.append(
            {
                "source_id": item.source.source_id,
                "n_claims": n,
                "unanchored": unanchored,
                "unanchored_rate": _rate(unanchored, n),
                "quarantined": quarantined,
                "dispositions": dict(Counter(r["disposition"] for r in records)),
            }
        )

        for r in records:
            stats = proposer_stats.setdefault(r["proposer"], Counter())
            stats["proposed"] += 1
            if _is_unanchored(r):
                stats["unanchored"] += 1
            if _is_quarantined(r):
                stats["quarantined"] += 1

    total_claims = len(all_records)
    total_unanchored = sum(_is_unanchored(r) for r in all_records)

    integrity_flags: list[dict[str, Any]] = []
    for s in per_source:
        if s["n_claims"] >= _MIN_CLAIMS_FOR_FLAG and s["unanchored_rate"] >= _UNANCHORED_FLAG_RATE:
            integrity_flags.append(
                {
                    "kind": "HIGH_UNANCHORED_RATE",
                    "subject": s["source_id"],
                    "rate": s["unanchored_rate"],
                    "detail": "most claims do not occur in the source; likely fabricated extraction",
                }
            )
    proposer_accountability: dict[str, Any] = {}
    for proposer, stats in proposer_stats.items():
        proposed = stats["proposed"]
        unanchored_rate = _rate(stats["unanchored"], proposed)
        quarantine_rate = _rate(stats["quarantined"], proposed)
        proposer_accountability[proposer] = {
            "proposed": proposed,
            "unanchored": stats["unanchored"],
            "unanchored_rate": unanchored_rate,
            "quarantined": stats["quarantined"],
            "quarantine_rate": quarantine_rate,
        }
        if proposed >= _MIN_CLAIMS_FOR_FLAG and unanchored_rate >= _UNANCHORED_FLAG_RATE:
            integrity_flags.append(
                {
                    "kind": "PROPOSER_FABRICATION",
                    "subject": proposer,
                    "rate": unanchored_rate,
                    "detail": "proposer's claims mostly fail to anchor in their sources",
                }
            )
        elif proposed >= _MIN_CLAIMS_FOR_FLAG and quarantine_rate >= _QUARANTINE_FLAG_RATE:
            integrity_flags.append(
                {
                    "kind": "PROPOSER_LOW_FALSIFIABILITY",
                    "subject": proposer,
                    "rate": quarantine_rate,
                    "detail": "proposer's claims are mostly non-falsifiable/quarantined",
                }
            )

    batch_report: dict[str, Any] = {
        "schema": BATCH_SCHEMA,
        "tool": "bsff",
        "tool_version": __version__,
        "generated_by": "bsff adjudicate-batch",
        "n_sources": len(items),
        "n_claims": total_claims,
        "corpus_summary": {
            "dispositions": dict(Counter(r["disposition"] for r in all_records)),
            "tiers": dict(Counter(r["tier"] for r in all_records)),
            "anchor_failure_rate": _rate(total_unanchored, total_claims),
        },
        "per_source": per_source,
        "proposer_accountability": proposer_accountability,
        "integrity_flags": integrity_flags,
        "sources": [r["source"] for r in source_reports],
    }
    batch_report["artifact_sha256"] = stable_sha256(batch_report)
    return batch_report
