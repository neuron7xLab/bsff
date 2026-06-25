# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (c) 2026 Yaroslav Vasylenko / neuron7xLab
"""The executable constitution of BSFF — its axioms, made machine-checkable.

A falsification engine that only *claims* to be deterministic, fail-closed, and
honest is just another assertion. These tests turn those claims into invariants
that CI enforces on every commit:

  INV-1 DETERMINISM   same (input, seed) -> byte-identical verdict.
  INV-2 NO-TRUE       no path can promote a claim to "true"/"proven".
  INV-3 FAIL-CLOSED   degraded evidence can only demote a verdict, never upgrade.
  INV-4 ANCHOR        a quote absent from its source is always quarantined.
  INV-5 PROVENANCE    every report's artifact hash recomputes from its content.
  INV-6 RAW-GUARD     a non-signal (labels/features) is refused, not adjudicated.

If any axiom is ever violated by a code change, one of these fails. That is the
difference between a principle and a guarantee.
"""

from __future__ import annotations

import numpy as np
import pytest

from bsff.adjudication import (
    ProposedClaim,
    SourceDocument,
    TruthLedger,
    adjudicate,
    adjudicate_batch,
    classify,
)
from bsff.adjudication.batch import BatchItem
from bsff.datasets import adjudicate_dataset, load_series, materialize
from bsff.evidence import stable_sha256
from bsff.schemas import ClaimSpec
from bsff.synthetic import henon_series
from bsff.transfer_entropy import gaussian_transfer_entropy, transfer_entropy_test
from bsff.verdict_engine import evaluate_claim

_TRUE_WORDS = {"TRUE", "PROVEN", "PROVED", "CONFIRMED_TRUE", "VALIDATED_TRUE"}


def _source():
    return SourceDocument.from_text(
        source_id="inv",
        kind="text",
        uri="",
        text=(
            "Decoding accuracy was 84% (p < 0.01). Clinicians should adopt it. "
            "Consciousness is defined as integrated information."
        ),
    )


# ----------------------------- INV-1 DETERMINISM ----------------------------


def test_inv1_evaluate_claim_is_deterministic():
    sig = henon_series(768, seed=11)
    spec = ClaimSpec(
        claim_id="d",
        signal_type="EEG",
        task_type="nonlinear_structure",
        sampling_rate_hz=250.0,
        n_channels=1,
        n_samples=768,
        statistic="lagged_quadratic",
        surrogate_count=49,
    )
    a = evaluate_claim(spec, sig, seed=7).to_dict()
    b = evaluate_claim(spec, sig, seed=7).to_dict()
    assert stable_sha256(a) == stable_sha256(b)


def test_inv1_transfer_entropy_is_deterministic():
    x = henon_series(512, seed=1)
    y = henon_series(512, seed=2)
    a = transfer_entropy_test(x, y, k=2, n_surrogates=49, seed=3).to_dict()
    b = transfer_entropy_test(x, y, k=2, n_surrogates=49, seed=3).to_dict()
    assert a == b
    assert gaussian_transfer_entropy(x, y) == gaussian_transfer_entropy(x, y)


def test_inv1_adjudicate_report_is_byte_identical():
    src = _source()
    claims = [ProposedClaim("c1", "Decoding accuracy was 84% (p < 0.01)", "h")]
    r1 = adjudicate(src, claims)
    r2 = adjudicate(src, claims)
    assert r1 == r2
    assert r1["artifact_sha256"] == r2["artifact_sha256"]


# ------------------------------- INV-2 NO-TRUE ------------------------------


def test_inv2_no_disposition_is_true():
    src = _source()
    claims = [
        ProposedClaim("c1", "Decoding accuracy was 84% (p < 0.01)", "h"),
        ProposedClaim("c2", "Clinicians should adopt it", "h"),
        ProposedClaim("c3", "Consciousness is defined as integrated information", "h"),
        ProposedClaim("c4", "a sentence never written in the source", "llm"),
    ]
    report = adjudicate(src, claims)
    for rec in report["records"]:
        assert rec["disposition"].upper() not in _TRUE_WORDS
        assert "TRUE" not in rec["disposition"].upper()


def test_inv2_dataset_verdicts_are_never_true():
    for name in ("nonlinear_effect", "nonlinear_null"):
        spec, data = materialize(name)
        v = adjudicate_dataset(spec, data, n_surrogates=49)
        assert str(v["verdict"]).upper() not in _TRUE_WORDS


# ----------------------------- INV-3 FAIL-CLOSED ----------------------------


