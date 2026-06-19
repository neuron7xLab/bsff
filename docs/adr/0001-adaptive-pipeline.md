<!-- SPDX-License-Identifier: CC-BY-4.0 -->

# ADR-0001: Use an adaptive pipeline instead of direct monolithic evaluation

## Status

Accepted.

## Context

The initial implementation exposed `evaluate_claim()` as a direct function. That was useful for a kernel smoke test, but it made the architecture hard to extend safely. Adding stationarity gates, leakage stages, Bayesian evidence, calibration, and provenance would either bloat one function or scatter verdict logic across modules.

## Decision

Introduce:

- `PolicyProfile`
- `adapt_policy_for_signal()`
- `StageRegistry`
- `StageResult`
- `EvidenceGraph`
- `FalsificationPipeline`
- `PipelineVerdict`

The old `evaluate_claim()` remains as a compatibility path. New development should target `evaluate_claim_pipeline()`.

## Consequences

Positive:

- deterministic stage topology,
- explicit policy thresholds,
- easier detector addition,
- hashable evidence graph,
- clean CI architecture contract.

Negative:

- more files,
- more concepts,
- fewer opportunities to pretend a 300-line god function is “simple”.
