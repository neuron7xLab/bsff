<!-- SPDX-License-Identifier: CC-BY-4.0 -->

# Reproducibility contract

BSFF outputs must be deterministic for fixed seeds. Every public claim must carry:

1. `ClaimSpec`,
2. command used,
3. package version,
4. validation artifact JSON,
5. artifact SHA-256,
6. caveats.

## Local evidence command

```bash
python tools/generate_evidence_bundle.py
```

This regenerates:

- `artifacts/bsff_phase1_validation.json`
- `artifacts/evidence_manifest.json`

## Non-negotiable caveat

Phase 1 evidence is smoke-level engineering validation. It is not external MIAAFT validation, not clinical validation, not regulatory validation, and not proof that a BCI model works. It proves that this repository can execute the configured falsification gates and disclose their outputs.
