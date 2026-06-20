# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (c) 2026 Yaroslav Vasylenko / neuron7xLab
"""Contract + ground-truth validation for the v0.2.0 validation corpus.

Two things are asserted. First, the committed corpus is exactly the artifact its
manifest claims (sha256 + shapes + synthetic-only flags). Second — the point of a
ground-truth corpus — the BSFF engine returns the verdict the corpus declares:
genuine nonlinear structure survives, linear/IID nulls do not, a causal pair is
called directionally, a null pair is not, and a common-drive confound that fools
pairwise transfer entropy collapses under conditioning. The corpus is generated
independently of the engine, so agreement is real external validation, not a
restatement.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import numpy as np

from bsff.schemas import ClaimSpec
from bsff.transfer_entropy import transfer_entropy_test
from bsff.verdict_engine import evaluate_claim

ROOT = Path(__file__).resolve().parents[1]
MANIFEST_PATH = ROOT / "data" / "validation" / "bsff_validation_corpus_v0_2_0_manifest.json"


def _manifest() -> dict:
    return json.loads(MANIFEST_PATH.read_text())


def _corpus():
    return np.load(ROOT / _manifest()["artifact"])


def _nonlinear_verdict(series, seed: int) -> str:
    series = np.asarray(series, dtype=float)
    cs = ClaimSpec(
        claim_id="vc",
        signal_type="EEG",
        task_type="nonlinear_structure",
        sampling_rate_hz=250.0,
        n_channels=1,
        n_samples=int(series.size),
        statistic="lagged_quadratic",
        surrogate_count=49,
    )
    return evaluate_claim(cs, series, seed=seed).verdict


# ------------------------------ corpus contract -----------------------------


def test_corpus_matches_manifest():
    man = _manifest()
    artifact = ROOT / man["artifact"]
    assert hashlib.sha256(artifact.read_bytes()).hexdigest() == man["sha256"]
    assert man["synthetic_only"] is True
    assert man["clinical_data"] is False
    assert man["version"] == "0.2.0"


def test_corpus_arrays_and_shapes():
    man = _manifest()
    corpus = _corpus()
    assert set(corpus.files) == set(man["arrays"])
    for name, shape in man["arrays"].items():
        assert tuple(corpus[name].shape) == tuple(shape), name


# --------------------------- ground-truth verdicts --------------------------


def test_nonlinear_structure_present_survives():
    corpus = _corpus()
    assert _nonlinear_verdict(corpus["henon_nonlinear_series"][:1024], seed=7) == "SURVIVED"
    assert _nonlinear_verdict(corpus["logistic_nonlinear_series"][:1024], seed=7) == "SURVIVED"


def test_linear_null_banks_do_not_survive():
    corpus = _corpus()
    for name in ("ar1_null_bank", "correlated_linear_null_bank"):
        bank = corpus[name]
        survived = [_nonlinear_verdict(bank[i, 0], seed=100 + i) == "SURVIVED" for i in range(4)]
        assert sum(survived) == 0, f"{name} false-survived {sum(survived)}/4"


def test_causal_pairs_are_called_directionally():
    corpus = _corpus()
    pairs = corpus["coupled_ar_causal_pairs"]
    correct = [
        transfer_entropy_test(
            pairs[i, 0], pairs[i, 1], k=2, n_surrogates=49, seed=200 + i
        ).direction
        == "source->target"
        for i in range(5)
    ]
    assert sum(correct) >= 4, f"causal direction correct {sum(correct)}/5"


def test_null_pairs_show_no_direction():
    corpus = _corpus()
    pairs = corpus["coupled_ar_null_pairs"]
    none = [
        transfer_entropy_test(
            pairs[i, 0], pairs[i, 1], k=2, n_surrogates=49, seed=300 + i
        ).direction
        == "none"
        for i in range(5)
    ]
    assert sum(none) >= 4, f"null pairs -> none {sum(none)}/5"


def test_common_drive_confound_collapses_under_conditioning():
    corpus = _corpus()
    tri = corpus["coupled_ar_common_drive_triples"]
    pairwise_fires = 0
    conditional_fires = 0
    for i in range(5):
        x, y, z = tri[i, 0], tri[i, 1], tri[i, 2]
        if transfer_entropy_test(x, y, k=2, n_surrogates=49, seed=400 + i).p_value <= 0.05:
            pairwise_fires += 1
        if (
            transfer_entropy_test(
                x, y, conditions=[z], k=2, cond_lag=3, n_surrogates=49, seed=400 + i
            ).p_value
            <= 0.05
        ):
            conditional_fires += 1
    # pairwise TE is fooled by the shared driver; conditioning must reduce it.
    assert pairwise_fires >= 4
    assert conditional_fires < pairwise_fires
