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
