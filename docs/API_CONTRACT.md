<!-- SPDX-License-Identifier: CC-BY-4.0 -->
<!-- Copyright (c) 2026 Yaroslav Vasylenko / neuron7xLab -->

# BSFF public API contract

`bsff.api` is the supported integration surface. The signatures below are frozen
and guarded by `tests/test_public_api_contract.py`: a rename, removal, or reorder
of any public parameter fails CI. Integrate through `bsff.api`; everything under
other `bsff.*` submodules is internal and may move between releases.

## Stability policy

- Public signatures change only with a version bump and an update to this file
  and the frozen contract test.
- Every public function carries a docstring, type hints, and a runnable example.
- A verdict is always one of `REFUTED` / `UNSUPPORTED` / `SURVIVED`, bound to a
  64-hex `contract_sha256`; invalid input fails closed with `ValueError`.

## Functions

### `evaluate_claim_pipeline(spec, signal, *, policy="smoke", leakage_flags=None, seed=123) -> PipelineVerdict`
Run one claim + signal through the default falsification pipeline. Returns a
`PipelineVerdict` (verdict, policy, evidence graph, caveats, contract hash).

### `rank_order_surrogate_test(signal, statistic=lagged_quadratic, *, n_surrogates=19, alpha=0.05, seed=123, max_iter=200, tol=1e-3, fallback="warn", max_relative_spectrum_error=0.10, max_covariance_relative_rmsd=0.35) -> dict`
One-sided rank-order surrogate test with convergence/fidelity diagnostics.

### `miaaft_surrogate(signal, *, n_iter=None, max_iter=200, tol=1e-4, seed=None, return_diagnostics=False, fallback="warn")`
Generate one multivariate IAAFT-style surrogate (optionally with diagnostics).

### `validate_verdict_json(payload) -> None`
Validate a verdict document against the published JSON Schema; raises
`jsonschema.ValidationError` on non-conformance.

### `load_policy_profile(name="smoke") -> PolicyProfile`
Return a named policy profile: `smoke` | `standard` | `strict`.

### `generate_evidence_manifest(verdict) -> dict`
Build a deterministic, hash-stamped evidence manifest from a `PipelineVerdict`
(binds claim id, verdict, contract hash, evidence graph, and caveats under a
single `manifest_sha256`).

## Example

```python
from bsff.api import evaluate_claim_pipeline, generate_evidence_manifest
from bsff.schemas import ClaimSpec
from bsff.synthetic import henon_series

spec = ClaimSpec(
    claim_id="demo", signal_type="EEG", task_type="nonlinear_structure",
    sampling_rate_hz=250.0, n_channels=1, n_samples=768,
    statistic="lagged_quadratic", alpha=0.05, surrogate_count=19,
)
verdict = evaluate_claim_pipeline(spec, henon_series(768, seed=11), policy="standard")
manifest = generate_evidence_manifest(verdict)
assert len(manifest["manifest_sha256"]) == 64
```
