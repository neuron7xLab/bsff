# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (c) 2026 Yaroslav Vasylenko / neuron7xLab
from __future__ import annotations

from .bayesian import jzs_bayes_factor
from .schemas import ClaimSpec, VerdictJSON
from .stationarity import check_stationarity
from .surrogate_engine import rank_order_surrogate_test


def evaluate_claim(
    spec: ClaimSpec,
    signal,
    *,
    leakage_flags: dict | None = None,
    seed: int = 123,
    bayesian_evidence: bool | None = None,
) -> VerdictJSON:
    """Evaluate one claim through leakage-first and surrogate-test logic."""
    spec.validate()
    leakage_flags = leakage_flags or {}
    caveats: list[str] = []
    evidence: dict[str, object] = {}

    if any(bool(v.get("flagged")) for v in leakage_flags.values() if isinstance(v, dict)):
        return VerdictJSON(
            claim_id=spec.claim_id,
            verdict="REFUTED",
            p_value=None,
            original_statistic=None,
            surrogate_min=None,
            surrogate_max=None,
            leakage_flags=leakage_flags,
            evidence={"reason": "leakage_detector_flagged"},
            caveats=["Leakage falsification short-circuited surrogate testing."],
        )

    if spec.stationarity_gate == "required":
        stat_check = check_stationarity(signal, alpha=spec.alpha)
        evidence["stationarity_gate"] = stat_check
        if not bool(stat_check["all_stationary"]):
            caveats.append(
                f"Stationarity gate: {stat_check['n_channels_failed']} channel(s) failed KPSS. "
                "Interpret surrogate verdict as preprocessing-sensitive."
            )

    result = rank_order_surrogate_test(
        signal,
        n_surrogates=spec.surrogate_count,
        alpha=spec.alpha,
        seed=seed,
    )
    surrogate_stats = result["surrogate_statistics"]
    rejected = bool(result["rejected"])
    verdict = "SURVIVED" if rejected else "REFUTED"

    use_bayes = bool(
        spec.metadata.get("bayesian_evidence", False)
        if bayesian_evidence is None
        else bayesian_evidence
    )
    if use_bayes:
        bf = jzs_bayes_factor(float(result["original_statistic"]), surrogate_stats)
        evidence["bayesian_evidence"] = bf
        if not rejected:
            # BF01 > 3 is explicit evidence for the null; otherwise the correct
            # verdict is insufficient evidence, not fake certainty wearing a lab coat.
            verdict = "REFUTED" if float(bf["BF01"]) > 3.0 else "UNSUPPORTED"

    if spec.surrogate_count < 99:
        caveats.append("Low surrogate count: suitable for CI smoke, not final evidence.")
    evidence["surrogate_test"] = result
    return VerdictJSON(
        claim_id=spec.claim_id,
        verdict=verdict,
        p_value=float(result["p_value"]),
        original_statistic=float(result["original_statistic"]),
        surrogate_min=float(min(surrogate_stats)),
        surrogate_max=float(max(surrogate_stats)),
        leakage_flags=leakage_flags,
        evidence=evidence,
        caveats=caveats,
    )
