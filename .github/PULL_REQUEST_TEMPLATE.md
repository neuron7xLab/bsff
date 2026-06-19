<!-- SPDX-License-Identifier: CC-BY-4.0 -->

## Change class

- [ ] Runtime/kernel logic
- [ ] Validation/test gate
- [ ] Documentation/truth disclosure
- [ ] CI/security/supply-chain
- [ ] Refactor only

## Evidence contract

- [ ] `python -m pytest tests/ -v --tb=short` passes
- [ ] `bsff-validate --output artifacts/bsff_phase1_validation.json` passes
- [ ] `python tools/validate_truth_contract.py` passes
- [ ] No claim of clinical/regulatory/TISEAN validation unless backed by artifact

## Falsification impact

Describe which claim this change makes harder to fake:

## Risks / caveats

List any remaining caveat. Empty caveats are suspicious. Reality rarely signs blank forms.
