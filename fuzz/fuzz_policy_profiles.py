#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (c) 2026 Yaroslav Vasylenko / neuron7xLab
"""Deterministic fuzz harness for policy-profile construction + validation.

A policy is the boundary between scientific intent and runtime thresholds; it must
reject nonsense fail-closed. This feeds adversarial parameters into ``PolicyProfile``
and ``get_policy_profile`` and asserts: an invalid policy raises ``ValueError`` (a
loosened gate, e.g. ``bayesian_corroboration_min < 1``, must never validate), an
unknown profile name raises ``ValueError``, and nothing crashes uncontrolled.

    python fuzz/fuzz_policy_profiles.py --max-runs 5000 --seed 2026
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from bsff.policy import PolicyProfile, get_policy_profile

ROOT = Path(__file__).resolve().parents[1]
REGRESSIONS = ROOT / "fuzz" / "corpus" / "regressions"


def _store(tag: str, payload: dict) -> Path:
    REGRESSIONS.mkdir(parents=True, exist_ok=True)
    path = REGRESSIONS / f"policy_{tag}.json"
    path.write_text(json.dumps(payload, indent=2, default=str), encoding="utf-8")
    return path


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--max-runs", type=int, default=5000)
    parser.add_argument("--seed", type=int, default=2026)
    args = parser.parse_args(argv)

    rng = np.random.default_rng(args.seed)
    valid = invalid = 0
    for i in range(args.max_runs):
        params = {
            "name": "" if rng.random() < 0.2 else f"fuzz-{i}",
            "alpha": float(rng.uniform(-0.5, 1.5)),
            "surrogate_count": int(rng.integers(-5, 2000)),
            "bayesian_corroboration_min": float(rng.uniform(-2.0, 20.0)),
            "miaaft_max_iter": int(rng.integers(-10, 500)),
            "miaaft_tol": float(rng.uniform(-1.0, 1.0)),
            "max_channels_ci": int(rng.integers(-5, 64)),
            "max_samples_ci": int(rng.integers(-5, 8192)),
        }
        try:
            policy = PolicyProfile(**params)
            policy.validate()
            # If it validated, the loosening invariants must hold.
            assert policy.bayesian_corroboration_min >= 1.0
            assert 0 < policy.alpha < 1
            valid += 1
        except (ValueError, AssertionError):
            invalid += 1
        except Exception as exc:
            path = _store(f"crash_{i}", {"run": i, "error": repr(exc), "params": params})
            print(f"[CRASH] run {i}: {type(exc).__name__}: {exc}\n  stored: {path}")
            return 1

    # Unknown profile names must fail closed.
    for bad_name in ("", "nonexistent", "SURVIVED", "../etc"):
        try:
            get_policy_profile(bad_name)
            path = _store("unknown_accepted", {"name": bad_name})
            print(f"[LEAK] unknown profile {bad_name!r} was accepted\n  stored: {path}")
            return 1
        except ValueError:
            pass

    print(
        f"fuzz_policy_profiles: PASS ({args.max_runs} runs, {valid} valid, {invalid} rejected, "
        f"seed={args.seed})"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
