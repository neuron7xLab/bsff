# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (c) 2026 Yaroslav Vasylenko / neuron7xLab
"""Bonn bright-line pipeline (Sample-Entropy lower-tail MIAAFT test).

G1: Set E (ictal) -> SURVIVED (power);  Sets A/B (healthy) -> not SURVIVED.
Deterministic seeds (SEED_BASE + index), convergence-gated, evidence-bearing JSON.
"""

from __future__ import annotations

import json
import platform
import subprocess
import sys
import time
from pathlib import Path
from typing import Any

import numpy as np

_HERE = Path(__file__).resolve().parent
if str(_HERE) not in sys.path:
    sys.path.insert(0, str(_HERE))

from loader import BonnSegment, load_set  # noqa: E402
from statistics_sampen import STATISTIC_ID, sampen_lower_tail_test  # noqa: E402

ALPHA = 0.05
SEED_BASE = 20260623
BRIGHT_LINE_THRESHOLD = 0.80  # predeclared; see docs/validation/BONN_BRIGHT_LINE_PROTOCOL.md


def _git_commit() -> str:
    try:
        return subprocess.run(["git", "rev-parse", "HEAD"], capture_output=True, text=True,
                              cwd=_HERE).stdout.strip()
    except Exception:
        return "unknown"


def adjudicate_segment(seg: BonnSegment, *, n_surrogates: int, seed: int) -> dict[str, Any]:
    from bsff.datasets import check_rawness
    from bsff.stationarity import check_stationarity

    data_2d = seg.data[np.newaxis, :]
    rawness = check_rawness(data_2d)
    stat = check_stationarity(data_2d, alpha=ALPHA)
    test = sampen_lower_tail_test(seg.data, n_surrogates=n_surrogates, alpha=ALPHA, seed=seed)
    return {
        "segment_id": seg.segment_id, "set": seg.set_label, "file_sha256": seg.file_sha256,
        "n_samples": seg.n_samples, "fs_hz": seg.metadata["fs_hz"],
        "rawness_flags": rawness, "kpss_stationary": bool(stat["all_stationary"]),
        "kpss_n_failed": int(stat["n_channels_failed"]),
        "sampen_orig": test["orig"], "sampen_surr_mean": test["surr_mean"], "sampen_surr_std": test["surr_std"],
        "p_value": test["p_value"], "n_surrogates": int(n_surrogates),
        "surrogate_converged": test["surrogate_converged"], "verdict": test["verdict"],
        "rejected": test["rejected"], "seed": int(seed), "statistic_id": STATISTIC_ID,
        "null": "MIAAFT", "tail": "lower", "alpha": ALPHA,
    }


def run_set(data_dir: Path, set_label: str, *, n_segments: int, n_surrogates: int, verbose=True) -> list[dict]:
    results = []
    for i, seg in enumerate(load_set(data_dir, set_label, n_segments=n_segments)):
        res = adjudicate_segment(seg, n_surrogates=n_surrogates, seed=SEED_BASE + i)
        results.append(res)
        if verbose:
            sym = {"SURVIVED": "✓", "REFUTED": "✗", "UNSUPPORTED": "?"}.get(res["verdict"], "?")
            print(f"  [{set_label}] {seg.segment_id} {sym} {res['verdict']:<11} p={res['p_value']:.3f} "
                  f"SampEn={res['sampen_orig']:.3f} surr={res['sampen_surr_mean']:.3f} "
                  f"conv={'ok' if res['surrogate_converged'] else 'FAIL'}")
    return results


def evaluate_bright_line(results_by_set: dict[str, list[dict]]) -> dict[str, Any]:
    E = results_by_set.get("E", [])
    survived_E = sum(1 for r in E if r["verdict"] == "SURVIVED")
    frac_E = survived_E / len(E) if E else 0.0
    neg = {}
    neg_pass = True
    for s in ("A", "B"):
        rs = results_by_set.get(s, [])
        if not rs:
            continue
        not_surv = sum(1 for r in rs if r["verdict"] != "SURVIVED")
        survived = sum(1 for r in rs if r["verdict"] == "SURVIVED")
        frac_not = not_surv / len(rs)
        neg[s] = {"n": len(rs), "survived": survived, "frac_not_survived": round(frac_not, 4)}
        neg_pass = neg_pass and frac_not >= BRIGHT_LINE_THRESHOLD
    pos_pass = frac_E >= BRIGHT_LINE_THRESHOLD
    passed = pos_pass and neg_pass and bool(neg)
    return {
        "n_E": len(E), "survived_E": survived_E, "frac_survived_E": round(frac_E, 4),
        "negative_sets": neg, "threshold": BRIGHT_LINE_THRESHOLD,
        "positive_control_pass": pos_pass, "negative_control_pass": neg_pass,
        "G1_PASS": passed, "verdict": "G1_PASS" if passed else "G1_NOT_PASS",
    }


def run_pipeline(data_dir, *, sets=("A", "B", "E"), n_segments=20, n_surrogates=99,
                 output=None, verbose=True) -> dict[str, Any]:
    import bsff

    if verbose:
        print("=" * 64)
        print(f"BSFF Bonn Bright Line (G1) | bsff {bsff.__version__} | statistic={STATISTIC_ID}")
        print(f"n_segments={n_segments} n_surrogates={n_surrogates} alpha={ALPHA} "
              f"seed_base={SEED_BASE} threshold={BRIGHT_LINE_THRESHOLD}")
        print("=" * 64)
    t0 = time.time()
    results_by_set: dict[str, list[dict]] = {}
    for s in sets:
        if verbose:
            print(f"\nSet {s}")
        try:
            results_by_set[s] = run_set(data_dir, s, n_segments=n_segments, n_surrogates=n_surrogates, verbose=verbose)
        except FileNotFoundError as e:
            if verbose:
                print(f"  WARNING: {e}")
    gate = evaluate_bright_line(results_by_set)
    elapsed = time.time() - t0
    if verbose:
        print("\n" + "=" * 64)
        print(f"  G1 Set E SURVIVED: {gate['survived_E']}/{gate['n_E']} ({gate['frac_survived_E'] * 100:.0f}%)")
        for s, d in gate["negative_sets"].items():
            print(f"  Set {s} not-SURVIVED: {d['n'] - d['survived']}/{d['n']} ({d['frac_not_survived'] * 100:.0f}%)")
        print(f"  G1_PASS: {gate['G1_PASS']}")
        print("=" * 64)
    bundle = {
        "schema": "bsff.bonn_bright_line/v3",
        "timestamp_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "bsff_version": bsff.__version__, "git_commit": _git_commit(),
        "environment": {"python": platform.python_version(), "platform": platform.platform()},
        "dataset": {"name": "Bonn EEG (Andrzejak 2001)", "doi": "10.1103/PhysRevE.64.061907",
                    "source": "UPF NTSA", "license": "research use, non-commercial"},
        "protocol": {"statistic_id": STATISTIC_ID, "statistic_params": {"m": 2, "r_factor": 0.15, "subsample": 1024},
                     "null": "MIAAFT", "tail": "lower", "alpha": ALPHA, "seed_base": SEED_BASE,
                     "n_surrogates": n_surrogates, "n_segments_per_set": n_segments,
                     "bright_line_threshold": BRIGHT_LINE_THRESHOLD},
        "results_by_set": results_by_set, "bright_line": gate, "elapsed_sec": round(elapsed, 2),
    }
    if output:
        Path(output).write_text(json.dumps(bundle, indent=2), encoding="utf-8")
        if verbose:
            print(f"Evidence bundle -> {output}")
    return bundle
