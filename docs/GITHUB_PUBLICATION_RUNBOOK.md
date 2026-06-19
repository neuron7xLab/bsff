<!-- SPDX-License-Identifier: CC-BY-4.0 -->

# GitHub public repository publication runbook

This file is the manual switchboard for free GitHub open-source controls that cannot be fully enabled by files alone.

## Required repository settings after publish

1. Set visibility to public only after the local gate passes.
2. Enable GitHub Actions.
3. Enable Dependabot alerts and Dependabot security updates.
4. Enable dependency graph.
5. Enable secret scanning and push protection.
6. Enable CodeQL/code scanning alerts.
7. Import or recreate `.github/repository-ruleset-main.json` as the main branch ruleset.
8. Require pull requests, status checks, code owner review, and conversation resolution.
9. Add topics: `bci`, `eeg`, `falsification`, `surrogate-testing`, `leakage-detection`, `reproducibility`.
10. Open the first issue from `.github/ISSUE_TEMPLATE/falsification_claim.yml` only after the README caveats are visible.

## Required checks for main

- `test-py3.10`
- `test-py3.11`
- `test-py3.12`
- `build-package`
- `codeql-python`
- `pip-audit`
- `local-security-policy`
- `OpenSSF Scorecard`

## Release rule

A tag release is acceptable only if:

```bash
python tools/generate_evidence_bundle.py
python tools/validate_truth_contract.py
python tools/validate_open_source_readiness.py
python tools/check_github_actions_policy.py
python tools/scan_secrets.py
```

all pass and `artifacts/evidence_manifest.json` is attached.
