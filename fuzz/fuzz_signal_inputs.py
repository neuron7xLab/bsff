#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (c) 2026 Yaroslav Vasylenko / neuron7xLab
"""Deterministic fuzz harness for the signal -> verdict entry point.

Feeds adversarial, malformed, and pathological arrays into
``evaluate_claim_pipeline`` and asserts the fail-closed contract: the engine either
(a) refuses with ``ValueError`` or (b) returns a well-formed verdict (one of the
three terminal verdicts with a 64-hex contract hash). Any OTHER escaping exception,
or a verdict emitted from non-finite input, is a crasher: the offending input is
written under ``fuzz/corpus/regressions/`` and the run exits non-zero.

    python fuzz/fuzz_signal_inputs.py --max-runs 5000 --seed 2026

Deterministic: a fixed seed reproduces the exact input sequence.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from bsff import ClaimSpec, evaluate_claim_pipeline

ROOT = Path(__file__).resolve().parents[1]
REGRESSIONS = ROOT / "fuzz" / "corpus" / "regressions"
VERDICTS = {"REFUTED", "UNSUPPORTED", "SURVIVED"}
_POLICIES = ("smoke", "standard")


def _spec(ch: int, n: int) -> ClaimSpec:
    return ClaimSpec(
        claim_id="fuzz",
        signal_type="EEG",
        task_type="nonlinear_structure",
        sampling_rate_hz=250.0,
        n_channels=max(1, ch),
        n_samples=max(16, n),
        statistic="lagged_quadratic",
        alpha=0.05,
        surrogate_count=19,
    )


def _random_signal(rng: np.random.Generator) -> np.ndarray:
    ch = int(rng.integers(1, 5))
    n = int(rng.integers(1, 200))
    scale = float(10.0 ** rng.integers(-6, 7))
    x = rng.normal(scale=scale, size=(ch, n)).astype(float)
    mode = int(rng.integers(0, 6))
    if mode == 1:  # inject NaN
        x[rng.integers(0, ch), rng.integers(0, n)] = np.nan
    elif mode == 2:  # inject Inf
        x[rng.integers(0, ch), rng.integers(0, n)] = np.inf * rng.choice([1, -1])
    elif mode == 3:  # constant channel
        x[:] = float(rng.normal())
    elif mode == 4:  # 1-D
        x = x[0]
    elif mode == 5:  # extreme amplitude spike
        x[0, 0] = 1e300
    return x


def _store_regression(tag: str, payload: dict) -> Path:
    REGRESSIONS.mkdir(parents=True, exist_ok=True)
    path = REGRESSIONS / f"signal_{tag}.json"
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return path


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--max-runs", type=int, default=5000)
    parser.add_argument("--seed", type=int, default=2026)
    args = parser.parse_args(argv)

    rng = np.random.default_rng(args.seed)
    refusals = verdicts = 0
    for i in range(args.max_runs):
        x = _random_signal(rng)
        arr = np.asarray(x, dtype=float)
        finite = bool(np.all(np.isfinite(arr))) and arr.size >= 16 and arr.ndim <= 2
        ch = arr.shape[0] if arr.ndim == 2 else 1
        n = arr.shape[-1]
        policy = _POLICIES[i % len(_POLICIES)]
        try:
            v = evaluate_claim_pipeline(_spec(ch, n), x, policy=policy, seed=i % 7)
        except ValueError:
            refusals += 1
            continue
        except Exception as exc:
            path = _store_regression(
                f"crash_{i}", {"run": i, "shape": list(arr.shape), "error": repr(exc)}
            )
            print(f"[CRASH] run {i}: {type(exc).__name__}: {exc}\n  stored: {path}")
            return 1
        if v.verdict not in VERDICTS or len(v.contract_sha256) != 64:
            path = _store_regression(f"badverdict_{i}", {"run": i, "verdict": v.verdict})
            print(f"[BAD VERDICT] run {i}: {v.verdict!r}\n  stored: {path}")
            return 1
        if not finite:
            path = _store_regression(
                f"verdict_from_nonfinite_{i}", {"run": i, "shape": list(arr.shape)}
            )
            print(
                f"[LEAK] run {i}: verdict emitted from non-finite/invalid input\n  stored: {path}"
            )
            return 1
        verdicts += 1

    print(
        f"fuzz_signal_inputs: PASS ({args.max_runs} runs, {refusals} refused, {verdicts} verdicts, "
        f"seed={args.seed})"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
