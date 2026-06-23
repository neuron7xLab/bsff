#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (c) 2026 Yaroslav Vasylenko / neuron7xLab
"""Cross-artifact numeric consistency checker (Phase 3).

Verifies the G1/G2 numbers and the final verdict agree across the executed JSON
verdicts AND the human-facing docs. Fails closed: any mismatch -> exit 2. It never
edits measured results — it only reports divergence so a doc/script can be fixed.
"""
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def _num(text: str, pattern: str):
    m = re.search(pattern, text)
    return float(m.group(1)) if m else None


def main(argv=None) -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--summary", default="artifacts/bonn_bright_line/BRIGHT_LINE_SUMMARY.json")
    p.add_argument("--g1", default="artifacts/bonn_bright_line/bonn_CONFIRMATORY_VERDICT.json")
    p.add_argument("--g2a", default="artifacts/controls/ar_negative_CONFIRMATORY_A.json")
    p.add_argument("--g2b", default="artifacts/controls/ar_negative_CONFIRMATORY_B.json")
    p.add_argument("--formal", default="FORMAL_VERDICT.md")
    p.add_argument("--status", default="docs/validation/BONN_STATUS.md")
    p.add_argument("--output", default="artifacts/release/CONSISTENCY_CHECK.json")
    a = p.parse_args(argv)

    s = json.loads((ROOT / a.summary).read_text())
    g1 = json.loads((ROOT / a.g1).read_text())["bright_line"]
    g2a = json.loads((ROOT / a.g2a).read_text())["control"]
    g2b = json.loads((ROOT / a.g2b).read_text())["control"]

    # Source of truth = the executed verdict JSONs.
    truth = {
        "E_survived_fraction": round(float(g1["frac_survived_E"]), 4),
        "A_not_survived_fraction": round(float(g1["negative_sets"]["A"]["frac_not_survived"]), 4),
        "B_not_survived_fraction": round(float(g1["negative_sets"]["B"]["frac_not_survived"]), 4),
        "FPR_A": round(float(g2a["fpr"]), 4),
        "FPR_B": round(float(g2b["fpr"]), 4),
        "combined_FPR": round((g2a["n_false_positives"] + g2b["n_false_positives"])
                              / (g2a["n_segments"] + g2b["n_segments"]), 4),
        "G1_PASS": bool(g1["G1_PASS"]),
        "G2_PASS": bool(g2a["fpr_ok"] and g2b["fpr_ok"]
                        and (g2a["n_false_positives"] + g2b["n_false_positives"])
                        / (g2a["n_segments"] + g2b["n_segments"]) <= 0.05),
    }
    truth["BRIGHT_LINE_PASSED"] = truth["G1_PASS"] and truth["G2_PASS"]
    truth["final_state"] = "BRIGHT_LINE_PASSED" if truth["BRIGHT_LINE_PASSED"] else "BRIGHT_LINE_NOT_PASSED"

    mismatches = []

    # 1. Summary JSON vs truth.
    for k in ("E_survived_fraction", "A_not_survived_fraction", "B_not_survived_fraction"):
        if round(float(s["G1"][k]), 4) != truth[k]:
            mismatches.append(f"summary.G1.{k}={s['G1'][k]} != {truth[k]}")
    for k in ("FPR_A", "FPR_B", "combined_FPR"):
        if round(float(s["G2"][k]), 4) != truth[k]:
            mismatches.append(f"summary.G2.{k}={s['G2'][k]} != {truth[k]}")
    for k in ("G1_PASS", "G2_PASS", "BRIGHT_LINE_PASSED", "final_state"):
        if s.get(k) != truth[k]:
            mismatches.append(f"summary.{k}={s.get(k)} != {truth[k]}")

    # 2. Docs vs truth (numbers appear as text).
    for path, name in ((a.formal, "FORMAL_VERDICT.md"), (a.status, "BONN_STATUS.md")):
        fp = ROOT / path
        if not fp.is_file():
            mismatches.append(f"{name}: missing")
            continue
        txt = fp.read_text()
        if truth["final_state"] not in txt:
            mismatches.append(f"{name}: final_state {truth['final_state']} not present")
        for _label, val in (("0.96", truth["E_survived_fraction"]), ("0.86", truth["A_not_survived_fraction"]),
                           ("0.08", truth["FPR_A"]), ("0.065", truth["combined_FPR"])):
            if f"{val:.2f}".rstrip("0") not in txt and f"{val:g}" not in txt and f"{val}" not in txt:
                mismatches.append(f"{name}: expected value {val} not found")

    result = {
        "status": "PASS" if not mismatches else "FAIL",
        "truth_from_verdict_json": truth,
        "mismatches": mismatches,
    }
    out = ROOT / a.output
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(result, indent=2) + "\n")
    print(f"CONSISTENCY: {result['status']}")
    for m in mismatches:
        print("  -", m)
    return 0 if not mismatches else 2


if __name__ == "__main__":
    raise SystemExit(main())