def test_inv3_leakage_can_only_demote_to_refuted():
    # a leakage flag must short-circuit to REFUTED — never SURVIVED.
    spec = ClaimSpec(
        claim_id="lk",
        signal_type="EEG",
        task_type="nonlinear_structure",
        sampling_rate_hz=250.0,
        n_channels=1,
        n_samples=768,
        statistic="lagged_quadratic",
        surrogate_count=49,
    )
    v = evaluate_claim(
        spec, henon_series(768, seed=11), seed=7, leakage_flags={"x": {"flagged": True}}
    )
    assert v.verdict == "REFUTED"


@pytest.mark.parametrize(
    "leak",
    [
        {"x": True},  # bare truthy non-dict — must not be silently ignored
        {"x": {"leak": True}},  # malformed dict, no "flagged" key — fail closed
        {"x": "leaking"},  # truthy string
    ],
)
def test_inv3_malformed_leakage_entry_fails_closed(leak):
    # Regression: the consumer filtered with `isinstance(v, dict)` and read
    # `.get("flagged")`, so a truthy-but-unrecognised leakage entry slipped past
    # the gate and the claim could SURVIVE. An unknown leakage shape must demote.
    spec = ClaimSpec(
        claim_id="lk",
        signal_type="EEG",
        task_type="nonlinear_structure",
        sampling_rate_hz=250.0,
        n_channels=1,
        n_samples=768,
        statistic="lagged_quadratic",
        surrogate_count=49,
    )
    v = evaluate_claim(spec, henon_series(768, seed=11), seed=7, leakage_flags=leak)
    assert v.verdict == "REFUTED"


def test_inv3_null_signal_does_not_survive():
    # IID Gaussian carries no nonlinear structure -> must not SURVIVE.
    spec, data = materialize("nonlinear_null")
    v = adjudicate_dataset(spec, data, n_surrogates=49)
    assert v["verdict"] != "SURVIVED"


# ------------------------------- INV-4 ANCHOR -------------------------------


@pytest.mark.parametrize(
    "quote",
    [
        "this empirical claim with p < 0.001 is absent from the source",
        "everyone should definitely adopt this absent normative claim",
        "an absent definitional sentence is defined as nothing",
    ],
)
def test_inv4_absent_quote_always_quarantined(quote):
    rec = adjudicate(_source(), [ProposedClaim("a", quote, "llm")])["records"][0]
    assert rec["disposition"] == "QUARANTINED_UNANCHORED"
    assert rec["anchored"] is False


# ----------------------------- INV-5 PROVENANCE -----------------------------


def test_inv5_adjudicate_artifact_hash_recomputes():
    report = adjudicate(_source(), [ProposedClaim("c1", "Decoding accuracy was 84%", "h")])
    clone = {k: v for k, v in report.items() if k != "artifact_sha256"}
    assert stable_sha256(clone) == report["artifact_sha256"]


def test_inv5_batch_artifact_hash_recomputes(tmp_path):
    item = BatchItem(_source(), [ProposedClaim("c1", "Decoding accuracy was 84%", "h")])
    report = adjudicate_batch([item], ledger=TruthLedger(tmp_path / "l.jsonl"))
    clone = {k: v for k, v in report.items() if k != "artifact_sha256"}
    assert stable_sha256(clone) == report["artifact_sha256"]


# ------------------------------ INV-6 RAW-GUARD -----------------------------


def test_inv6_non_signal_is_refused(tmp_path):
    p = tmp_path / "labels.npy"
    np.save(p, np.tile([0.0, 1.0, 2.0], 50))  # categorical labels, not a signal
    with pytest.raises(ValueError, match="raw/near-raw signal"):
        load_series(p)


# ------------------------ classify is pure/deterministic --------------------


def test_inv1_classify_is_pure():
    q = "the effect was statistically significant (p < 0.01)"
    assert classify(q).to_dict() == classify(q).to_dict()


# --------------------------- INV-7 SEED-STABILITY ---------------------------


def test_inv7_unstable_verdict_fails_closed():
    # a verdict that flips across the random seed is never certified.
    from bsff.stability import UNSTABLE, certify

    flip = {0: "SURVIVED", 1: "REFUTED"}
    report = certify(lambda s: flip[s % 2], seeds=[0, 1, 2, 3])
    assert report.stable is False
    assert report.certified == UNSTABLE


def test_inv7_strong_signal_certifies_stable():
    from bsff.stability import certify_dataset

    spec, data = materialize("nonlinear_effect")
    out = certify_dataset(spec, data, seeds=[1, 2, 3], n_surrogates=49)
    assert out["stability"]["stable"] is True
    assert out["certified_verdict"] == "SURVIVED"
