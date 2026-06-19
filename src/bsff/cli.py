# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (c) 2026 Yaroslav Vasylenko / neuron7xLab
from __future__ import annotations

import argparse
import json
from pathlib import Path

from .calibration import calibrate_miaaft_budget, required_rank_order_surrogates
from .leakage_detector import detect_block_design_leakage
from .schemas import ClaimSpec
from .surrogate_engine import miaaft_surrogate, rank_order_surrogate_test
from .synthetic import ar1_multichannel, block_design_dataset, henon_series
from .validation import sha256_bytes
from .verdict_engine import evaluate_claim


def validate_kernel(output: Path) -> dict[str, object]:
    output.parent.mkdir(parents=True, exist_ok=True)

    x = ar1_multichannel(n_channels=32, n_samples=1024, seed=42)
    _surrogate, surrogate_diag = miaaft_surrogate(
        x,
        max_iter=200,
        tol=1e-3,
        seed=42,
        return_diagnostics=True,
    )
    ar1 = rank_order_surrogate_test(
        ar1_multichannel(n_channels=1, n_samples=512, seed=1)[0],
        n_surrogates=19,
        alpha=0.05,
        seed=99,
    )
    henon = rank_order_surrogate_test(
        henon_series(n_samples=768, seed=11),
        n_surrogates=19,
        alpha=0.05,
        seed=101,
    )
    _features, labels, block_ids = block_design_dataset(n_blocks=12, block_len=16)
    leakage = detect_block_design_leakage(labels, block_ids)
    spec = ClaimSpec(
        claim_id="bsff-cli-smoke",
        signal_type="EEG",
        task_type="nonlinear_structure",
        sampling_rate_hz=250.0,
        n_channels=1,
        n_samples=768,
        statistic="lagged_quadratic",
        surrogate_count=19,
    )
    verdict = evaluate_claim(spec, henon_series(n_samples=768, seed=11), seed=101)
    calibration = calibrate_miaaft_budget(
        x, candidate_iters=(20, 40, 80, 120, 160, 200), tol=1e-3, seed=42
    )

    report = {
        "document_ref": "OS-BSFF-CORE-2026.1",
        "pipeline_status": "EXECUTION_COMPLETE",
        "phase": "PHASE_1_OPERATIONAL_KERNEL",
        "gates": {
            "miaaft_convergence": surrogate_diag,
            "ar1_null_not_rejected": ar1,
            "henon_power_smoke": henon,
            "block_design_leakage": leakage,
            "verdict_json": verdict.to_dict(),
            "surrogate_budget_calibration": calibration.to_dict(),
            "rank_order_min_surrogates_alpha_0_05": required_rank_order_surrogates(0.05),
        },
        "status": "SURVIVED_PHASE_1_GATES"
        if surrogate_diag["converged"]
        and ar1["surrogate_convergence"]["all_converged"]
        and henon["surrogate_convergence"]["all_converged"]
        and ar1["p_value"] > 0.05
        and henon["p_value"] <= 0.05
        and leakage["flagged"]
        else "FAILED_PHASE_1_GATES",
    }
    serialized = json.dumps(report, ensure_ascii=False, indent=2)
    report["artifact_sha256"] = sha256_bytes(serialized.encode("utf-8"))
    output.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    return report


def main() -> None:
    parser = argparse.ArgumentParser(description="Run BSFF operational kernel validation.")
    parser.add_argument(
        "--output",
        default="artifacts/bsff_phase1_validation.json",
        help="Path for machine-readable validation artifact.",
    )
    args = parser.parse_args()
    report = validate_kernel(Path(args.output))
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
