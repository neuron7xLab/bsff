#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (c) 2026 Yaroslav Vasylenko / neuron7xLab
"""Aggregate BNCI2014-001 confirmatory verdict -> BNCI_SUMMARY.json + BNCI_VERDICT.md.

Pass logic (frozen): positive-control pooled SURVIVED fraction >= 0.80 AND combined
AR-null FPR <= 0.05. No threshold change; the artifact decides.
"""

from __future__ import annotations

import json
import subprocess
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
A = ROOT / "artifacts" / "bnci2014_001"
CONF = A / "CONFIRMATORY_VERDICT.json"


def main() -> int:
    if not CONF.is_file():
        print("BLOCKED: CONFIRMATORY_VERDICT.json missing")
        return 3
    c = json.loads(CONF.read_text())
    commit = subprocess.run(
        ["git", "rev-parse", "HEAD"], capture_output=True, text=True, cwd=ROOT
    ).stdout.strip()
    pos = c["positive_control"]
    spec = c["specificity"]
    state = c["final_state"]
    summary = {
        "schema": "bsff.bnci_summary/v2",
        "final_state": state,
        "dataset": "BNCI2014-001",
        "statistic_id": c["statistic_id"],
        "null_model": c["null_model"],
        "alpha": c["alpha"],
        "detection_threshold_p": c["detection_threshold_p"],
        "n_surrogates": c["n_surrogates"],
        "correction": c["correction"],
        "channel_aggregation": c["channel_aggregation"],
        "subjects_requested": c["subjects_requested"],
        "subjects_executed": c["subjects_executed"],
        "subjects_failed": c["subjects_failed"],
        "positive_control": pos,
        "specificity": spec,
        "BNCI_CONFIRMATORY_PASSED": c["BNCI_CONFIRMATORY_PASSED"],
        "forbidden_claims": c["forbidden_claims"],
        "limitations": [
            "single dataset",
            "channel-mean aggregation",
            "epoch-level instrument",
            "not clinical/regulatory",
            "not independent replication",
        ],
        "git_commit": commit,
        "timestamp_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "next_state": (
            "BNCI confirmatory passed; record + preserve."
            if c["BNCI_CONFIRMATORY_PASSED"]
            else "BNCI confirmatory NOT passed; preserved as negative result. Bonn S2 unchanged; "
            "no BNCI claim."
        ),
    }
    (A / "BNCI_SUMMARY.json").write_text(json.dumps(summary, indent=2) + "\n")

    p, s = pos, spec
    md = f"""<!-- SPDX-License-Identifier: CC-BY-4.0 -->
# BNCI2014-001 confirmatory — verdict

**{state}** (commit `{commit[:12]}`).

Executed the locked SampEn+MIAAFT+AR-null method (p <= 0.025, n_surrogates={c["n_surrogates"]},
BH-FDR; channel-mean per epoch; bandpass {c["bandpass_hz"]} Hz, epoch {c["epoch_s"]} s).

- Subjects executed: {c["subjects_executed"]} (failed: {len(c["subjects_failed"])})
- Positive control: pooled SURVIVED fraction **{p["pooled_survived_fraction"]}** (>= {
        p["threshold"]
    }) -> {p["pass"]}
- Specificity: combined AR-null FPR **{s["combined_FPR"]}** (<= {s["threshold"]}) -> {s["pass"]}
- **BNCI_CONFIRMATORY_PASSED = {c["BNCI_CONFIRMATORY_PASSED"]}**

## Interpretation
{
        (
            "The BSFF instrument detects motor-imagery epoch structure and holds specificity on real-spectrum "
            "AR nulls for BNCI2014-001 under the locked protocol."
            if c["BNCI_CONFIRMATORY_PASSED"]
            else "The instrument did not satisfy both gates on BNCI2014-001 under the locked protocol. This is a "
            "valid negative result (e.g. finite-N specificity loss on short ~501-sample epochs vs the "
            "4097-sample Bonn calibration). Bonn S2 remains passed; no BNCI claim is made."
        )
    }

## Limits
Not clinical, regulatory, or device-grade. Single dataset; channel-mean aggregation; not replicated.
"""
    (A / "BNCI_VERDICT.md").write_text(md)
    print(state, "| positive", p["pooled_survived_fraction"], "FPR", s["combined_FPR"])
    return 0 if c["BNCI_CONFIRMATORY_PASSED"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
