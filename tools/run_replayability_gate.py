#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (c) 2026 Yaroslav Vasylenko / neuron7xLab
"""Replayability gate (PR-2) for the OpenAI-2026 Validation Grid.

Runs ONE fixed deterministic validation subset (the rank-order surrogate test on a
pinned logistic-map signal) across >=3 seed sets and proves:

  * the verdict CLASS (reject / do-not-reject the null) is identical across seeds —
    a seed must not be able to flip the decision (only p-value/timing noise may move);
  * the computation is bit-stable — re-running the SAME seed reproduces a
    byte-identical numeric artifact hash (no hidden nondeterminism).

Writes ``artifacts/replay/replayability_report.json``. FAIL if a seed is unfixed,
fewer than 3 seeds are used, the verdict class changes without an input change, or a
re-run hash diverges. No network.

    python tools/run_replayability_gate.py [--output artifacts/replay/replayability_report.json]
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

import numpy as np

from bsff import api

ROOT = Path(__file__).resolve().parents[1]

# Fixed seed sets — pinned in source so the grid (and reviewers) replay identically.
SEEDS = [2026, 7, 1337]
_SIGNAL_LEN = 512
_N_SURROGATES = 19


def _fixed_signal() -> np.ndarray:
    """Deterministic logistic-map series (chaotic, nonlinear) — no RNG, no seed."""
    x = np.empty(_SIGNAL_LEN, dtype=np.float64)
    x[0] = 0.4
    for i in range(1, _SIGNAL_LEN):
        x[i] = 3.9 * x[i - 1] * (1.0 - x[i - 1])
    return x


def _run_once(signal: np.ndarray, seed: int) -> dict:
    result = api.rank_order_surrogate_test(
        signal, n_surrogates=_N_SURROGATES, seed=seed, alpha=0.05
    )
    # Numeric fingerprint pinned to a tolerance that ignores nothing relevant: the
    # decision plus the statistic/p-value at full precision for the SAME seed.
    payload = {
        "rejected": bool(result["rejected"]),
        "original_statistic": float(result["original_statistic"]),
        "p_value": float(result["p_value"]),
    }
    canonical = json.dumps(payload, sort_keys=True).encode("utf-8")
    return {
        "seed": seed,
        "verdict_class": "REJECT_NULL" if payload["rejected"] else "RETAIN_NULL",
        "p_value": payload["p_value"],
        "artifact_hash": hashlib.sha256(canonical).hexdigest(),
    }


def derive() -> dict:
    signal = _fixed_signal()
    per_seed = [_run_once(signal, s) for s in SEEDS]

    # Determinism: re-run the first seed; its hash must reproduce byte-for-byte.
    rerun = _run_once(signal, SEEDS[0])
    deterministic = rerun["artifact_hash"] == per_seed[0]["artifact_hash"]

    classes = {r["verdict_class"] for r in per_seed}
    verdict_class_stable = len(classes) == 1
    seeds_fixed = len(SEEDS) >= 3 and len(set(SEEDS)) == len(SEEDS)

    failures: list[str] = []
    if not seeds_fixed:
        failures.append("fewer than 3 distinct fixed seeds")
    if not verdict_class_stable:
        failures.append(f"verdict class not seed-stable: {sorted(classes)}")
    if not deterministic:
        failures.append("re-run hash diverged (nondeterministic)")

    return {
        "gate": "openai-2026-replayability",
        "verdict": "PASS" if not failures else "FAIL",
        "seeds": SEEDS,
        "subset": "rank_order_surrogate_test/logistic_map",
        "per_seed": per_seed,
        "verdict_class_stable": verdict_class_stable,
        "artifact_hashes_match": deterministic,
        "failures": failures,
    }


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument(
        "--output", type=Path, default=ROOT / "artifacts" / "replay" / "replayability_report.json"
    )
    args = ap.parse_args(argv)
    report = derive()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2, sort_keys=True))
    print(f"\nREPLAYABILITY: {report['verdict']}  (report: {args.output})")
    return 0 if report["verdict"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
