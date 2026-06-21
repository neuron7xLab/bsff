# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (c) 2026 Yaroslav Vasylenko / neuron7xLab
"""Self-falsification controls: BSFF must fail and pass correctly on ground truth."""

from __future__ import annotations

from bsff.controls import run_control, verify_controls


def test_negative_control_does_not_survive():
    # white noise has no nonlinear structure -> must NOT be certified SURVIVED.
    rec = run_control("negative", seed=7, n_surrogates=99)
    assert rec["verdict"] != "SURVIVED"
    assert rec["control_passed"] is True


def test_positive_control_survives():
    # genuine Hénon nonlinearity -> must be certified SURVIVED.
    rec = run_control("positive", seed=7, n_surrogates=99)
    assert rec["verdict"] == "SURVIVED"
    assert rec["control_passed"] is True


def test_controls_contract_holds():
    result = verify_controls(seed=7, n_surrogates=99)
    assert result["controls_ok"] is True


def test_negative_control_robust_across_seeds():
    # the conjunction gate must hold the negative control across seeds, not one.
    survived = [
        run_control("negative", seed=s, n_surrogates=99)["verdict"] == "SURVIVED"
        for s in (11, 12, 13, 14, 15)
    ]
    assert sum(survived) == 0, f"white noise false-SURVIVED {sum(survived)}/5"
