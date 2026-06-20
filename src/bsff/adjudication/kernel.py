# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (c) 2026 Yaroslav Vasylenko / neuron7xLab
"""The adjudication kernel: anchor -> classify -> route -> record.

This is the spine of BSFF as a publication-claim engine. Each proposed claim is
anchored to its source (or quarantined as fabricated), classified by
falsifiability tier, routed to the matching adjudicator, and turned into an
auditable record. A claim is never promoted to "true": the strongest disposition
an empirical claim can earn is ``SURVIVED_FALSIFICATION`` under stated
conditions, and only when real data drove the signal-falsification battery.
Everything else is pending evidence, structural-only, or quarantined.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from .. import __version__
from ..evidence import stable_sha256
from .argument import ArgumentStructure, lint_argument
from .claim import AnchoredClaim, ProposedClaim
from .falsifiability import Classification, FalsifiabilityTier, classify
from .ledger import TruthLedger
from .source import SourceDocument, locate

REPORT_SCHEMA = "bsff.adjudication/v1"

# Empirical statistical claims with attached data route here lazily to avoid a
# hard import cost when no claim needs the signal-falsification battery.


def _run_empirical_statistical(op: dict[str, Any]) -> dict[str, Any]:
    from ..case import run_case  # local import: heavy numerical stack

    required = ("claim_spec", "signal")
    missing = [k for k in required if not op.get(k)]
    if missing:
        return {
            "disposition": "PENDING_EVIDENCE",
            "evidence": {
                "reason": "empirical-statistical claim lacks data to run the battery",
                "required": [f"operationalization.{k}" for k in missing],
            },
        }
    dossier = run_case(
        op["claim_spec"],
        op["signal"],
        policy=op.get("policy", "strict"),
        seed=int(op.get("seed", 123)),
    )
    verdict = str(dossier["verdict"]["verdict"])
    disposition = {
        "SURVIVED": "SURVIVED_FALSIFICATION",
        "REFUTED": "REFUTED",
        "UNSUPPORTED": "UNSUPPORTED",
    }.get(verdict, "UNSUPPORTED")
    return {
        "disposition": disposition,
        "evidence": {
            "engine_verdict": verdict,
            "p_value": dossier["verdict"].get("p_value"),
            "case_artifact_sha256": dossier["artifact_sha256"],
            "signal_sha256": dossier["signal_provenance"]["sha256"],
            "caveats": dossier.get("caveats", []),
        },
    }


def _route(claim: AnchoredClaim, classification: Classification) -> dict[str, Any]:
    tier = classification.tier
    op = claim.claim.operationalization or {}

    if tier is FalsifiabilityTier.EMPIRICAL_STATISTICAL:
        return _run_empirical_statistical(op)

    if tier is FalsifiabilityTier.EMPIRICAL_GENERAL:
        return {
            "disposition": "PENDING_EVIDENCE",
            "evidence": {
                "reason": "empirical claim is qualitative; requires operationalization into a "
                "ClaimSpec + signal before it can be falsified",
                "required": ["operationalization.claim_spec", "operationalization.signal"],
            },
        }

    if tier is FalsifiabilityTier.LOGICAL:
        report = lint_argument(claim.claim.quote)
        disposition = {
            ArgumentStructure.STRUCTURE_PRESENT: "LOGICAL_STRUCTURE_PRESENT",
            ArgumentStructure.STRUCTURE_INCOMPLETE: "LOGICAL_STRUCTURE_INCOMPLETE",
            ArgumentStructure.NO_ARGUMENT_STRUCTURE: "NOT_AN_ARGUMENT",
        }[report.structure]
        return {"disposition": disposition, "evidence": {"argument": report.to_dict()}}

    quarantine = {
        FalsifiabilityTier.DEFINITIONAL: "QUARANTINED_DEFINITIONAL",
        FalsifiabilityTier.NORMATIVE: "QUARANTINED_NORMATIVE",
        FalsifiabilityTier.NON_FALSIFIABLE: "QUARANTINED_NON_FALSIFIABLE",
    }[tier]
    return {
        "disposition": quarantine,
        "evidence": {"reason": f"tier {tier.value} is not empirically falsifiable"},
    }


@dataclass(frozen=True)
class AdjudicationRecord:
    claim_id: str
    source_id: str
    proposer: str
    anchored: bool
    disposition: str
    tier: str
    classification: dict[str, Any]
    anchor: dict[str, Any] | None
    evidence: dict[str, Any]

    def to_dict(self) -> dict[str, Any]:
        return {
            "claim_id": self.claim_id,
            "source_id": self.source_id,
            "proposer": self.proposer,
            "anchored": self.anchored,
            "disposition": self.disposition,
            "tier": self.tier,
            "classification": self.classification,
            "anchor": self.anchor,
            "evidence": self.evidence,
        }


def adjudicate_claim(source: SourceDocument, claim: ProposedClaim) -> AdjudicationRecord:
    """Anchor, classify, and route a single claim into an adjudication record."""
    claim.validate()
    span = locate(source.text, claim.quote)
    if span is None:
        return AdjudicationRecord(
            claim_id=claim.claim_id,
            source_id=source.source_id,
            proposer=claim.proposer,
            anchored=False,
            disposition="QUARANTINED_UNANCHORED",
            tier="N/A",
            classification={},
            anchor=None,
            evidence={
                "reason": "quote not found in source text; refusing to adjudicate a "
                "claim the source does not contain"
            },
        )

    anchored = AnchoredClaim(claim=claim, source_id=source.source_id, span=span)
    classification = classify(claim.quote)
    routed = _route(anchored, classification)
    return AdjudicationRecord(
        claim_id=claim.claim_id,
        source_id=source.source_id,
        proposer=claim.proposer,
        anchored=True,
        disposition=routed["disposition"],
        tier=classification.tier.value,
        classification=classification.to_dict(),
        anchor=span.to_dict(),
        evidence=routed["evidence"],
    )


def adjudicate(
    source: SourceDocument,
    claims: list[ProposedClaim],
    *,
    ledger: TruthLedger | None = None,
) -> dict[str, Any]:
    """Adjudicate every claim against one source; emit a self-verifying report."""
    source.validate()
    records: list[dict[str, Any]] = []
    for claim in claims:
        record = adjudicate_claim(source, claim)
        record_dict = record.to_dict()
        if ledger is not None:
            entry = ledger.append({"source": source.provenance(), "record": record_dict})
            record_dict["ledger"] = {"seq": entry["seq"], "record_hash": entry["record_hash"]}
        records.append(record_dict)

    summary: dict[str, int] = {}
    for record in records:
        summary[record["disposition"]] = summary.get(record["disposition"], 0) + 1

    report: dict[str, Any] = {
        "schema": REPORT_SCHEMA,
        "tool": "bsff",
        "tool_version": __version__,
        "generated_by": "bsff adjudicate",
        "source": source.provenance(),
        "n_claims": len(records),
        "summary": summary,
        "records": records,
    }
    report["artifact_sha256"] = stable_sha256(report)
    return report
