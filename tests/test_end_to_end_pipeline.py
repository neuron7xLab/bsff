# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (c) 2026 Yaroslav Vasylenko / neuron7xLab
"""End-to-end: the whole BSFF pipeline composes into one coherent system.

This is the integration proof that the parts built across the engine are not a
pile of modules but a single chain: a raw signal is written as EDF, normalized
through the raw-signal guard, and adjudicated to a real verdict; a publication's
claims are anchored, classified, routed, and chained into a tamper-evident
ledger; the ledger verifies and the report renders. If any link were broken,
this test would catch it.
"""

from __future__ import annotations

import numpy as np

from bsff.adjudication import (
    ProposedClaim,
    SourceDocument,
    TruthLedger,
    adjudicate,
    render_html,
)
from bsff.datasets import adjudicate_dataset, load_series, materialize
from bsff.normalize import write_edf
from bsff.synthetic import henon_series


def test_signal_path_edf_to_verdict(tmp_path):
    # raw signal -> EDF on disk -> normalize+guard -> data-driven verdict
    edf = tmp_path / "recording.edf"
    write_edf(edf, henon_series(1024, seed=3) * 40.0, sample_rate_hz=256.0, labels=["Cz"])
    data = load_series(edf)  # routes through normalize, passes the raw-signal guard
    assert data.shape == (1, 1024)
    spec, _ = materialize("nonlinear_effect")
    verdict = adjudicate_dataset(spec, data, n_surrogates=49)
    assert verdict["verdict"] == "SURVIVED"


def test_claim_path_anchor_to_ledger_to_render(tmp_path):
    source = SourceDocument.from_text(
        source_id="paper:demo",
        kind="text",
        uri="",
        text=(
            "Decoding accuracy was 84% (p < 0.01). Clinicians should adopt it. "
            "The field can never be measured by any instrument."
        ),
    )
    claims = [
        ProposedClaim("c1", "Decoding accuracy was 84% (p < 0.01)", "human:y"),
        ProposedClaim("c2", "Clinicians should adopt it", "human:y"),
        ProposedClaim("c3", "the device reads minds across continents", "llm:x"),  # not in source
    ]
    ledger = TruthLedger(tmp_path / "ledger.jsonl")
    report = adjudicate(source, claims, ledger=ledger)

    dispositions = {r["claim_id"]: r["disposition"] for r in report["records"]}
    assert dispositions["c2"] == "QUARANTINED_NORMATIVE"
    assert dispositions["c3"] == "QUARANTINED_UNANCHORED"
    # no claim is ever promoted to "true"
    assert "TRUE" not in set(dispositions.values())

    # the ledger is tamper-evident and intact, and the report renders for humans
    assert ledger.verify()["ok"]
    assert render_html(report).startswith("<!doctype html>")


def test_corpus_causal_fixture_through_engine():
    import json
    from pathlib import Path

    root = Path(__file__).resolve().parents[1]
    man = json.loads(
        (root / "data" / "validation" / "bsff_validation_corpus_v0_2_0_manifest.json").read_text()
    )
    corpus = np.load(root / man["artifact"])
    from bsff.transfer_entropy import transfer_entropy_test

    pair = corpus["coupled_ar_causal_pairs"][0]
    result = transfer_entropy_test(pair[0], pair[1], k=2, n_surrogates=49, seed=1)
    assert result.direction == "source->target"
