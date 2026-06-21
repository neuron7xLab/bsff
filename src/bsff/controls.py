# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (c) 2026 Yaroslav Vasylenko / neuron7xLab
"""Self-falsification controls: prove the instrument fails and passes correctly.

Before BSFF is allowed to attack an external claim, it must demonstrate on
ground truth that it can be wrong in both directions:

* the **negative control** feeds a signal with no nonlinear structure (white
  noise) under a claim that it *has* structure — a correct instrument must NOT
  return SURVIVED;
* the **positive control** feeds a signal with genuine nonlinear structure
  (Hénon) — a correct instrument MUST return SURVIVED.

If either control gives the wrong verdict, BSFF has no authority to judge
anything else. This is Axiom 7 (self-falsification before authority) made
executable. Both controls run through the same engine as any real case and emit
a hash-stamped verdict.
"""

from __future__ import annotations

from typing import Any

import numpy as np

from .evidence import stable_sha256
from .schemas import ClaimSpec
from .synthetic import henon_series, white_noise_series
from .validation import sha256_bytes
from .verdict_engine import evaluate_claim

CONTROL_KINDS = ("negative", "positive")

# The controls run the CONJUNCTION GATE (effect-size Bayes factor >= 3), not the
# bare rank-order test. Self-falsification surfaced why: without it, the
# rank-order p-value is anti-conservative and white noise false-SURVIVES ~2/10
# (measured); with the conjunction gate it is 0/10 while genuine nonlinearity
# stays 10/10. A strict verdict therefore requires the gate.
_BAYES_CORROBORATION_MIN = 3.0


def _signal(kind: str, seed: int, n: int) -> np.ndarray:
    if kind == "negative":
        return white_noise_series(n, seed=seed)  # no nonlinear structure
    if kind == "positive":
        return henon_series(n, seed=seed)  # genuine deterministic nonlinearity
    raise ValueError(f"unknown control kind {kind!r}; expected {CONTROL_KINDS}")


def run_control(
    kind: str, *, seed: int = 7, n_samples: int = 768, n_surrogates: int = 99
) -> dict[str, Any]:
    """Run one control through the conjunction-gated engine; hash-stamped verdict."""
    if kind not in CONTROL_KINDS:
        raise ValueError(f"unknown control kind {kind!r}; expected {CONTROL_KINDS}")
    expected = "not SURVIVED" if kind == "negative" else "SURVIVED"
    series = np.asarray(_signal(kind, seed, n_samples), dtype=float)
    spec = ClaimSpec(
        claim_id=f"control-{kind}",
        signal_type="EEG",
        task_type="nonlinear_structure",
        sampling_rate_hz=250.0,
        n_channels=1,
        n_samples=int(series.size),
        statistic="lagged_quadratic",
        surrogate_count=n_surrogates,
    )
    v = evaluate_claim(
        spec,
        series,
        seed=seed,
        bayesian_evidence=True,
        bayesian_corroboration_min=_BAYES_CORROBORATION_MIN,
    )
    verdict = str(v.verdict)
    passed = (verdict != "SURVIVED") if kind == "negative" else (verdict == "SURVIVED")
    record: dict[str, Any] = {
        "control": kind,
        "expected": expected,
        "verdict": verdict,
        "p_value": v.p_value,
        "decision_rule": "conjunction (rank-order p<=alpha AND BF10>=3)",
        "control_passed": bool(passed),
        "data_sha256": sha256_bytes(series.tobytes()),
        "seed": seed,
        "n_surrogates": n_surrogates,
    }
    record["artifact_sha256"] = stable_sha256(record)
    return record


def verify_controls(*, seed: int = 7, n_surrogates: int = 99) -> dict[str, Any]:
    """Run both controls and return the contract result (fail-closed)."""
    neg = run_control("negative", seed=seed, n_surrogates=n_surrogates)
    pos = run_control("positive", seed=seed, n_surrogates=n_surrogates)
    ok = neg["control_passed"] and pos["control_passed"]
    return {
        "negative": neg,
        "positive": pos,
        "contract": "negative != SURVIVED AND positive == SURVIVED",
        "controls_ok": bool(ok),
    }
