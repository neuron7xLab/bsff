# SPDX-License-Identifier: GPL-3.0-or-later

from tests import test_stat_proof_gate as smoke


def test_gate_passes_on_committed_artifacts():
    smoke.test_gate_passes_on_committed_artifacts()


def test_gate_report_snapshot_is_present():
    smoke.test_gate_report_snapshot_is_present()
