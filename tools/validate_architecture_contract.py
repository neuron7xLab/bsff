#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (c) 2026 Yaroslav Vasylenko / neuron7xLab
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from bsff.pipeline import FalsificationPipeline  # noqa: E402
from bsff.policy import adapt_policy_for_signal  # noqa: E402
from bsff.schemas import ClaimSpec  # noqa: E402
from bsff.synthetic import henon_series  # noqa: E402

REQUIRED_STAGES = ["stationarity_gate", "leakage_gate", "surrogate_attack", "bayesian_evidence"]


def main() -> int:
    failures: list[str] = []
    pipeline = FalsificationPipeline()
    if pipeline.registry.ids() != REQUIRED_STAGES:
        failures.append(f"stage topology mismatch: {pipeline.registry.ids()}")

    spec = ClaimSpec(
        claim_id="architecture-contract-smoke",
        signal_type="EEG",
        task_type="nonlinear_structure",
        sampling_rate_hz=250.0,
        n_channels=1,
        n_samples=768,
        statistic="lagged_quadratic",
        surrogate_count=19,
    )
    signal = henon_series(n_samples=768, seed=11)
    policy = adapt_policy_for_signal(spec, signal, "smoke")
    result = pipeline.evaluate(spec, signal, policy=policy, seed=101)
    payload = result.to_dict()

    if result.verdict != "SURVIVED":
        failures.append(f"expected SURVIVED smoke verdict, got {result.verdict}")
    if len(result.contract_sha256) != 64:
        failures.append("contract_sha256 is not a sha256 digest")
    if payload["evidence_graph"]["node_count"] != len(REQUIRED_STAGES):
        failures.append("evidence graph node count mismatch")

    out = ROOT / "artifacts" / "architecture_contract.json"
    out.parent.mkdir(exist_ok=True)
    out.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    if failures:
        print("Architecture contract: FAIL")
        for item in failures:
            print(f"- {item}")
        return 1
    print("Architecture contract: PASS")
    return 0


if __name__ == "__main__":
    sys.exit(main())
