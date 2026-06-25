# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (c) 2026 Yaroslav Vasylenko / neuron7xLab
"""PI-grade statistical-claims gate: no point-estimate-as-pass when the CI crosses the gate."""

from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def _vsc():
    spec = importlib.util.spec_from_file_location(
        "vsc", ROOT / "tools" / "validate_statistical_claims.py"
    )
    mod = importlib.util.module_from_spec(spec)
    sys.modules["vsc"] = mod
    spec.loader.exec_module(mod)
    return mod


def test_repo_passes_statistical_claims(tmp_path):
    assert _vsc().main(["--output", str(tmp_path / "r.json")]) == 0


def test_truth_records_robustness_honestly():
    t = json.loads((ROOT / "artifacts" / "release" / "CURRENT_TRUTH.json").read_text())
    assert {
        "robust_gate",
        "robust_gate_passed",
        "s2_wilson_ci_upper",
        "bonn_s2_robustness_state",
    } <= set(t)
    # If the specificity CI upper crosses 0.05, the state must NOT claim a robust/unqualified pass.
    if t.get("s2_wilson_ci_upper") and t["s2_wilson_ci_upper"] > 0.05:
        assert t["latest_validation_state"] not in {
            "BONN_S2_BRIGHT_LINE_PASSED",
            "BONN_S2_BRIGHT_LINE_ROBUSTLY_PASSED",
        }
        assert t["robust_gate_passed"] is False
