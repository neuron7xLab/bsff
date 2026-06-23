# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (c) 2026 Yaroslav Vasylenko / neuron7xLab
"""Property gate — schema + evidence-hash contract (P7-P8).

* P7: a ClaimSpec serializes, round-trips, and validates against its JSON Schema —
      the machine contract cannot silently drift from the dataclass.
* P8: the evidence hash is content-sensitive — identical content hashes identically,
      different content hashes differently. A constant/elided hash is a defect.
"""

from __future__ import annotations

import jsonschema
from hypothesis import given, settings
from hypothesis import strategies as st

from bsff.evidence import stable_sha256
from bsff.json_schema import claim_spec_schema
from bsff.schemas import ClaimSpec

_CORE = settings(max_examples=1000, deadline=None)

_SIGNALS = ["EEG", "ECoG", "sEEG", "spike", "LFP"]
_TASKS = ["classification", "regression", "connectivity", "nonlinear_structure"]


@st.composite
def _valid_spec(draw: st.DrawFn) -> ClaimSpec:
    alpha = draw(st.sampled_from([0.05, 0.01, 0.1, 0.025]))
    minimum = int(1 / alpha) - 1
    return ClaimSpec(
        claim_id=draw(
            st.text(
                min_size=1, max_size=24, alphabet=st.characters(min_codepoint=48, max_codepoint=122)
            )
        ),
        signal_type=draw(st.sampled_from(_SIGNALS)),
        task_type=draw(st.sampled_from(_TASKS)),
        sampling_rate_hz=draw(st.floats(1.0, 5000.0, allow_nan=False, allow_infinity=False)),
        n_channels=draw(st.integers(1, 256)),
        n_samples=draw(st.integers(16, 100_000)),
        statistic=draw(st.sampled_from(["lagged_quadratic", "transfer_entropy"])),
        alpha=alpha,
        surrogate_count=draw(st.integers(minimum, minimum + 2000)),
    )


@given(spec=_valid_spec())
@_CORE
def test_p7_claimspec_roundtrips_and_validates(spec: ClaimSpec) -> None:
    payload = spec.to_dict()
    jsonschema.validate(payload, claim_spec_schema())
    rebuilt = ClaimSpec(**payload)
    rebuilt.validate()
    assert rebuilt.to_dict() == payload


@given(
    a=st.dictionaries(st.text(max_size=8), st.integers(), max_size=6),
    b=st.dictionaries(st.text(max_size=8), st.integers(), max_size=6),
)
@_CORE
def test_p8_evidence_hash_is_content_sensitive(a: dict, b: dict) -> None:
    assert stable_sha256(a) == stable_sha256(a)
    assert len(stable_sha256(a)) == 64
    if a != b:
        assert stable_sha256(a) != stable_sha256(b), "distinct evidence collided to one hash"
