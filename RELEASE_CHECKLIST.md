<!-- SPDX-License-Identifier: CC-BY-4.0 -->

# Release Checklist

## v0.5.0 — Validation Candidate

Required:

- [ ] `claims.yaml` covers all scientific claims.
- [ ] `CLAIMS.md` explains every claim boundary.
- [ ] `data_registry.json` covers synthetic, public EEG/BCI, and external-replication slots.
- [ ] `STATISTICAL_CONTRACT.md` defines metrics, nulls, uncertainty, and failure semantics.
- [ ] `pytest tests/test_claim_registry.py tests/test_dataset_provenance.py tests/test_statistical_contract.py` passes.
- [ ] `bsff evidence verify` passes.

## v0.6.0 — External Review Candidate

Required:

- [ ] `reproduce.sh --clean --verify --run-paper` runs from a fresh checkout.
- [ ] `ARTIFACT_EVALUATION.md` is complete.
- [ ] `reviewer_quickstart.md` is sufficient without private explanation.
- [ ] release artifacts have checksums.
- [ ] SBOM and provenance evidence exist.
- [ ] DOI draft release is prepared.

## v1.0.0 — Stable Scientific Release

Required:

- [ ] public API stability contract exists.
- [ ] core claims are externally reproduced.
- [ ] release archive has DOI.
- [ ] paper is submitted or accepted.
- [ ] external reproduction report is public.
- [ ] no clinical, regulatory, therapeutic, or universal BCI overclaim is present.
- [ ] all critical CI, security, evidence, and provenance gates pass.

## Hard stop

Do not cut v1.0.0 until external hostile reproduction exists.
