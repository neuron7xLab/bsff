# SPDX-License-Identifier: GPL-3.0-or-later

from pathlib import Path

from bsff.statistics.proof_gate import DEFAULT_REPORT, evaluate, validate_report_in_sync

ROOT = Path(__file__).resolve().parents[1]


def test_gate_passes_on_committed_artifacts():
    report = evaluate(ROOT)
    assert report["status"] == "PASS"
    assert report["proof_count"] >= 1


def test_gate_report_snapshot_is_present():
    report = evaluate(ROOT)
    assert validate_report_in_sync(report, ROOT / DEFAULT_REPORT) == []
