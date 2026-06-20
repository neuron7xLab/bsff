# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (c) 2026 Yaroslav Vasylenko / neuron7xLab
"""Causal-claim route: adjudication via the transfer-entropy instrument."""

import numpy as np

from bsff.adjudication import ProposedClaim, SourceDocument, adjudicate_claim
from bsff.synthetic import coupled_ar_common_drive, coupled_ar_unidirectional

SOURCE_TEXT = (
    "We find that neural activity in region X drives the response in region Y. "
    "The premotor signal leads to motor output across trials."
)


def _src() -> SourceDocument:
    return SourceDocument.from_text(source_id="local:causal", kind="text", uri="", text=SOURCE_TEXT)


def _write(tmp_path, name, arr):
    p = tmp_path / name
    np.save(p, arr)
    return str(p) + ".npy"


def test_causal_claim_without_series_is_pending():
    claim = ProposedClaim(
        claim_id="c-cause",
        quote="neural activity in region X drives the response in region Y",
        proposer="human:y",
        operationalization={"test": "transfer_entropy"},
    )
    rec = adjudicate_claim(_src(), claim)
    assert rec.tier == "EMPIRICAL_GENERAL"
    assert rec.disposition == "PENDING_EVIDENCE"


def test_causal_claim_survives_with_conditioned_te(tmp_path):
    x, y = coupled_ar_unidirectional(n_samples=512, coupling=0.6, seed=5)
    # supply a (here irrelevant) conditioning series to exercise the conditioned path
    _x2, _y2, z = coupled_ar_common_drive(n_samples=512, seed=6)
    op = {
        "test": "transfer_entropy",
        "source": _write(tmp_path, "x", x),
        "target": _write(tmp_path, "y", y),
        "conditions": [_write(tmp_path, "z", z)],
        "n_surrogates": 49,
        "seed": 7,
    }
    claim = ProposedClaim(
        claim_id="c1",
        quote="neural activity in region X drives the response in region Y",
        proposer="human:y",
        operationalization=op,
    )
    rec = adjudicate_claim(_src(), claim)
    assert rec.disposition == "DIRECTED_COUPLING_SURVIVED"
    assert rec.evidence["direction"] == "source->target"
    assert rec.evidence["conditioned"] is True


def test_causal_claim_unconditioned_is_provisional(tmp_path):
    x, y = coupled_ar_unidirectional(n_samples=512, coupling=0.6, seed=5)
    op = {
        "test": "transfer_entropy",
        "source": _write(tmp_path, "x", x),
        "target": _write(tmp_path, "y", y),
        "n_surrogates": 49,
        "seed": 7,
    }
    claim = ProposedClaim(
        claim_id="c2",
        quote="neural activity in region X drives the response in region Y",
        proposer="human:y",
        operationalization=op,
    )
    rec = adjudicate_claim(_src(), claim)
    assert rec.disposition == "DIRECTED_COUPLING_UNCONDITIONED"
    assert any("common drive" in c for c in rec.evidence["caveats"])


def test_causal_claim_refuted_when_direction_is_reversed(tmp_path):
    # Claimed X->Y, but feed the data with source/target swapped: truth is Y->X.
    x, y = coupled_ar_unidirectional(n_samples=512, coupling=0.6, seed=5)
    op = {
        "test": "transfer_entropy",
        "source": _write(tmp_path, "y", y),  # claimed source is actually the effect
        "target": _write(tmp_path, "x", x),
        "n_surrogates": 49,
        "seed": 7,
    }
    claim = ProposedClaim(
        claim_id="c3",
        quote="the premotor signal leads to motor output across trials",
        proposer="human:y",
        operationalization=op,
    )
    rec = adjudicate_claim(_src(), claim)
    assert rec.disposition == "REFUTED"
    assert rec.evidence["direction"] == "target->source"
