# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (c) 2026 Yaroslav Vasylenko / neuron7xLab
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from .bayesian import jzs_bayes_factor
from .evidence import StageResult
from .leakage_detector import any_leakage_flagged
from .policy import PolicyProfile
from .schemas import ClaimSpec
from .stationarity import check_stationarity
from .surrogate_engine import rank_order_surrogate_test


@dataclass
class PipelineContext:
    spec: ClaimSpec
    signal: object
    policy: PolicyProfile
    seed: int = 123
    leakage_flags: dict[str, Any] = field(default_factory=dict)
    scratch: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class StationarityStage:
    stage_id: str = "stationarity_gate"

    def run(self, context: PipelineContext) -> StageResult:
        if context.policy.stationarity_mode == "off" or context.spec.stationarity_gate == "off":
            return StageResult(self.stage_id, "SKIP", evidence={"reason": "stationarity disabled"})
        result = check_stationarity(context.signal, alpha=context.policy.alpha)
        context.scratch[self.stage_id] = result
        all_stationary = bool(result["all_stationary"])
        if all_stationary:
            return StageResult(self.stage_id, "PASS", evidence=result)
        fatal = context.policy.stationarity_mode == "fail_closed"
        return StageResult(
            self.stage_id,
            "FAIL" if fatal else "WARN",
            fatal=fatal,
            evidence=result,
            caveats=[
                f"Stationarity gate: {result['n_channels_failed']} channel(s) failed KPSS; surrogate interpretation is preprocessing-sensitive."
            ],
        )


@dataclass(frozen=True)
class LeakageStage:
    stage_id: str = "leakage_gate"

    def run(self, context: PipelineContext) -> StageResult:
        flags = context.leakage_flags or {}
        flagged = any_leakage_flagged(flags)
        evidence = {"leakage_flags": flags, "flagged": bool(flagged)}
        context.scratch[self.stage_id] = evidence
        if flagged:
            return StageResult(
                self.stage_id,
                "FAIL",
                fatal=context.policy.leakage_fail_closed,
                evidence=evidence,
                caveats=[
                    "Leakage detector flagged a methodological path; surrogate testing is short-circuited."
                ],
            )
        return StageResult(self.stage_id, "PASS", evidence=evidence)


@dataclass(frozen=True)
class SurrogateAttackStage:
    stage_id: str = "surrogate_attack"

    def run(self, context: PipelineContext) -> StageResult:
        result = rank_order_surrogate_test(
            context.signal,
            n_surrogates=context.policy.surrogate_count,
            alpha=context.policy.alpha,
            seed=context.seed,
            max_iter=context.policy.miaaft_max_iter,
            tol=context.policy.miaaft_tol,
            fallback=context.policy.miaaft_fallback,
            max_relative_spectrum_error=context.policy.spectrum_error_warn,
            max_covariance_relative_rmsd=context.policy.covariance_rmsd_warn,
        )
        context.scratch[self.stage_id] = result
        rejected = bool(result["rejected"])
        status = "PASS" if rejected else "FAIL"
        caveats = []
        if context.policy.surrogate_count < 99:
            caveats.append(
                "Low surrogate count: CI smoke evidence, not publication-grade evidence."
            )
        convergence = result["surrogate_convergence"]
        if not bool(convergence["all_converged"]):
            caveats.append(
                f"Surrogate null mis-specified: {convergence['n_nonconverged']}/"
                f"{convergence['n_surrogates']} surrogate(s) failed the convergence/fidelity "
                "gate; verdict cannot exceed UNSUPPORTED."
            )
        return StageResult(self.stage_id, status, fatal=False, evidence=result, caveats=caveats)


@dataclass(frozen=True)
class BayesianEvidenceStage:
    stage_id: str = "bayesian_evidence"

    def run(self, context: PipelineContext) -> StageResult:
        if not context.policy.bayesian_evidence:
            return StageResult(
                self.stage_id, "SKIP", evidence={"reason": "bayesian evidence disabled"}
            )
        surrogate = context.scratch.get("surrogate_attack")
        if not isinstance(surrogate, dict):
            return StageResult(
                self.stage_id,
                "SKIP",
                evidence={"reason": "surrogate result unavailable"},
                caveats=["Bayesian evidence skipped because surrogate stage did not run."],
            )
        bf = jzs_bayes_factor(
            float(surrogate["original_statistic"]), surrogate["surrogate_statistics"]
        )
        context.scratch[self.stage_id] = bf
        status = "PASS" if float(bf["BF10"]) > 1.0 else "WARN"
        caveats: list[str] = []
        threshold = float(context.policy.bayesian_corroboration_min)
        if bool(surrogate.get("rejected")) and float(bf["BF10"]) < threshold:
            caveats.append(
                f"Frequentist rejection not corroborated: BF10={float(bf['BF10']):.3g} < "
                f"{threshold:.3g}; SURVIVED is demoted to UNSUPPORTED by the conjunction gate."
            )
        return StageResult(self.stage_id, status, evidence=bf, caveats=caveats)
