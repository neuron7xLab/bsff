# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (c) 2026 Yaroslav Vasylenko / neuron7xLab
"""Instrument calibration is a property of the build, not a one-off claim.

A reduced ground-truth battery is recomputed here so the headline operating
characteristic — full power on deterministic chaos, a conjunction gate that never
loosens specificity, and a clean Bayes-factor separation between genuine
nonlinear structure and linear-Gaussian artifacts — is enforced on every commit.
The full-resolution numbers live in ``artifacts/operating_characteristic.json``.
"""

from __future__ import annotations

import json
from pathlib import Path

from bsff.operating_characteristic import measure_operating_characteristic

ARTIFACT = Path(__file__).resolve().parents[1] / "artifacts" / "operating_characteristic.json"


def test_reduced_battery_invariants():
    oc = measure_operating_characteristic(
        n_seeds=10, n_samples=512, surrogate_count=49, corroboration_min=3.0
    )
    nonlinear_min_bf10 = []
    null_max_bf10 = []
    for c in oc.classes:
        # The conjunction rule is a subset of the frequentist rule: it can only
        # ever remove a SURVIVED, never invent one. Specificity cannot regress.
        assert c.conjunction_survive_rate <= c.frequentist_survive_rate + 1e-12
        if c.expect_survive:
            # Power must be retained: deterministic chaos survives the gate.
            assert c.conjunction_survive_rate >= 0.9
            assert c.min_bf10_among_rejections is not None
            nonlinear_min_bf10.append(c.min_bf10_among_rejections)
        else:
            if c.max_bf10_among_rejections is not None:
                null_max_bf10.append(c.max_bf10_among_rejections)

    # The mechanism: genuine nonlinear structure yields astronomically larger
    # effect-size evidence than any linear-Gaussian false rejection. A clean
    # margin is what lets a single threshold separate them.
    assert min(nonlinear_min_bf10) > 1e3
    if null_max_bf10:
        assert max(null_max_bf10) < 3.0
        assert max(null_max_bf10) < min(nonlinear_min_bf10)


def test_committed_artifact_is_consistent_and_shows_gate_effect():
    assert ARTIFACT.exists(), "run tools/calibrate_operating_characteristic.py"
    payload = json.loads(ARTIFACT.read_text(encoding="utf-8"))
    classes = {c["name"]: c for c in payload["classes"]}
    alpha = float(payload["config"]["alpha"])

    # Power: chaos survives at full rate.
    for name in ("henon", "logistic"):
        assert classes[name]["conjunction_survive_rate"] >= 0.95

    # Specificity: under the conjunction gate every null class's MEASURED FPR (point
    # estimate, not the permissive lower CI bound) sits at or below the nominal alpha,
    # and the gate strictly helped the worst offender (strongly autocorrelated AR(1)).
    for name in ("ar1_phi0.75", "ar1_phi0.50", "white"):
        c = classes[name]
        assert c["conjunction_survive_rate"] <= alpha
        assert c["conjunction_survive_rate"] <= c["frequentist_survive_rate"]
    worst = classes["ar1_phi0.75"]
    assert worst["conjunction_survive_rate"] < worst["frequentist_survive_rate"]
