# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (c) 2026 Yaroslav Vasylenko / neuron7xLab
"""Aggregator verdict logic + allowed-state machine (no threshold hacking)."""

from __future__ import annotations

import json

import aggregate_verdict as agg

_ALLOWED = {"BRIGHT_LINE_PASSED", "BRIGHT_LINE_NOT_PASSED", "BLOCKED_DATA"}


def _g1(frac_e, frac_a_not, frac_b_not):
    return {
        "protocol": {"statistic_id": "sampen_lower_tail_m2_r015_v1", "n_surrogates": 199},
        "bright_line": {
            "frac_survived_E": frac_e,
            "negative_sets": {
                "A": {"frac_not_survived": frac_a_not},
                "B": {"frac_not_survived": frac_b_not},
            },
        },
    }


def _g2(fpr, n=100):
    nfp = round(fpr * n)
    return {
        "control": {"n_segments": n, "n_false_positives": nfp, "fpr": fpr, "fpr_ok": fpr <= 0.05}
    }


def _wire(tmp_path, monkeypatch, g1, g2a, g2b):
    bl = tmp_path / "bl"
    ct = tmp_path / "ct"
    bl.mkdir()
    ct.mkdir()
    (bl / "g1.json").write_text(json.dumps(g1))
    (ct / "a.json").write_text(json.dumps(g2a))
    (ct / "b.json").write_text(json.dumps(g2b))
    monkeypatch.setattr(agg, "BL", bl)
    monkeypatch.setattr(agg, "CT", ct)
    monkeypatch.setattr(agg, "G1", bl / "g1.json")
    monkeypatch.setattr(agg, "G2A", ct / "a.json")
    monkeypatch.setattr(agg, "G2B", ct / "b.json")
    monkeypatch.setattr(agg, "ROOT", tmp_path)
    (tmp_path / "docs" / "validation").mkdir(parents=True)


def _verdict(bl):
    return json.loads((bl / "BRIGHT_LINE_SUMMARY.json").read_text())["verdict"]


def test_pass_when_both_gates_pass(tmp_path, monkeypatch):
    _wire(tmp_path, monkeypatch, _g1(1.0, 0.9, 0.95), _g2(0.02), _g2(0.03))
    rc = agg.main()
    v = _verdict(tmp_path / "bl")
    assert v == "BRIGHT_LINE_PASSED" and rc == 0 and v in _ALLOWED


def test_not_passed_when_negative_sanity_fails(tmp_path, monkeypatch):
    # G1 power perfect but Set A not-survived 0.75 < 0.80 -> NOT PASSED (no threshold hacking).
    _wire(tmp_path, monkeypatch, _g1(1.0, 0.75, 0.95), _g2(0.02), _g2(0.02))
    rc = agg.main()
    assert _verdict(tmp_path / "bl") == "BRIGHT_LINE_NOT_PASSED" and rc == 2


def test_not_passed_when_g2_fpr_exceeds_alpha(tmp_path, monkeypatch):
    _wire(tmp_path, monkeypatch, _g1(1.0, 0.9, 0.9), _g2(0.09), _g2(0.02))
    agg.main()
    assert _verdict(tmp_path / "bl") == "BRIGHT_LINE_NOT_PASSED"


def test_blocked_when_bundle_missing(tmp_path, monkeypatch):
    bl = tmp_path / "bl"
    bl.mkdir()
    monkeypatch.setattr(agg, "BL", bl)
    monkeypatch.setattr(agg, "G1", bl / "missing.json")
    monkeypatch.setattr(agg, "G2A", bl / "missing.json")
    monkeypatch.setattr(agg, "G2B", bl / "missing.json")
    rc = agg.main()
    assert _verdict(bl) == "BLOCKED_DATA" and rc == 3
