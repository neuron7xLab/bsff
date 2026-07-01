<!-- SPDX-License-Identifier: CC-BY-4.0 -->

# Supply Chain and Release Integrity Contract

BSFF's scientific claims depend on release integrity. A falsification artifact is not
elite research software if its build origin, dependencies, and release artifacts cannot be
audited.

## Required controls

- pinned GitHub Actions;
- least-privilege `GITHUB_TOKEN` permissions;
- CodeQL or equivalent static-analysis gate;
- dependency audit;
- secret scan;
- SBOM;
- release artifact checksums;
- provenance attestation where supported;
- documented vulnerability disclosure path;
- reproducible release checklist.

## Failure conditions

The release is not R6/R7-ready if:

- release artifacts are unsigned or lack checksums;
- dependency tree is unknown;
- CI permissions are broader than required;
- actions are unpinned;
- SBOM is missing;
- high/critical dependency vulnerability is unresolved;
- provenance cannot be verified;
- scientific artifact hashes drift without a declared freeze or regeneration.

## Starter verification

The current scaffold does not claim final supply-chain maturity. It creates the explicit
contract that future release gates must enforce.
