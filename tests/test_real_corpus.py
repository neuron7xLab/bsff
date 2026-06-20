# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (c) 2026 Yaroslav Vasylenko / neuron7xLab
"""The real-claims corpus must triage honestly and reproducibly in CI."""

import json
import subprocess
import sys
from pathlib import Path

from bsff.adjudication import FalsifiabilityTier, classify

ROOT = Path(__file__).resolve().parents[1]
RUNNER = ROOT / "examples" / "real_corpus" / "run_corpus.py"

SURVIVING = {
    "SURVIVED_FALSIFICATION",
    "DIRECTED_COUPLING_SURVIVED",
    "DIRECTED_COUPLING_UNCONDITIONED",
}


def test_explicit_unfalsifiability_outranks_empirical_lexeme():
    # "measure" is an empirical lexeme, but the claim forbids its own test.
    c = classify("consciousness is a field that no instrument can ever detect or measure")
    assert c.tier is FalsifiabilityTier.NON_FALSIFIABLE
    assert "explicit_unfalsifiability" in c.signals


def test_real_corpus_triage(tmp_path):
    result = subprocess.run(
        [sys.executable, str(RUNNER), "--out", str(tmp_path)],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )
    assert result.returncode == 0, result.stdout + result.stderr

    lines = (tmp_path / "ledger.jsonl").read_text(encoding="utf-8").splitlines()
    verdicts = {
        json.loads(line)["payload"]["record"]["claim_id"]: json.loads(line)["payload"]["record"][
            "disposition"
        ]
        for line in lines
        if line.strip()
    }

    # explicit-unfalsifiable / normative / definitional pseudoscience: killed outright
    assert verdicts["consciousness-1"] == "QUARANTINED_NON_FALSIFIABLE"
    assert verdicts["crystal-1"] == "QUARANTINED_NORMATIVE"
    assert verdicts["intelligent-design-1"] == "QUARANTINED_DEFINITIONAL"

    # empirically phrased claims: honestly pending their data, never fake-killed
    for cid in ("astrology-1", "homeopathy-1", "vaccines-autism-1"):
        assert verdicts[cid] == "PENDING_EVIDENCE"

    # nothing is ever promoted to a surviving verdict without data
    assert not (set(verdicts.values()) & SURVIVING)
