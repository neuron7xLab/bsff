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
    bayesian_corroboration_min: float = 3.0,
    max_iter: int = 200,
    tol: float = 1e-3,
    miaaft_fallback: str = "warn",
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
        max_iter=max_iter,
        tol=tol,
        fallback=miaaft_fallback,  # type: ignore[arg-type]
    )
    surrogate_stats = result["surrogate_statistics"]
    rejected = bool(result["rejected"])
    verdict = "SURVIVED" if rejected else "REFUTED"

    # Fail-closed: a verdict can never exceed UNSUPPORTED when the null model that
    # produced the p-value did not converge to the spectral/covariance constraints.
    # A mis-specified null makes both SURVIVED and REFUTED unearned certainty.
    convergence = result["surrogate_convergence"]
    evidence["surrogate_convergence"] = convergence
    if not bool(convergence["all_converged"]):
        caveats.append(
            f"Surrogate null mis-specified: {convergence['n_nonconverged']}/"
            f"{convergence['n_surrogates']} surrogate(s) failed the convergence/fidelity "
            "gate. Verdict demoted to UNSUPPORTED — the p-value rests on an invalid null."
        )
        evidence["surrogate_test"] = result
        return VerdictJSON(
            claim_id=spec.claim_id,
            verdict="UNSUPPORTED",
            p_value=float(result["p_value"]),
            original_statistic=float(result["original_statistic"]),
            surrogate_min=float(min(surrogate_stats)),
            surrogate_max=float(max(surrogate_stats)),
            leakage_flags=leakage_flags,
            evidence=evidence,
            caveats=caveats,
        )

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
        elif float(bf["BF10"]) < bayesian_corroboration_min:
            # Conjunction gate: a frequentist rejection that is NOT corroborated by
            # an effect-size Bayes factor is demoted from SURVIVED to UNSUPPORTED.
            # This is the rejected-path twin of the BF01 rule above and exists
            # because the rank-order p-value is anti-conservative for strongly
            # autocorrelated linear-Gaussian nulls (finite-N IAAFT bias): a
            # near-zero nonlinear effect can clear alpha by chance, but it cannot
            # also clear BF10 >= threshold. Measured to restore nominal specificity
            # with zero power loss (see tools/calibrate_operating_characteristic.py).
            verdict = "UNSUPPORTED"
            evidence["bayesian_corroboration"] = {
                "required_bf10": float(bayesian_corroboration_min),
                "observed_bf10": float(bf["BF10"]),
                "corroborated": False,
            }
            caveats.append(
                f"Frequentist rejection (p={float(result['p_value']):.3g}) not corroborated by "
                f"effect-size evidence: BF10={float(bf['BF10']):.3g} < "
                f"{float(bayesian_corroboration_min):.3g}. Verdict demoted to UNSUPPORTED — a "
                "rank-order p-value alone is anti-conservative for autocorrelated nulls."
            )

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
