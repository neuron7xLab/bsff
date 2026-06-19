<!-- SPDX-License-Identifier: CC-BY-4.0 -->

# BSFF Development Package

This repository is packaged for maintainable open-source development from day zero.

## Local command set

```bash
python -m venv .venv
. .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -e '.[dev,leakage,stats]'
python -m pytest tests/ -v --tb=short
python tools/validate_architecture_contract.py
python tools/validate_truth_contract.py
python tools/validate_open_source_readiness.py
python tools/validate_ip_provenance.py
python tools/check_github_actions_policy.py
python tools/scan_secrets.py
python -m build
```

## Change taxonomy

| Change type | Required checks |
|---|---|
| Mathematical kernel | unit tests, architecture contract, evidence artifact |
| New detector | detector fixture, false-positive test, docs update |
| New policy | policy validation, adaptive geometry test |
| Workflow change | actions policy, secret scan, least-permission review |
| Documentation claim | truth-contract validation, citation/provenance update |
| Release | build, provenance manifest, artifact attestation |

## Maintainer rule

A PR is not “done” when tests pass. It is done when the claim, runtime behavior, evidence artifact, and README all describe the same reality. Primitive, apparently.

## Architectural boundaries

- `schemas.py`: public claim/verdict contracts.
- `policy.py`: runtime thresholds and adaptive geometry.
- `registry.py`: deterministic stage ordering.
- `stages.py`: composable falsification stages.
- `pipeline.py`: collapse semantics and evidence graph generation.
- `validation.py`: artifact acceptance contract.
- `tools/*`: repository-level gates.

## Release posture

Before publishing a tag:

```bash
python -m pytest tests/ -v --tb=short
python tools/validate_architecture_contract.py
bsff-validate --output artifacts/bsff_phase1_validation.json
python tools/generate_provenance_manifest.py
python tools/validate_ip_provenance.py
python -m build
```

The release workflow then builds artifacts and generates GitHub artifact attestations.
