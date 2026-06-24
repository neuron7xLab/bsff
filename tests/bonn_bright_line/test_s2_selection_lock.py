# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (c) 2026 Yaroslav Vasylenko / neuron7xLab
"""S2 selection lock: freezes the best passing candidate, or NONE; no edits after freeze."""

from __future__ import annotations

import json

import s2_select_candidate as sel


def _expl(tmp_path, results):
    p = tmp_path / "expl.json"
    p.write_text(json.dumps({"schema": "bsff.s2_exploratory/v1", "results": results}))
    return p


def test_selects_lowest_fpr_passing(tmp_path, monkeypatch):
    monkeypatch.setattr(sel, "ROOT", tmp_path)
    res = [
        {"id": "S2-C3-sampen-fdr", "status": "PASS", "combined_FPR": 0.04, "G1_E_survived": 0.95},
        {"id": "S2-C7-permen", "status": "PASS", "combined_FPR": 0.02, "G1_E_survived": 0.90},
        {
            "id": "S2-C2-sampen-corroboration",
            "status": "FAIL",
            "combined_FPR": 0.06,
            "G1_E_survived": 0.96,
        },
    ]
    sel.main(["--exploratory", str(_expl(tmp_path, res)), "--output", "lock.json"])
    lock = json.loads((tmp_path / "lock.json").read_text())
    assert lock["S2_SELECTION"] == "S2-C7-permen"  # lowest combined_FPR among PASS
    assert lock["alpha_frozen"] == 0.05
    assert "alpha" in lock["forbidden_changes"]


def test_none_when_no_candidate_passes(tmp_path, monkeypatch):
    monkeypatch.setattr(sel, "ROOT", tmp_path)
    res = [
        {
            "id": "S2-C1-sampen-finiteN",
            "status": "FAIL",
            "combined_FPR": 0.06,
            "G1_E_survived": 0.40,
        }
    ]
    sel.main(["--exploratory", str(_expl(tmp_path, res)), "--output", "lock.json"])
    lock = json.loads((tmp_path / "lock.json").read_text())
    assert lock["S2_SELECTION"] == "NONE"
    assert "no candidate" in lock["reason"]
