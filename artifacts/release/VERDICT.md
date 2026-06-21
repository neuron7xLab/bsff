# BSFF Release Evidence Bundle

- Tool version: `0.4.0`
- Command: `bsff release-check --strict`
- Python: `3.12.3`
- Strict evidence path: `True`
- **Release verdict: RELEASE_READY**

## Gates

| Gate | Required | Result |
| --- | --- | --- |
| operational-kernel-selftest | True | PASS |
| architecture-contract | True | PASS |
| truth-contract | True | PASS |
| open-source-readiness | True | PASS |
| ip-provenance | True | PASS |
| markdown | True | PASS |
| github-actions-policy | True | PASS |
| secret-scan | True | PASS |
| provenance-manifest | True | PASS |
| tisean-reference | True | PASS |
| real-eeg-case | True | PASS |
| status-sync | True | PASS |

## Pinned artifacts

| Artifact | Present | sha256 |
| --- | --- | --- |
| `artifacts/bsff_phase1_validation.json` | True | `0710770017bc7278…` |
| `artifacts/provenance_manifest.json` | True | `27ca373f83647b5e…` |
| `artifacts/tisean_validation.json` | True | `7b609387dc7bdbca…` |
| `artifacts/real_eeg_case/verdict.json` | True | `8bc5414765adb3f9…` |
| `artifacts/real_eeg_case/manifest.json` | True | `3a0c3f94a591ea98…` |
| `STATUS.md` | True | `294f41e8bfa76e91…` |
