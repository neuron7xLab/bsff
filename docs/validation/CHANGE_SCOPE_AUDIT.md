<!-- SPDX-License-Identifier: CC-BY-4.0 -->
# Change-scope audit

## Scope
All changes are confined to the validation-artifact surface:
`examples/bonn_bright_line/`, `tests/bonn_bright_line/`, `docs/`, `artifacts/`,
`FORMAL_VERDICT.md`, `REPRODUCE.md`, `.gitignore`.

- **`src/` BSFF source changed:** **none**
  (`git diff --name-only origin/main~1 origin/main | grep ^src/` → empty for PR #75).
- **Raw Bonn data tracked:** **none** (`git ls-files | grep bonn_data` → empty; gitignored).

## Deliberate deviation from the execution order (Phase 8)
The order's Phase 8 asks to write the Bonn status into `STATUS.md`. In this repo `STATUS.md`
is a **generated, manifest-synced** file (`tools/generate_manifest.py`; `tests/test_manifest_sync.py`
parses a live test count from it). Overwriting it breaks the manifest/status-sync CI gates.

Per rule 19 (do not alter repo machinery unless a real reproducibility bug requires it),
the Bonn status is written to **`docs/validation/BONN_STATUS.md`** instead, and `STATUS.md`
is left in its generated repo format. `finalize_release.py` never writes `STATUS.md`.
This keeps the repository CI-green while still publishing a machine-readable bonn status.
