# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (c) 2026 Yaroslav Vasylenko / neuron7xLab
"""The pseudoscience-killer demonstration must kill, reproducibly, in CI."""

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEMO = ROOT / "examples" / "pseudoscience_killer" / "run_demo.py"

SURVIVING = {
    "SURVIVED_FALSIFICATION",
    "DIRECTED_COUPLING_SURVIVED",
    "DIRECTED_COUPLING_UNCONDITIONED",
}


def test_demo_runs_and_kills(tmp_path):
    result = subprocess.run(
        [sys.executable, str(DEMO), "--out", str(tmp_path)],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )
    # The script self-checks; a zero exit means no pseudoscience claim survived.
    assert result.returncode == 0, result.stdout + result.stderr

    report = json.loads((tmp_path / "report.json").read_text(encoding="utf-8"))
    assert report["n_claims"] == 5

    ledger_lines = (tmp_path / "ledger.jsonl").read_text(encoding="utf-8").splitlines()
    verdicts = {
        json.loads(line)["payload"]["record"]["claim_id"]: json.loads(line)["payload"]["record"][
            "disposition"
        ]
        for line in ledger_lines
        if line.strip()
    }
    assert not (set(verdicts.values()) & SURVIVING)
    assert verdicts["fabricated"] == "QUARANTINED_UNANCHORED"
    assert verdicts["chaos"] in {"REFUTED", "UNSUPPORTED"}
    assert verdicts["telepathy"] == "UNSUPPORTED"

    # the rendered, human-readable verdict page is produced and self-contained
    html = (tmp_path / "report.html").read_text(encoding="utf-8")
    assert html.startswith("<!doctype html>")
