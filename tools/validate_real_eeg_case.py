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

import argparse
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

# Cross-environment float tolerance for the drift comparison. A reproducibility gate
# must catch a real verdict change (algorithmic drift is orders of magnitude larger)
# without firing on last-ULP numpy/BLAS noise that differs between CI runner images and
# Python versions (e.g. py3.13's newer numpy). 6 decimals is ULP-safe yet drift-catching.
_DRIFT_NDIGITS = 6


def _round_floats(obj: object, ndigits: int = _DRIFT_NDIGITS) -> object:
    """Recursively round floats so an exact comparison tolerates cross-env ULP noise."""
    if isinstance(obj, float):
        return round(obj, ndigits)
    if isinstance(obj, dict):
        return {k: _round_floats(v, ndigits) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_round_floats(v, ndigits) for v in obj]
    return obj


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


VERDICT_PATH = ART_DIR / "verdict.json"


def main(check: bool = False) -> int:
    failures: list[str] = []

    # Drift gate: in --check mode, snapshot the committed verdict.json *before* the run
    # overwrites it, so we can assert the engine still reproduces the published evidence
    # byte-for-byte. verdict.json is path-free and deterministic (unlike manifest.json,
    # which embeds the absolute BIDS path), so this comparison is environment-stable.
    # The core-fields reproducibility sha deliberately excludes the Bayesian block, so a
    # BF10/BF01 drift (e.g. the 1.8e19 -> capped-1e6 change in #93) was invisible to it;
    # comparing the whole verdict.json closes that hole for any field, not a hand-picked set.
    committed_verdict: str | None = None
    if check and VERDICT_PATH.is_file():
        committed_verdict = VERDICT_PATH.read_text(encoding="utf-8")

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

    # Verdict drift: the freshly regenerated verdict.json must equal the committed one.
    if check and committed_verdict is not None:
        regenerated = VERDICT_PATH.read_text(encoding="utf-8")
        # Restore the committed bytes so the working tree is never mutated by --check.
        VERDICT_PATH.write_text(committed_verdict, encoding="utf-8")
        if _round_floats(json.loads(regenerated)) != _round_floats(json.loads(committed_verdict)):
            failures.append(
                "verdict.json drifted from the committed artifact — the engine no longer "
                "reproduces the published evidence. Run `python tools/validate_real_eeg_case.py` "
                "and commit the refreshed artifacts/real_eeg_case/verdict.json."
            )

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
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--check",
        action="store_true",
        help="fail if the regenerated verdict.json drifts from the committed artifact "
        "(does not mutate the working tree)",
    )
    args = parser.parse_args()
    sys.exit(main(check=args.check))
