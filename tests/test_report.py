# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (c) 2026 Yaroslav Vasylenko / neuron7xLab
"""The verdict writer must emit deterministic, sorted, round-trippable JSON."""

from __future__ import annotations

import json

from bsff.report import write_verdict_json
from bsff.schemas import VerdictJSON


def _verdict() -> VerdictJSON:
    return VerdictJSON(
        claim_id="report-roundtrip",
        verdict="UNSUPPORTED",
        p_value=0.05,
        original_statistic=0.42,
        surrogate_min=0.01,
        surrogate_max=0.4,
        leakage_flags={},
        evidence={"k": "v"},
        caveats=["c1"],
    )


def test_write_verdict_json_roundtrips(tmp_path):
    out = write_verdict_json(_verdict(), tmp_path / "nested" / "verdict.json")
    assert out.exists()
    loaded = json.loads(out.read_text(encoding="utf-8"))
    assert loaded == _verdict().to_dict()


def test_write_verdict_json_is_sorted_and_stable(tmp_path):
    path = tmp_path / "v.json"
    first = write_verdict_json(_verdict(), path).read_text(encoding="utf-8")
    second = write_verdict_json(_verdict(), path).read_text(encoding="utf-8")
    assert first == second
    keys = list(json.loads(first).keys())
    assert keys == sorted(keys)
