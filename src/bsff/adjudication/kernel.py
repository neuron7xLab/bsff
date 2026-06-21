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
from pathlib import Path
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


def _load_series(path: str) -> Any:
    import numpy as np  # local import: heavy numerical stack

    p = Path(path)
    if not p.is_file():
        raise FileNotFoundError(f"series file not found: {path}")
    suffix = p.suffix.lower()
    if suffix == ".npy":
        array = np.load(p)
    elif suffix in (".csv", ".tsv", ".txt"):
        array = np.loadtxt(p, delimiter="\t" if suffix == ".tsv" else ",")
    else:
        raise ValueError(f"unsupported series format '{suffix}'")
    array = np.asarray(array, dtype=float).squeeze()
    if array.ndim != 1:
        raise ValueError(f"series must be 1-D after squeeze, got {array.ndim}-D: {path}")
    if not np.all(np.isfinite(array)):
        raise ValueError(f"series contains non-finite values: {path}")
    return array


def _run_causal_te(op: dict[str, Any]) -> dict[str, Any]:
    from ..transfer_entropy import transfer_entropy_test  # local import: heavy numerical stack

    missing = [k for k in ("source", "target") if not op.get(k)]
    if missing:
        return {
            "disposition": "PENDING_EVIDENCE",
            "evidence": {
                "reason": "causal claim lacks the series needed for a transfer-entropy test",
                "required": [f"operationalization.{k}" for k in missing],
            },
        }
    source = _load_series(op["source"])
    target = _load_series(op["target"])
    conditions = [_load_series(c) for c in op.get("conditions", [])]
    result = transfer_entropy_test(
        source,
        target,
        conditions=conditions or None,
        k=int(op.get("k", 2)),
        cond_lag=int(op.get("cond_lag", 3)),
        n_surrogates=int(op.get("n_surrogates", 199)),
        alpha=float(op.get("alpha", 0.05)),
        seed=int(op.get("seed", 123)),
    )
    evidence = result.to_dict()
    caveats: list[str] = []
    if result.direction == "source->target":
        # Pairwise TE cannot rule out a common drive (measured FPR ~1.0); an
        # unconditioned survival is the weaker disposition by design.
        if conditions:
            disposition = "DIRECTED_COUPLING_SURVIVED"
        else:
            disposition = "DIRECTED_COUPLING_UNCONDITIONED"
            caveats.append(
                "No conditioning series supplied: pairwise transfer entropy cannot "
                "distinguish a direct coupling from a common drive. Treat as provisional."
            )
    elif result.direction == "target->source":
        disposition = "REFUTED"
        caveats.append(
            "Directed coupling runs target->source, contradicting the claimed direction."
        )
    elif result.direction == "bidirectional":
        disposition = "UNSUPPORTED"
        caveats.append(
            "Coupling significant in both directions; the claimed direction is not isolable."
        )
    else:
        disposition = "UNSUPPORTED"
        caveats.append(
            "No directed coupling detected; the causal claim is not supported by the data."
        )
    evidence["caveats"] = caveats
    return {"disposition": disposition, "evidence": evidence}


def _route(claim: AnchoredClaim, classification: Classification) -> dict[str, Any]:
    tier = classification.tier
    op = claim.claim.operationalization or {}

    # A transfer-entropy operationalization routes any empirical claim to the
    # directed-causality test regardless of statistical/qualitative wording.
    if op.get("test") == "transfer_entropy" and tier in (
        FalsifiabilityTier.EMPIRICAL_STATISTICAL,
        FalsifiabilityTier.EMPIRICAL_GENERAL,
    ):
        return _run_causal_te(op)

    if tier is FalsifiabilityTier.EMPIRICAL_STATISTICAL:
        return _run_empirical_statistical(op)

    if tier is FalsifiabilityTier.EMPIRICAL_GENERAL:
        return {
            "disposition": "PENDING_EVIDENCE",
            "evidence": {
                "reason": "empirical claim is qualitative; supply a ClaimSpec + signal, or a "
                "transfer_entropy operationalization (source/target series), to falsify it",
                "required": [
                    "operationalization.claim_spec + signal",
                    "or operationalization.test=transfer_entropy",
                ],
            },
        }

    if tier is FalsifiabilityTier.LOGICAL:
        report = lint_argument(claim.claim.quote)
        disposition = {
            # ARGUMENT_STRUCTURE_DETECTED, not LOGICAL_STRUCTURE_PRESENT: this route
            # detects that a premise→conclusion structure exists, NOT that the
            # argument is sound. The label must not imply established truth.
            ArgumentStructure.STRUCTURE_PRESENT: "ARGUMENT_STRUCTURE_DETECTED",
            ArgumentStructure.STRUCTURE_INCOMPLETE: "ARGUMENT_STRUCTURE_INCOMPLETE",
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
