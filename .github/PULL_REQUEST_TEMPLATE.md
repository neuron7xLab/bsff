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

## Research-grade validation (OpenAI-2026 grid)

- [ ] tests run (`pytest -m "not slow"` + `tests/property` + `tests/adversarial`)
- [ ] mutation report attached and 8/8 killed (`artifacts/adversarial/mutation_kill_report.json`)
- [ ] statistical power profile within thresholds (`artifacts/statistics/power_profile.json`)
- [ ] artifact hashes / SBOM regenerated (`artifacts/sbom/`, `*.sha256`)
- [ ] schema changes documented (or none)
- [ ] public API changes documented in `docs/API_CONTRACT.md` (or none)
- [ ] known limitations stated below

### Known limitations

<!-- what this change does NOT prove -->
