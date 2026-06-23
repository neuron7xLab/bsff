#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (c) 2026 Yaroslav Vasylenko / neuron7xLab
"""Degradation gate: compare a benchmark run against the committed baseline.

Raw wall-times are not comparable across machines, so each benchmark's time is
normalized by the ``test_bench_calibration`` time in the SAME run — a fixed unit of
numerical work. Comparing the calibration-normalized ratios cancels machine speed,
so a regression flagged here is algorithmic, not a slow runner. Peak memory (from
tracemalloc, counted in bytes) is machine-independent and compared directly.

    python tools/compare_benchmark_baseline.py baseline.json current.json

Peak memory (tracemalloc bytes) is machine-independent and gated tightly (+15%).
Wall-time is gated to catch ALGORITHMIC regressions (>=2x), not micro-noise: even
calibration-normalized, an FFT-heavy calibration and a Python-loop-heavy pipeline
scale differently across CPU microarchitectures, so a same-machine baseline run on
a different CI runner legitimately drifts tens of percent without any code change.
A 2x normalized-time blow-up is a real complexity regression and fails the gate.
Standard library only; no network.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

CALIBRATION = "test_bench_calibration"
# Wall-time: catch algorithmic regressions across machines, not micro-jitter.
TIME_THRESHOLD = 1.0
# Below this baseline median (seconds) a benchmark is faster than the measurement
# noise floor; its normalized time ratio swings wildly from jitter alone, so the
# wall-time gate is not applied (memory, which is allocation-counted, still is).
TIME_NOISE_FLOOR_S = 5e-4
# Peak memory is allocation-counted (machine-independent) → tight bound.
MEMORY_THRESHOLD = 0.15


def _index(report: dict) -> dict[str, dict]:
    out: dict[str, dict] = {}
    for b in report.get("benchmarks", []):
        out[b["name"]] = {
            "mean": float(b["stats"]["mean"]),
            "median": float(b["stats"].get("median", b["stats"]["mean"])),
            "peak_memory_bytes": float(b.get("extra_info", {}).get("peak_memory_bytes", 0.0)),
        }
    return out


def _normalized_time(entry: dict, calib: float) -> float:
    # median is steadier than mean under one-off jitter.
    return entry["median"] / calib if calib > 0 else entry["median"]


def compare(baseline: dict, current: dict) -> list[str]:
    base = _index(baseline)
    cur = _index(current)
    regressions: list[str] = []

    if CALIBRATION not in base or CALIBRATION not in cur:
        return [f"calibration benchmark {CALIBRATION!r} missing from a report"]
    base_calib = base[CALIBRATION]["median"]
    cur_calib = cur[CALIBRATION]["median"]

    for name, base_entry in base.items():
        if name == CALIBRATION or name not in cur:
            continue
        cur_entry = cur[name]
        # Only gate wall-time on benchmarks slower than the noise floor.
        if base_entry["median"] >= TIME_NOISE_FLOOR_S:
            base_ratio = _normalized_time(base_entry, base_calib)
            cur_ratio = _normalized_time(cur_entry, cur_calib)
            if base_ratio > 0:
                drift = (cur_ratio - base_ratio) / base_ratio
                if drift > TIME_THRESHOLD:
                    regressions.append(
                        f"{name}: normalized time +{drift:.0%} (> {TIME_THRESHOLD:.0%})"
                    )
        base_mem = base_entry["peak_memory_bytes"]
        cur_mem = cur_entry["peak_memory_bytes"]
        if base_mem > 0:
            mem_drift = (cur_mem - base_mem) / base_mem
            if mem_drift > MEMORY_THRESHOLD:
                regressions.append(
                    f"{name}: peak memory +{mem_drift:.0%} (> {MEMORY_THRESHOLD:.0%})"
                )
    return regressions


def main(argv: list[str] | None = None) -> int:
    args = argv if argv is not None else sys.argv[1:]
    if len(args) != 2:
        print("usage: compare_benchmark_baseline.py <baseline.json> <current.json>")
        return 2
    baseline = json.loads(Path(args[0]).read_text(encoding="utf-8"))
    current = json.loads(Path(args[1]).read_text(encoding="utf-8"))
    regressions = compare(baseline, current)
    if regressions:
        print("Performance degradation detected:")
        for item in regressions:
            print(f"- {item}")
        print("If this is intentional, regenerate the baseline with justification.")
        return 1
    print(f"Degradation gate: PASS (no calibration-normalized regression > {TIME_THRESHOLD:.0%})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
