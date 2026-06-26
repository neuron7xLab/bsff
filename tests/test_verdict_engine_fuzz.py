# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (c) 2026 Yaroslav Vasylenko / neuron7xLab
"""Self-breaking fuzz gate: the verdict engine must never fake a SURVIVED.

`test_surrogate_chaos` fuzzes the surrogate *engine*; this fuzzes the end-to-end
*verdict pipeline*. Hypothesis bombards ``evaluate_claim_pipeline`` with machine-
generated finite signals, policies, leakage flags, and seeds, and asserts the
fail-closed contract holds for EVERY input — the system tries to break itself:

  1. The only acceptable rejection is a ``ValueError`` (a controlled refusal). Any
     other escaping exception is a silent crash and fails the property.
  2. A returned verdict is always one of REFUTED / UNSUPPORTED / SURVIVED, bound to
     a 64-hex contract hash and a populated evidence graph.
  3. SURVIVED is unforgeable: it requires the surrogate stage to PASS on a
     *converged* null, and — when the policy runs Bayesian evidence — a BF10 at or
     above the corroboration threshold. A nonconverged or uncorroborated SURVIVED
     is a defect, and this gate turns red on it.
  4. Fatal leakage can never co-exist with a non-REFUTED verdict.

``derandomize=True`` makes the search reproducible, so a failure is a deterministic
artifact an auditor can replay, not a flaky scare.
"""

from __future__ import annotations

from collections import Counter

import numpy as np
from hypothesis import HealthCheck, given, settings
from hypothesis import strategies as st
from hypothesis.extra.numpy import arrays

from bsff import ClaimSpec, evaluate_claim_pipeline
from bsff.policy import PolicyProfile
from bsff.synthetic import henon_series

_VERDICTS = {"REFUTED", "UNSUPPORTED", "SURVIVED"}

# Coverage witness: white-noise-only fuzzing can NEVER produce SURVIVED, so the
# unforgeable-SURVIVED invariant below would be dead code. We mix in a genuine
# nonlinear positive control (Henon) and record every outcome, then assert the
# fuzz actually reached the SURVIVED branch (see test_fuzz_exercises_survived).
_OUTCOMES: Counter[str] = Counter()

_SETTINGS = settings(
    max_examples=60,
    deadline=None,
    derandomize=True,
    suppress_health_check=[HealthCheck.too_slow, HealthCheck.data_too_large],
)

# Fast policies that still exercise every collapse branch: smoke (no Bayes),
# standard (Bayesian corroboration), and a cheap Bayesian profile so the
# corroboration gate is fuzzed without paying for 999 strict surrogates.
_FAST_BAYES = PolicyProfile(
    name="fuzz-fast-bayes",
    surrogate_count=19,
    bayesian_evidence=True,
    bayesian_corroboration_min=3.0,
)
_POLICIES = st.sampled_from(["smoke", "standard", _FAST_BAYES])

_LEAKAGE = st.sampled_from(
    [
        None,
        {},
        {"block_design": {"flagged": False}},
        {"block_design": {"flagged": True, "reason": "fuzz"}},
        {"feature_selection": {"flagged": True}},
    ]
)


def _noise_signals():
    """Finite, validly-shaped signals — including pathological-but-finite ones."""
    return arrays(
        dtype=np.float64,
        shape=st.tuples(st.integers(1, 4), st.integers(32, 192)),
        elements=st.floats(
            min_value=-1e4, max_value=1e4, allow_nan=False, allow_infinity=False, width=64
        ),
    )


@st.composite
def _nonlinear_signals(draw):
    """Genuine nonlinear positive controls (Henon) so SURVIVED is reachable.

    Without these the fuzz only ever sees noise/pathological inputs, which can
    never SURVIVE, leaving the unforgeable-SURVIVED invariant untested.
    """
    seed = draw(st.integers(0, 2**31 - 1))
    n_samples = draw(st.integers(96, 192))
    series = henon_series(n_samples=n_samples, seed=seed)
    return series[np.newaxis, :].astype(np.float64)


def _signals():
    """White-noise/pathological inputs mixed with nonlinear positive controls."""
    return st.one_of(_noise_signals(), _nonlinear_signals())


