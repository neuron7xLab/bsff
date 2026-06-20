# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (c) 2026 Yaroslav Vasylenko / neuron7xLab
"""Tests for the BSFF adjudication kernel."""

import json

import numpy as np
import pytest

from bsff.adjudication import (
    FalsifiabilityTier,
    ProposedClaim,
    SourceDocument,
    TruthLedger,
    adjudicate,
    adjudicate_claim,
    classify,
    lint_argument,
    locate,
)
from bsff.adjudication.argument import ArgumentStructure

SOURCE_TEXT = (
    "We recorded EEG from 32 channels at 250 Hz. "
    "Decoding accuracy was 84% and the effect was statistically significant (p < 0.01). "
    "If the axioms hold then the theorem is true, therefore the proof is complete. "
    "Consciousness is defined as integrated information. "
    "Clinicians should adopt this protocol. "
    "The system is fundamentally aware of the user's soul."
)


def make_source() -> SourceDocument:
    return SourceDocument.from_text(
        source_id="arXiv:2401.00001",
        kind="arxiv",
        uri="https://arxiv.org/abs/2401.00001",
        text=SOURCE_TEXT,
    )


# ----------------------------- source anchoring -----------------------------


def test_locate_exact():
    span = locate(SOURCE_TEXT, "Decoding accuracy was 84%")
    assert span is not None and span.method == "exact"
    assert SOURCE_TEXT[span.start : span.end] == "Decoding accuracy was 84%"


def test_locate_whitespace_normalized():
    span = locate(SOURCE_TEXT, "Decoding   accuracy\nwas 84%")
    assert span is not None and span.method == "whitespace_normalized"


def test_locate_absent_returns_none():
    assert locate(SOURCE_TEXT, "the brain is a quantum antenna for telepathy") is None


def test_source_provenance_tamper_detected():
    src = make_source()
    bad = SourceDocument(
        source_id=src.source_id,
        kind=src.kind,
        uri=src.uri,
        text=src.text + " tampered",
        retrieved_sha256=src.retrieved_sha256,
    )
    with pytest.raises(ValueError, match="provenance broken"):
        bad.validate()


# ----------------------------- proposed claims ------------------------------


def test_proposed_claim_rejects_unknown_field():
    with pytest.raises(ValueError, match="unknown claim field"):
        ProposedClaim.from_dict(
            {
                "claim_id": "c1",
                "quote": "Decoding accuracy was 84%",
                "proposer": "human:y",
                "bogus": 1,
            }
        )


def test_proposed_claim_rejects_short_quote():
    with pytest.raises(ValueError, match="anchored"):
        ProposedClaim.from_dict({"claim_id": "c1", "quote": "p<0.01", "proposer": "llm:x"})


# ----------------------------- classification -------------------------------


@pytest.mark.parametrize(
    "quote,tier",
    [
        (
            "the effect was statistically significant (p < 0.01)",
            FalsifiabilityTier.EMPIRICAL_STATISTICAL,
        ),
        ("Decoding accuracy was 84% across subjects", FalsifiabilityTier.EMPIRICAL_STATISTICAL),
        ("we observed that attention modulates the response", FalsifiabilityTier.EMPIRICAL_GENERAL),
        (
            "If the axioms hold then the theorem is true, therefore the proof is complete",
            FalsifiabilityTier.LOGICAL,
        ),
        ("Consciousness is defined as integrated information", FalsifiabilityTier.DEFINITIONAL),
        ("Clinicians should adopt this protocol for everyone", FalsifiabilityTier.NORMATIVE),
        (
            "The system is fundamentally aware of the user's soul",
            FalsifiabilityTier.NON_FALSIFIABLE,
        ),
    ],
)
def test_classify_tiers(quote, tier):
    assert classify(quote).tier is tier


def test_classify_carries_signals():
    c = classify("accuracy was 84% (p < 0.01)")
    assert c.signals  # auditable, non-empty


# ----------------------------- argument linting -----------------------------


def test_argument_structure_present():
    r = lint_argument("because the classifier exceeded chance, therefore it decodes intent")
    assert r.structure is ArgumentStructure.STRUCTURE_PRESENT


def test_argument_structure_incomplete():
    r = lint_argument("therefore the device decodes intent")
    assert r.structure is ArgumentStructure.STRUCTURE_INCOMPLETE


def test_argument_no_structure():
    r = lint_argument("the device decodes intent")
    assert r.structure is ArgumentStructure.NO_ARGUMENT_STRUCTURE


# ----------------------------- ledger ---------------------------------------


