<!-- SPDX-License-Identifier: CC-BY-4.0 -->

## Summary

<!-- what + why -->

## Merge discipline checklist

- [ ] fast matrix green (test-py3.10/3.11/3.12)
- [ ] slow-tests green
- [ ] security green (codeql, pip-audit, local-security-policy)
- [ ] zizmor green
- [ ] build-package green
- [ ] truth-contract green
- [ ] artifact schema green (no stale artifacts)
- [ ] STATUS + MANIFEST regenerated and in sync
- [ ] no admin bypass (or `docs/ADMIN_BYPASS_WAIVER.md` entry filled)

## Risk / rollback

<!-- risk, and how to revert -->

## Owner-required items

<!-- anything only the repo owner can do (e.g. ruleset changes) -->

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
