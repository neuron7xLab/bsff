<!-- SPDX-License-Identifier: CC-BY-4.0 -->

# Statistical Proof Gate

`tools/validate_statistical_proof_gate.py --check` recomputes the repository proof surface from `claims.yaml`, `artifacts/release/CURRENT_TRUTH.json`, and the metric files referenced by `CURRENT_TRUTH.artifact_paths`.

The gate checks that internally verified statistical evidence has real repository artifacts for null-model results, uncertainty intervals, seed-level evidence, dataset-level output, threshold boundaries, aggregate consistency, and hashable files.

This is an internal artifact contract only. It does not assert external reproduction, R6 status, clinical validity, regulatory status, or multi-dataset replication.
