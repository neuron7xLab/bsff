<!-- SPDX-License-Identifier: CC-BY-4.0 -->

# Reviewer Quickstart

This quickstart is for an external reviewer who has no private context from the author.

## Minimal gate

```bash
git clone https://github.com/neuron7xLab/bsff
cd bsff
python -m pip install -e ".[dev,stats]"
pytest tests/test_claim_registry.py tests/test_dataset_provenance.py tests/test_statistical_contract.py
bsff evidence verify
```

## Full gate

```bash
bash reproduce.sh --clean --verify --run-paper
```

## What to inspect first

1. [`claims.yaml`](claims.yaml) — machine-readable claim scope and failure semantics.
2. [`CLAIMS.md`](CLAIMS.md) — human-readable claim boundary.
3. [`data_registry.json`](data_registry.json) — dataset provenance and external-replication gap.
4. [`STATISTICAL_CONTRACT.md`](STATISTICAL_CONTRACT.md) — null, uncertainty, and failure requirements.
5. [`ARTIFACT_EVALUATION.md`](ARTIFACT_EVALUATION.md) — artifact review contract.

## Reviewer verdict options

| Verdict | Meaning |
|---|---|
| PASS | The stated claim reproduced under public instructions. |
| PARTIAL | The software runs, but one evidence or documentation boundary is incomplete. |
| FAIL | The claim cannot be reproduced or exceeds the evidence. |
| OUT_OF_SCOPE | The claim is clinical, regulatory, therapeutic, or otherwise outside BSFF's evidence boundary. |

## Required reviewer note

A valid external reproduction report must state whether the reviewer used any private
author explanation. R6 requires no private explanation.