def test_ledger_append_and_verify(tmp_path):
    led = TruthLedger(tmp_path / "ledger.jsonl")
    led.append({"a": 1})
    led.append({"b": 2})
    result = led.verify()
    assert result["ok"] and result["length"] == 2


def test_ledger_tamper_breaks_chain(tmp_path):
    path = tmp_path / "ledger.jsonl"
    led = TruthLedger(path)
    led.append({"verdict": "REFUTED"})
    led.append({"verdict": "UNSUPPORTED"})
    lines = path.read_text(encoding="utf-8").splitlines()
    entry = json.loads(lines[0])
    entry["payload"]["verdict"] = "SURVIVED"  # silently soften a recorded verdict
    lines[0] = json.dumps(entry, ensure_ascii=False, sort_keys=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    result = led.verify()
    assert not result["ok"] and result["broken_at"] == 0


# ----------------------------- routing --------------------------------------


def test_unanchored_claim_quarantined():
    src = make_source()
    claim = ProposedClaim(
        claim_id="c-fab", quote="the brain emits measurable telepathy fields", proposer="llm:x"
    )
    rec = adjudicate_claim(src, claim)
    assert rec.anchored is False and rec.disposition == "QUARANTINED_UNANCHORED"


def test_normative_claim_quarantined():
    src = make_source()
    claim = ProposedClaim(
        claim_id="c-norm", quote="Clinicians should adopt this protocol", proposer="human:y"
    )
    rec = adjudicate_claim(src, claim)
    assert rec.disposition == "QUARANTINED_NORMATIVE"


def test_empirical_statistical_without_data_is_pending():
    src = make_source()
    claim = ProposedClaim(
        claim_id="c-emp",
        quote="Decoding accuracy was 84% and the effect was statistically significant (p < 0.01)",
        proposer="human:y",
    )
    rec = adjudicate_claim(src, claim)
    assert rec.tier == "EMPIRICAL_STATISTICAL"
    assert rec.disposition == "PENDING_EVIDENCE"


def test_logical_claim_routed_to_argument():
    src = make_source()
    claim = ProposedClaim(
        claim_id="c-log",
        quote="If the axioms hold then the theorem is true, therefore the proof is complete",
        proposer="human:y",
    )
    rec = adjudicate_claim(src, claim)
    assert rec.tier == "LOGICAL"
    assert rec.disposition == "LOGICAL_STRUCTURE_PRESENT"


# ----------------------------- full report ----------------------------------


def test_adjudicate_report_is_self_verifying(tmp_path):
    src = make_source()
    claims = [
        ProposedClaim(claim_id="c1", quote="Decoding accuracy was 84%", proposer="human:y"),
        ProposedClaim(
            claim_id="c2", quote="Clinicians should adopt this protocol", proposer="human:y"
        ),
    ]
    led = TruthLedger(tmp_path / "led.jsonl")
    report = adjudicate(src, claims, ledger=led)
    assert report["n_claims"] == 2
    assert report["artifact_sha256"]
    assert led.verify()["ok"]
    # never promotes anything to "true"
    dispositions = {r["disposition"] for r in report["records"]}
    assert "TRUE" not in dispositions
    assert all(r.get("ledger") for r in report["records"])


def test_empirical_statistical_with_real_signal(tmp_path):
    from bsff.synthetic import henon_series

    sig = henon_series(n_samples=512, seed=11)
    sig_path = tmp_path / "sig.npy"
    np.save(sig_path, sig)
    spec = {
        "claim_id": "henon-nonlinearity",
        "signal_type": "EEG",
        "task_type": "nonlinear_structure",
        "sampling_rate_hz": 250.0,
        "n_channels": 1,
        "n_samples": 512,
        "statistic": "lagged_quadratic",
        "surrogate_count": 19,
    }
    spec_path = tmp_path / "claim.json"
    spec_path.write_text(json.dumps(spec), encoding="utf-8")

    src = SourceDocument.from_text(
        source_id="local:henon",
        kind="text",
        uri="",
        text="The Henon signal exhibits significant nonlinear structure (p < 0.05).",
    )
    claim = ProposedClaim(
        claim_id="henon-nonlinearity",
        quote="significant nonlinear structure (p < 0.05)",
        proposer="human:y",
        operationalization={
            "claim_spec": str(spec_path),
            "signal": str(sig_path),
            "policy": "smoke",
        },
    )
    rec = adjudicate_claim(src, claim)
    assert rec.tier == "EMPIRICAL_STATISTICAL"
    assert rec.disposition in {"SURVIVED_FALSIFICATION", "REFUTED", "UNSUPPORTED"}
    assert "case_artifact_sha256" in rec.evidence
