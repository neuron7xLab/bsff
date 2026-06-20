# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (c) 2026 Yaroslav Vasylenko / neuron7xLab
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from .evidence import EvidenceGraph, StageResult, stable_sha256
from .policy import PolicyProfile, adapt_policy_for_signal
from .registry import StageRegistry
from .schemas import ClaimSpec, VerdictJSON
from .stages import (
    BayesianEvidenceStage,
    LeakageStage,
    PipelineContext,
    StationarityStage,
    SurrogateAttackStage,
)


@dataclass(frozen=True)
class PipelineVerdict:
    claim_id: str
    verdict: str
    policy: dict[str, object]
    evidence_graph: dict[str, Any]
    caveats: list[str]
    contract_sha256: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "claim_id": self.claim_id,
            "verdict": self.verdict,
            "policy": self.policy,
            "evidence_graph": self.evidence_graph,
            "caveats": self.caveats,
            "contract_sha256": self.contract_sha256,
        }

    def to_verdict_json(self) -> VerdictJSON:
        nodes = self.evidence_graph.get("nodes", [])
        surrogate = next((n for n in nodes if n.get("stage_id") == "surrogate_attack"), None)
        leakage = next((n for n in nodes if n.get("stage_id") == "leakage_gate"), None)
        surrogate_evidence = surrogate.get("evidence", {}) if isinstance(surrogate, dict) else {}
        leakage_evidence = leakage.get("evidence", {}) if isinstance(leakage, dict) else {}
        stats = surrogate_evidence.get("surrogate_statistics") or []
        return VerdictJSON(
            claim_id=self.claim_id,
            verdict=self.verdict,  # type: ignore[arg-type]
            p_value=float(surrogate_evidence["p_value"])
            if "p_value" in surrogate_evidence
            else None,
            original_statistic=float(surrogate_evidence["original_statistic"])
            if "original_statistic" in surrogate_evidence
            else None,
            surrogate_min=float(min(stats)) if stats else None,
            surrogate_max=float(max(stats)) if stats else None,
            leakage_flags=dict(leakage_evidence.get("leakage_flags", {})),
            evidence={"pipeline": self.to_dict()},
            caveats=list(self.caveats),
        )


def default_stage_registry() -> StageRegistry:
    registry = StageRegistry()
    registry.extend(
        [StationarityStage(), LeakageStage(), SurrogateAttackStage(), BayesianEvidenceStage()]
    )
    return registry


class FalsificationPipeline:
    """Composable falsification pipeline with deterministic stage ordering."""

    def __init__(self, registry: StageRegistry | None = None) -> None:
        self.registry = registry or default_stage_registry()

    def run(
        self,
        spec: ClaimSpec,
        signal: object,
        *,
        policy: PolicyProfile | str = "smoke",
        leakage_flags: dict[str, Any] | None = None,
        seed: int = 123,
    ) -> PipelineVerdict:
        """Alias of :meth:`evaluate` for callers that expect a ``run`` entry point.

        The falsification semantics are identical; this exists only so that the
        common ``pipeline.run(spec, signal)`` idiom does not raise AttributeError.
        """
        return self.evaluate(spec, signal, policy=policy, leakage_flags=leakage_flags, seed=seed)

    def evaluate(
        self,
        spec: ClaimSpec,
        signal: object,
        *,
        policy: PolicyProfile | str = "smoke",
        leakage_flags: dict[str, Any] | None = None,
        seed: int = 123,
    ) -> PipelineVerdict:
        spec.validate()
        adapted = adapt_policy_for_signal(spec, signal, policy)
        context = PipelineContext(
            spec=spec, signal=signal, policy=adapted, seed=seed, leakage_flags=leakage_flags or {}
        )
        results: list[StageResult] = []
        for stage in self.registry:
            if any(result.fatal for result in results):
                results.append(
                    StageResult(stage.stage_id, "SKIP", evidence={"reason": "previous fatal stage"})
                )
                continue
            results.append(stage.run(context))

        graph = EvidenceGraph(tuple(results))
        verdict = self._collapse_verdict(results, context)
        graph_dict = graph.to_dict()
        contract = {
            "claim": spec.to_dict(),
            "policy": adapted.to_dict(),
            "stage_ids": self.registry.ids(),
            "evidence_graph_sha256": graph_dict["graph_sha256"],
            "verdict": verdict,
        }
        return PipelineVerdict(
            claim_id=spec.claim_id,
            verdict=verdict,
            policy=adapted.to_dict(),
            evidence_graph=graph_dict,
            caveats=graph.caveats,
            contract_sha256=stable_sha256(contract),
        )

    @staticmethod
    def _collapse_verdict(results: list[StageResult], context: PipelineContext) -> str:
        if any(result.fatal and result.status == "FAIL" for result in results):
            return "REFUTED"
        surrogate = next(
            (result for result in results if result.stage_id == "surrogate_attack"), None
        )
        if surrogate is None or surrogate.status == "SKIP":
            return "UNSUPPORTED"
        # Fail-closed: a non-converged null model invalidates the p-value, so no
        # confident SURVIVED/REFUTED can be claimed regardless of the rank order.
        surrogate_evidence = context.scratch.get("surrogate_attack", {})
        convergence = (
            surrogate_evidence.get("surrogate_convergence", {})
            if isinstance(surrogate_evidence, dict)
            else {}
        )
        if convergence and not bool(convergence.get("all_converged", True)):
            return "UNSUPPORTED"
        bayes = context.scratch.get("bayesian_evidence")
        if surrogate.status == "PASS":
            # Conjunction gate (mirrors verdict_engine.evaluate_claim): when the
            # Bayesian stage ran, a frequentist rejection must be corroborated by
            # BF10 >= policy.bayesian_corroboration_min to earn SURVIVED. This
            # closes the anti-conservative IAAFT-bias hole on autocorrelated nulls.
            if isinstance(bayes, dict) and float(bayes.get("BF10", 0.0)) < float(
                context.policy.bayesian_corroboration_min
            ):
                return "UNSUPPORTED"
            return "SURVIVED"
        if isinstance(bayes, dict) and float(bayes.get("BF01", 0.0)) <= 3.0:
            return "UNSUPPORTED"
        return "REFUTED"


def evaluate_claim_pipeline(
    spec: ClaimSpec,
    signal: object,
    *,
    policy: PolicyProfile | str = "smoke",
    leakage_flags: dict[str, Any] | None = None,
    seed: int = 123,
) -> PipelineVerdict:
    return FalsificationPipeline().evaluate(
        spec, signal, policy=policy, leakage_flags=leakage_flags, seed=seed
    )
