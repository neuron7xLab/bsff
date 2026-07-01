<!-- SPDX-License-Identifier: CC-BY-4.0 -->

# Artifact Evaluation Package

This file defines the reviewer-facing artifact contract for BSFF.

## Purpose

BSFF is a falsification-first framework for bounded BCI/EEG and signal-processing claims.

The artifact should let a reviewer determine:

- what claim is being tested;
- what data or generated signals are used;
- what null models are used;
- what metric and uncertainty boundary applies;
- how the result can fail;
- which files prove the run succeeded.

## Minimal reviewer path

```bash
git clone https://github.com/neuron7xLab/bsff
cd bsff
python -m pip install -e ".[dev,stats]"
pytest tests/test_claim_registry.py tests/test_dataset_provenance.py tests/test_statistical_contract.py
bsff evidence verify
```

## Full reviewer path

```bash
bash reproduce.sh --clean --verify --run-paper
```

## Expected outputs

- `REPRODUCTION_REPORT.md`;
- claim registry test PASS;
- dataset provenance test PASS;
- statistical contract test PASS;
- existing evidence verification PASS.

## Known limitations

- External hostile reproduction is not yet complete.
- R6/R7 status is not claimed by this scaffold.
- Dataset redistribution terms must be checked before any external dataset is bundled.
- v1.0 API stability is not yet declared.

## Acceptance

The artifact is R6-ready only when an external reviewer can reproduce the central evidence
from public materials without private explanation from the author.