def _spec(n_channels: int, n_samples: int) -> ClaimSpec:
    return ClaimSpec(
        claim_id="fuzz",
        signal_type="EEG",
        task_type="nonlinear_structure",
        sampling_rate_hz=250.0,
        n_channels=n_channels,
        n_samples=n_samples,
        statistic="lagged_quadratic",
        alpha=0.05,
        surrogate_count=19,
    )


@given(signal=_signals(), policy=_POLICIES, leakage=_LEAKAGE, seed=st.integers(0, 4))
@_SETTINGS
def test_verdict_engine_is_fail_closed_under_fuzz(signal, policy, leakage, seed):
    n_channels, n_samples = signal.shape
    spec = _spec(n_channels, n_samples)

    try:
        verdict = evaluate_claim_pipeline(
            spec, signal, policy=policy, leakage_flags=leakage, seed=seed
        )
    except ValueError:
        # A controlled, fail-closed refusal of an input the engine declines to judge.
        return

    # Whatever comes back must be a well-formed, hash-bound verdict.
    assert verdict.verdict in _VERDICTS
    _OUTCOMES[verdict.verdict] += 1
    assert isinstance(verdict.contract_sha256, str) and len(verdict.contract_sha256) == 64
    nodes = verdict.evidence_graph["nodes"]
    assert nodes, "evidence graph must not be empty"

    by_stage = {n["stage_id"]: n for n in nodes}
    surrogate = by_stage.get("surrogate_attack")
    bayesian = by_stage.get("bayesian_evidence")

    # Fatal leakage is incompatible with any non-REFUTED verdict.
    if isinstance(leakage, dict) and any(
        isinstance(v, dict) and v.get("flagged") for v in leakage.values()
    ):
        assert verdict.verdict == "REFUTED"
        assert surrogate is not None and surrogate["status"] == "SKIP"

    # The unforgeable-SURVIVED invariant.
    if verdict.verdict == "SURVIVED":
        assert surrogate is not None and surrogate["status"] == "PASS"
        convergence = surrogate["evidence"]["surrogate_convergence"]
        assert convergence["all_converged"] is True, "SURVIVED on a nonconverged null"
        # When the policy ran Bayesian evidence, a SURVIVED must be corroborated by
        # BF10 >= the policy's threshold (the conjunction gate); standard's is 3.0.
        prof = policy if isinstance(policy, PolicyProfile) else None
        runs_bayes = prof.bayesian_evidence if prof is not None else policy == "standard"
        if runs_bayes and isinstance(bayesian, dict) and bayesian.get("status") != "SKIP":
            bf10 = float(bayesian["evidence"].get("BF10", 0.0))
            threshold = prof.bayesian_corroboration_min if prof is not None else 3.0
            assert bf10 >= threshold, f"SURVIVED with uncorroborated BF10={bf10} < {threshold}"


def test_fuzz_exercises_survived() -> None:
    """The fuzz must actually reach SURVIVED, or the invariant above is dead code.

    Ordered after the property test (same file, definition order), so by the time
    this runs ``_OUTCOMES`` holds every verdict the fuzz produced. White-noise-only
    fuzzing yields {UNSUPPORTED, REFUTED} and silently skips the unforgeable-
    SURVIVED branch; the Henon positive controls make SURVIVED reachable.
    """
    assert _OUTCOMES, "fuzz produced no verdicts — the property test did not run"
    assert _OUTCOMES["SURVIVED"] > 0, (
        f"fuzz never reached SURVIVED, so its unforgeable-SURVIVED invariant is "
        f"untested (outcomes={dict(_OUTCOMES)})"
    )


def test_positive_control_reaches_unforgeable_survived() -> None:
    """Deterministic guard: a clean nonlinear control hits the SURVIVED invariant.

    Independent of Hypothesis' search so the SURVIVED branch is covered even if a
    future strategy change stops sampling it.
    """
    signal = henon_series(n_samples=160, seed=1)[np.newaxis, :]
    verdict = evaluate_claim_pipeline(
        _spec(1, 160), signal, policy="standard", leakage_flags=None, seed=1
    )
    assert verdict.verdict == "SURVIVED"
    by_stage = {n["stage_id"]: n for n in verdict.evidence_graph["nodes"]}
    surrogate = by_stage["surrogate_attack"]
    assert surrogate["status"] == "PASS"
    assert surrogate["evidence"]["surrogate_convergence"]["all_converged"] is True
