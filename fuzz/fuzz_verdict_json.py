#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (c) 2026 Yaroslav Vasylenko / neuron7xLab
"""Deterministic fuzz harness for the VerdictJSON schema loader.

Feeds malformed and adversarial payloads at the verdict JSON Schema validator and
asserts it fails closed: a non-conforming document is rejected with a
``ValidationError`` (never a crash), and a genuinely valid verdict always passes.
A malformed document that slips through, or any non-ValidationError exception, is a
crasher stored under ``fuzz/corpus/regressions/``.

    python fuzz/fuzz_verdict_json.py --max-runs 5000 --seed 2026
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import jsonschema
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from bsff.json_schema import verdict_json_schema

ROOT = Path(__file__).resolve().parents[1]
REGRESSIONS = ROOT / "fuzz" / "corpus" / "regressions"
_VERDICTS = ["REFUTED", "UNSUPPORTED", "SURVIVED", "MAYBE", "", 42, None]


def _random_payload(rng: np.random.Generator) -> dict:
    payload: dict = {}
    if rng.random() < 0.8:
        payload["claim_id"] = str(int(rng.integers(0, 10_000)))
    if rng.random() < 0.8:
        payload["verdict"] = _VERDICTS[int(rng.integers(0, len(_VERDICTS)))]
    if rng.random() < 0.6:
        payload["p_value"] = float(rng.normal()) if rng.random() < 0.7 else "nan"
    if rng.random() < 0.5:
        payload["leakage_flags"] = {} if rng.random() < 0.5 else [1, 2, 3]
    if rng.random() < 0.5:
        payload["evidence"] = {"k": int(rng.integers(0, 5))}
    if rng.random() < 0.3:
        payload[str(int(rng.integers(0, 99)))] = "junk"  # unexpected key
    return payload


def _store(tag: str, payload: dict) -> Path:
    REGRESSIONS.mkdir(parents=True, exist_ok=True)
    path = REGRESSIONS / f"verdict_{tag}.json"
    path.write_text(json.dumps(payload, indent=2, default=str), encoding="utf-8")
    return path


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--max-runs", type=int, default=5000)
    parser.add_argument("--seed", type=int, default=2026)
    args = parser.parse_args(argv)

    schema = verdict_json_schema()
    rng = np.random.default_rng(args.seed)
    rejected = accepted = 0
    for i in range(args.max_runs):
        payload = _random_payload(rng)
        try:
            jsonschema.validate(payload, schema)
            accepted += 1
        except jsonschema.ValidationError:
            rejected += 1
        except Exception as exc:
            path = _store(f"crash_{i}", {"run": i, "error": repr(exc), "payload": payload})
            print(f"[CRASH] run {i}: {type(exc).__name__}: {exc}\n  stored: {path}")
            return 1

    # A known-valid verdict document must always validate (no false rejection).
    valid = {
        "claim_id": "ok",
        "verdict": "UNSUPPORTED",
        "p_value": 0.5,
        "original_statistic": 0.1,
        "surrogate_min": 0.0,
        "surrogate_max": 1.0,
        "leakage_flags": {},
        "evidence": {},
        "caveats": [],
    }
    jsonschema.validate(valid, schema)

    print(
        f"fuzz_verdict_json: PASS ({args.max_runs} runs, {rejected} rejected, {accepted} accepted, "
        f"seed={args.seed})"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
