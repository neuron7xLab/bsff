# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (c) 2026 Yaroslav Vasylenko / neuron7xLab
"""Guard: the committed CURRENT_TRUTH.json is fresh and no public doc contradicts it."""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def _load(name: str):
    spec = importlib.util.spec_from_file_location(name, ROOT / "tools" / f"{name}.py")
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


def test_current_truth_is_fresh():
    assert _load("generate_current_truth").main(["--check"]) == 0


def test_no_public_doc_contradicts_current_truth(tmp_path):
    out = tmp_path / "truth_check.json"
    assert _load("validate_current_truth").main(["--output", str(out)]) == 0


def test_canonical_state_is_honest_about_robustness():
    import json

    truth = json.loads((ROOT / "artifacts" / "release" / "CURRENT_TRUTH.json").read_text())
    # The state tracks the strongest reproduced evidence; it must be one of the honest tokens.
    assert truth["latest_validation_state"] in {
        "BONN_NOMINAL_S2_PASS_BUT_G2_NOT_ROBUST",
        "BONN_S2_SEED_ROBUST_PASS_MULTINULL_PENDING",
        "BONN_S2_SEED_ROBUST_PASS_MULTINULL_FAILED",
        "BONN_S2_BRIGHT_LINE_ROBUSTLY_PASSED",  # only with seed-robust AND multi-null
    }
    assert truth["bonn_s2_nominal_state"] == "PASSED_SINGLE_SEED"
    # Full robust must not be claimed unless multi-null robustness also passed.
    if truth["latest_validation_state"] != "BONN_S2_BRIGHT_LINE_ROBUSTLY_PASSED":
        assert truth["robust_gate_passed"] is not True
    else:
        assert truth["multi_null_robustness_state"] == "PASSED"
    assert truth["BNCI_chain_state"] == "UNLOCKED_FOR_PREREGISTRATION_ONLY"
    assert truth["bonn_s1_state"] == "BRIGHT_LINE_NOT_PASSED"  # preserved
