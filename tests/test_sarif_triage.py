# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (c) 2026 Yaroslav Vasylenko / neuron7xLab
"""SARIF triage: severity bucketing and block-at gating."""

from __future__ import annotations

import importlib.util
from pathlib import Path

_TOOL = Path(__file__).resolve().parents[1] / "tools" / "triage_sarif.py"
_spec = importlib.util.spec_from_file_location("triage_sarif", _TOOL)
assert _spec and _spec.loader
triage_sarif = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(triage_sarif)


def _sarif(results, rules):
    return {
        "runs": [
            {"tool": {"driver": {"rules": rules}}, "results": results},
        ]
    }


def _rule(rule_id, security_severity=None):
    r = {"id": rule_id}
    if security_severity is not None:
        r["properties"] = {"security-severity": security_severity}
    return r


def test_security_severity_score_maps_to_tier():
    assert triage_sarif._score_to_tier(9.5) == "critical"
    assert triage_sarif._score_to_tier(7.0) == "high"
    assert triage_sarif._score_to_tier(4.0) == "medium"
    assert triage_sarif._score_to_tier(1.0) == "low"


def test_triage_counts_by_tier():
    sarif = _sarif(
        results=[
            {"ruleId": "py/x", "level": "error", "locations": []},
            {"ruleId": "py/crit", "level": "warning", "locations": []},
        ],
        rules=[_rule("py/x", "8.1"), _rule("py/crit", "9.8")],
    )
    report = triage_sarif.triage(sarif)
    assert report["counts"]["high"] == 1
    assert report["counts"]["critical"] == 1
    assert report["total"] == 2


def test_level_fallback_when_no_security_severity():
    sarif = _sarif(
        results=[{"ruleId": "py/q", "level": "error", "locations": []}],
        rules=[_rule("py/q")],
    )
    report = triage_sarif.triage(sarif)
    assert report["counts"]["high"] == 1  # error -> high


def test_block_at_high_fails_on_high_finding(tmp_path):
    sarif = _sarif(
        results=[{"ruleId": "py/x", "level": "warning", "locations": []}],
        rules=[_rule("py/x", "7.5")],
    )
    p = tmp_path / "r.sarif"
    p.write_text(__import__("json").dumps(sarif))
    assert triage_sarif.main([str(p), "--block-at", "high"]) == 1


def test_clean_sarif_passes(tmp_path):
    sarif = _sarif(
        results=[{"ruleId": "py/note", "level": "note", "locations": []}],
        rules=[_rule("py/note")],
    )
    p = tmp_path / "r.sarif"
    p.write_text(__import__("json").dumps(sarif))
    assert triage_sarif.main([str(p), "--block-at", "high"]) == 0


def test_empty_sarif_passes(tmp_path):
    p = tmp_path / "r.sarif"
    p.write_text('{"runs": []}')
    assert triage_sarif.main([str(p)]) == 0
