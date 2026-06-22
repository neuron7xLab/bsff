<!-- SPDX-License-Identifier: CC-BY-4.0 -->
<!-- Copyright (c) 2026 Yaroslav Vasylenko / neuron7xLab -->

# Canonical artifact schema

A JSON artifact becomes **governed** by declaring `schema_version`. Governed
artifacts are validated by `tools/validate_artifact_schema.py` (in CI, the release
gate, and `make lab-99`) and may never contradict the single sources of truth.

## Governed-artifact contract

| field | rule |
|-------|------|
| `schema_version` | required, non-empty (e.g. `bsff.manifest/v1`) — this is what makes the artifact governed |
| `version` / `package_version` | if present, must equal `pyproject.toml` version |
| `test_count` | if present, must equal `STATUS.md` live count |

Recommended (provenance) fields for release-time artifacts, added by generators
with `--ci` from the environment (kept out of the deterministic committed core so
in-repo `--check` stays stable): `commit_sha`, `workflow_run_id`,
`generated_at_utc`, `generator_script`.

## Why this shape

The original defect was a hand-edited `MANIFEST.json` claiming version 0.1.4 /
"80/80 passed" while the truth was 0.4.0 / 373. <!-- count-literal-ok: illustrative example of the forbidden pattern -->
This validator is the **generic**
guard against that class: any governed artifact whose `version` or `test_count`
drifts from pyproject/STATUS fails CI. Adoption is opt-in per artifact (declare
`schema_version`); ungoverned artifacts are listed for coverage, never passed off
as verified.

Currently governed: `artifacts/MANIFEST.json` (and, once their PRs land,
`governance_status.json` and `actions_99_scorecard.json`).

## Full governed-artifact contract (PR-67)

A governed artifact (one that declares `schema_version`) must now also describe
itself with these **required** fields:

```text
schema_version   artifact_type   package   generator   verdict
```

Drift guards remain: `version`/`package_version` must equal pyproject; `test_count`
must equal STATUS.

**Volatile provenance** (`commit_sha`, `workflow_run_id`, `generated_at_utc`) is
required **only** when an artifact declares `ci_emitted: true`, so the committed,
in-repo core stays deterministic and `--check`-able. CI/release runs add these via
`--ci`. Currently governed: `MANIFEST.json`, `actions_99_scorecard.json`,
`governance_status.json`. Ungoverned artifacts are listed for coverage, never
silently accepted.
