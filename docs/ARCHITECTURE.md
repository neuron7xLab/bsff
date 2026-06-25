<!-- SPDX-License-Identifier: CC-BY-4.0 -->

# BSFF Architecture v0.1.4 — Adaptive Falsification Control Plane

BSFF is structured as a falsification system, not as a pile of helper functions. The core invariant is simple:

```text
claim + signal + policy + ordered evidence stages -> immutable verdict contract
```

A verdict is never a social statement. It is the collapse of an evidence graph into one of three machine states:

```text
SURVIVED | REFUTED | UNSUPPORTED
```

## First-principles decomposition

| Layer | Responsibility | Failure mode blocked |
|---|---|---|
| Domain contract | `ClaimSpec`, `VerdictJSON`, policy profiles | ambiguous claims |
| Geometry policy | signal shape, alpha, surrogate budget, CI runtime budget | hidden magic thresholds |
| Stage registry | ordered falsification stages | untracked execution drift |
| Evidence graph | per-stage evidence + digest | unverifiable outputs |
| Pipeline collapse | deterministic verdict reduction | narrative-driven interpretation |
| OSS control plane | CI, security, provenance, attribution | supply-chain and plagiarism fog |

## Runtime topology

```text
ClaimSpec + signal
      │
      ▼
adapt_policy_for_signal
      │
      ▼
StageRegistry[stationarity, leakage, surrogate, bayes]
      │
      ▼
EvidenceGraph(nodes + sha256)
      │
      ▼
PipelineVerdict(contract_sha256)
      │
      ├── to_dict()
      └── to_verdict_json()
```

## Dynamic policy geometry

`PolicyProfile` makes operational choices explicit:

- `alpha`
- `surrogate_count`
- `stationarity_mode`
- `bayesian_evidence`
- `miaaft_max_iter`
- `miaaft_tol`
- `miaalft_fallback`
- CI shape budgets
- warning thresholds

`adapt_policy_for_signal()` adapts the policy to the signal geometry:

```text
geometry(signal) = (n_channels, n_samples)
minimum_surrogates = ceil(1 / alpha) - 1
runtime_budget = f(policy, n_channels, n_samples)
```

This is deliberately deterministic. No hidden model, no remote service, no policy mutation after execution.

## Stage contract

Every stage returns:

```python
StageResult(
    stage_id: str,
    status: "PASS" | "FAIL" | "WARN" | "SKIP",
    fatal: bool,
    evidence: dict,
    caveats: list[str],
)
```

Stages are composable through `StageRegistry`. Duplicate stage IDs fail immediately. That prevents the classic LLM-engineered soup where two modules pretend to be the same gate and everyone claps because YAML exists.

## Default stage chain

| Order | Stage | Purpose | Fatal behavior |
|---:|---|---|---|
| 1 | `stationarity_gate` | KPSS per-channel assumption check | fatal only in strict mode |
| 2 | `leakage_gate` | external leakage detector short-circuit | fatal by default |
| 3 | `surrogate_attack` | rank-order MIAAFT/null attack | verdict-driving |
| 4 | `bayesian_evidence` | optional BF10/BF01 evidence weight | supports UNSUPPORTED split |

## Collapse semantics

```text
fatal leakage/stationarity failure -> REFUTED
surrogate rejected null -> SURVIVED
surrogate not rejected + strong/null evidence -> REFUTED
surrogate unavailable or low evidence -> UNSUPPORTED
```

The architecture does not let a result become “true” because a user wants a stronger headline. Horrible inconvenience for marketing departments.

## Extension model

To add a new detector:

1. Implement a stage with `stage_id` and `run(context) -> StageResult`.
2. Register it in `StageRegistry`.
3. Add a test that proves:
   - deterministic output,
   - expected failure behavior,
   - evidence payload shape,
   - effect on final verdict if fatal.
4. Update `docs/ARCHITECTURE.md` and `tools/validate_architecture_contract.py` if it becomes part of the default topology.

## Architecture gates

The repository contains a dedicated architecture validator:

```bash
python tools/validate_architecture_contract.py
```

It verifies:

- default stage topology,
- adaptive policy construction,
- evidence graph generation,
- deterministic contract hash,
- smoke verdict collapse.

The same gate runs in `.github/workflows/architecture.yml`.

## Non-goals

BSFF does not:

- prove BCI claims true,
- replace peer review,
- validate medical devices,
- certify clinical safety,
- hide caveats behind pleasant prose.

BSFF is a falsification control plane. Its job is to break weak claims cheaply, reproducibly, and early.

## Full repository decomposition

For a per-subsystem map of specification + purpose for everything in the repository
(`src/bsff`, `tools`, `examples`, `tests`, `docs`, workflows, artifacts) with an honest
**accuracy / clarity / logic / factuality / aesthetics / simplicity / elegance** scorecard, see
[`docs/REPOSITORY_DECOMPOSITION.md`](REPOSITORY_DECOMPOSITION.md).
