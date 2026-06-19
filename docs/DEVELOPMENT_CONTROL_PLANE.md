<!-- SPDX-License-Identifier: CC-BY-4.0 -->

# BSFF Development Control Plane v0.1.5

BSFF is organized as a falsification system, not as a notebook-shaped shrine to
optimism. Every claim must move through a bounded sequence of deterministic
controls before it can be exposed as a verdict.

## Development geometry

```text
ClaimSpec
  -> PolicyProfile
  -> StageRegistry
  -> EvidenceGraph
  -> PipelineVerdict
  -> ProvenanceManifest
  -> ReleaseArtifact
```

The repository is intentionally split into five planes:

1. **Signal plane**: synthetic and external signal adapters.
2. **Attack plane**: leakage, surrogate, stationarity, Bayesian evidence.
3. **Policy plane**: smoke, standard, strict profiles.
4. **Evidence plane**: stage outputs, hashes, manifests, reproducibility payloads.
5. **Repository plane**: CI, security gates, provenance, issue templates, attribution.

## Adaptive rules

- Small signals use smoke policies for fast CI feedback.
- Large multichannel signals route into stricter surrogate and stationarity checks.
- Missing optional dependencies degrade to explicit caveats, never silent success.
- Unsupported claims become `UNSUPPORTED`, not fake proof.
- All generated evidence must have a SHA-256 digest.

## Maintenance invariant

A new feature is accepted only if it adds one of these:

- stronger falsification;
- lower false rejection;
- better provenance;
- clearer caveats;
- lower CI ambiguity;
- better reproducibility.

If it only adds noise, it belongs in a slide deck, which is where weak ideas go
to become someone else's budget problem.
