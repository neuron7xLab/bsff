# CI Observability Evidence

## Problem

Workflow isolation preserves hermeticity but hides duplicated setup cost and cache effectiveness.

## Non-goals

- no workflow monolith
- no skipped validation
- no weakened provenance/security
- no fake cost claims

## Metrics

- wall time
- CPU time
- max RSS
- I/O
- network
- cache hit/miss
- longitudinal trend
- provenance depth

## Evidence Matrix

| Claim | Falsifier | Instrumentation | Artifact | Verdict |
|---|---|---|---|---|
| every Python workflow inventoried | workflow absent from inventory | `tools/ci/inventory_workflows.py` | `artifacts/ci/workflow_inventory.json` | fail closed |
| every expensive step measured | missing step telemetry | `tools/ci/measure_step.py` | `artifacts/ci/steps/**.json` | fail closed |
| cache hit/miss visible | dependency setup lacks cache telemetry | `tools/ci/emit_cache_telemetry.py` | `artifacts/ci/cache/**.json` | fail closed |
| peak RSS visible where supported | null RSS without reason | `resource.getrusage` | step telemetry | fail closed |
| CPU time visible | missing CPU time | `resource.getrusage` | step telemetry | fail closed |
| I/O best-effort visible | missing availability state | procfs snapshot | step telemetry | available or unavailable with reason |
| network best-effort visible | missing availability state | procfs snapshot | step telemetry | available or unavailable with reason |
| longitudinal baseline supported | requested baseline absent | aggregator baseline mode | `artifacts/ci/history/ci_observability_baseline.json` | fail when required |
| Sigstore/attestation skipped state classified | skipped state unclassified | `tools/ci/classify_provenance_depth.py` | `artifacts/ci/provenance_depth.json` | policy gap or fail |
| no existing validation gate removed | workflow diff removes gate | workflow review | workflow files | fail closed |
| hermeticity preserved | workflows collapsed into monolith | workflow inventory | workflow files | fail closed |

Unsupported platform metrics must be encoded as unavailable with reason. No cost reduction claim is valid until at least two comparable runs exist.
