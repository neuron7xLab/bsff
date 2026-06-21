#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (c) 2026 Yaroslav Vasylenko / neuron7xLab
"""Fail-closed gate for the real-EEG (synthetic-fixture) BIDS case.

Runs the committed example end-to-end and asserts, exiting 1 on any failure:

* the fixture exists / is regenerated deterministically;
* the primary verdict is reproducible — re-running ``run_bids_case`` yields an
  identical sha256 over the *core* verdict fields (verdict, p_value, statistic);
* the feature-table case is REFUSED by the real ingestion guard;
* the label-leakage case is REFUTED by the real engine.

Writes/refreshes ``artifacts/real_eeg_case/{verdict.json,report.md,manifest.json}``
as a side effect of running the example. Styled after
``tools/validate_truth_contract.py``.
"""

from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
sys.path.insert(0, str(SRC))
sys.path.insert(0, str(ROOT / "examples" / "real_eeg_bids"))

from bsff.bids import run_bids_case  # noqa: E402

BIDS_DIR = ROOT / "examples" / "real_eeg_bids" / "bids"
ART_DIR = ROOT / "artifacts" / "real_eeg_case"
SEED = 101


def _core_verdict_sha256(verdict: dict[str, object]) -> str:
    """Stable digest over the verdict-bearing fields only (no caveats prose)."""
    core = {
        "claim_id": verdict.get("claim_id"),
        "verdict": verdict.get("verdict"),
        "p_value": verdict.get("p_value"),
        "original_statistic": verdict.get("original_statistic"),
        "surrogate_min": verdict.get("surrogate_min"),
        "surrogate_max": verdict.get("surrogate_max"),
    }
    blob = json.dumps(core, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(blob).hexdigest()


def main() -> int:
    failures: list[str] = []

    # Regenerate the fixture deterministically so the gate is hermetic.
    from generate_fixture import generate

    generate()

    if not (BIDS_DIR / "dataset_description.json").is_file():
        failures.append("missing fixture dataset_description.json")

    # Run the four-case example end-to-end (writes artifacts).
    from run import (
        feature_table_case,
        label_leakage_case,
        nonstationarity_case,
        primary_case,
    )

    try:
        primary = primary_case()
    except Exception as exc:
        print("real-eeg case gate failures:")
        print(f"- primary case raised: {exc}")
        return 1

    verdict = primary["verdict"]  # type: ignore[index]
    if verdict.get("verdict") not in {"SURVIVED", "REFUTED", "UNSUPPORTED"}:
        failures.append(f"primary verdict is not a valid verdict: {verdict.get('verdict')!r}")

    # Reproducibility: a second independent run must hash-match the core fields.
    rerun = run_bids_case(str(BIDS_DIR), subject="01", task="rest", seed=SEED, policy="standard")
    sha_a = _core_verdict_sha256(verdict)  # type: ignore[arg-type]
    sha_b = _core_verdict_sha256(rerun["verdict"])  # type: ignore[arg-type]
    if sha_a != sha_b:
        failures.append(f"primary verdict not reproducible: {sha_a} != {sha_b}")

    # Feature-table must be REFUSED by the real guard.
    try:
        ft = feature_table_case()
        if ft.get("outcome") != "REFUSED":
            failures.append(f"feature-table case not REFUSED: {ft.get('outcome')!r}")
    except Exception as exc:
        failures.append(f"feature-table guard did not fire: {exc}")

    # Label-leakage must be REFUTED by the real engine.
    try:
        ll = label_leakage_case()
        if ll.get("verdict") != "REFUTED":
            failures.append(f"label-leakage case not REFUTED: {ll.get('verdict')!r}")
    except Exception as exc:
        failures.append(f"label-leakage case failed: {exc}")

    # Nonstationarity case must carry the real KPSS caveat.
    try:
        ns = nonstationarity_case()
        if not any("Stationarity gate" in c for c in ns.get("caveats", [])):  # type: ignore[union-attr]
            failures.append("nonstationarity case missing KPSS stationarity caveat")
    except Exception as exc:
        failures.append(f"nonstationarity case failed: {exc}")

    for required in ("verdict.json", "report.md", "manifest.json"):
        if not (ART_DIR / required).is_file():
            failures.append(f"missing artifact: {required}")

    if failures:
        print("real-eeg case gate failures:")
        for failure in failures:
            print(f"- {failure}")
        return 1

    print("real-eeg case gate: PASS")
    print(f"  primary verdict : {verdict.get('verdict')} (p={verdict.get('p_value')})")
    print(f"  reproducible sha: {sha_a}")
    print("  feature-table   : REFUSED (real guard)")
    print("  label-leakage   : REFUTED (real engine)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
