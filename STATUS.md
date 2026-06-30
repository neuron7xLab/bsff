<!-- SPDX-License-Identifier: CC-BY-4.0 -->
<!-- Copyright (c) 2026 Yaroslav Vasylenko / neuron7xLab -->
<!-- GENERATED FILE -->

# BSFF status register

| Field | Value |
|---|---|
| package_version | `0.4.0` |
| canonical_state | `BONN_S2_BRIGHT_LINE_ROBUSTLY_PASSED` |
| committed_test_count | **714** |
| live_collection_gate | `tools/update_status.py --verify-count --strict-status` |
| live_collection_count_source | `pytest tests/ --collect-only -p no:cacheprovider` |
| cli_subcommand_count | 18 |
| optional_extras | `dev`, `full`, `fuzz`, `leakage`, `moabb`, `security`, `stats`, `yaml` |
| truth_artifact_path | `artifacts/release/CURRENT_TRUTH.json` |
| workflow_authority | `.github/workflows/ci.yml` and GitHub Actions for the exact commit |
| release_evidence_path | `docs/PR_109_EVIDENCE.md` |
| current_truth_gate | `tools/validate_current_truth.py` |
| status_sync_gate | `tools/update_status.py --check` |
| strict_count_sync_gate | `tools/update_status.py --verify-count --strict-status` |
