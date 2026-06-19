<!-- SPDX-License-Identifier: CC-BY-4.0 -->

# Provenance and Attribution Contract

## Canonical attribution

Use this attribution when redistributing, discussing, evaluating, forking, packaging, or publishing derivative work:

```text
BSFF: BCI Signal Falsification Framework
Author: Yaroslav Vasylenko / neuron7xLab
Repository: https://github.com/neuron7xLab/bsff
Code license: GPL-3.0-or-later
Documentation/specification license: CC-BY-4.0
Citation: CITATION.cff
```

## Machine-verifiable records

- `artifacts/provenance_manifest.json`: deterministic source and workflow hashes.
- `artifacts/evidence_manifest.json`: validation artifact hash and tracked file hashes.
- `release-artifact.yml`: GitHub build provenance attestation for release distributions.
- `NOTICE`: human-readable attribution and non-endorsement statement.
- File headers: SPDX license and copyright markers.

## Required change notice

Derivative works must mark modified files and must not imply endorsement by the original author.

Recommended modification line:

```text
Modified from BSFF by <name/org>, <date>, changes: <summary>.
```
