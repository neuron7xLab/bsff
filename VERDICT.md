<!-- SPDX-License-Identifier: CC-BY-4.0 -->

# BSFF v0.1.3 — Curator Verdict

**Status:** PHASE_1_OPERATIONAL_READY  
**Document ref:** OS-BSFF-CORE-2026.1  
**Date:** 2026-06-19

## Closed operations

- T-00 closed: MIAAFT convergence monitor added with `max_iter`, `tol`, `n_iter_actual`, `converged`, `convergence_delta`, spectrum diagnostics, covariance diagnostics, and explicit fallback policy.
- T-00b closed: the convergence monitor is now wired into the verdict path. `rank_order_surrogate_test` consumes the policy MIAAFT budget/tolerance/fallback (previously a hardcoded `n_iter=30, tol=1e-4` that never plateaued), measures every surrogate's convergence, and a non-converged null fails closed to `UNSUPPORTED` across `evaluate_claim` and the staged pipeline. Truth-contract forbidden-claim matching is now case-insensitive and the artifact `artifact_sha256` is recomputed and verified on load.
- T-01 closed: KPSS stationarity gate implemented and integrated into `evaluate_claim` evidence payload.
- T-04 partially closed: upstream feature-selection leakage detector implemented behind optional `bsff[leakage]` dependency.
- T-05 closed: GitHub Actions CI added for Python 3.10, 3.11, 3.12 plus scheduled extended lane.
- T-06 closed: `pyproject.toml` dependency/extras/script contract updated.
- T-07 closed: README hard gates updated with measured artifact-level metrics.
- Runtime artifact added: `artifacts/bsff_phase1_validation.json`.

## Machine verification

```text
pytest: 48/48 passed
bsff-validate: SURVIVED_PHASE_1_GATES
MIAAFT M=32,N=1024: converged=True, n_iter_actual=33/200, delta=0.000506
AR(1) null: p=0.40, not rejected
Hénon smoke: p=0.05, survived
Block leakage: flagged=True
```

## Remaining non-Phase-1 blockers

- TISEAN/reference validation is still open before JOSS-grade mathematical claim.
- DataLad/BIDS-App/container provenance is still Phase 3.
- Bayesian evidence is implemented as optional, but not mandatory in Phase 1 CI.

## Final verdict

The repository is ready as an executable Phase 1 falsification kernel. It is not honestly ready for JOSS, regulatory, or real EEG production deployment until external MIAAFT validation and provenance containerization are completed. The difference matters, tragically, because reality keeps refusing to obey README adjectives.


## Open-source control plane verdict

Status: `OSS_STARTER_CONTROL_PLANE_READY`.

Added repository hygiene, security automation, dependency automation, claim-truth validation, artifact hashing, GitHub publication runbook, issue/PR governance, and release provenance workflow. This does not make the science magically true. It makes unsupported claims easier to kill, which is the closest software gets to honesty before humans add marketing.


## IP / provenance status

Status: `PASS`

- Code license: `GPL-3.0-or-later`
- Docs/spec license: `CC-BY-4.0`
- Attribution controls: `NOTICE`, `AUTHORS.md`, `CITATION.cff`, SPDX headers
- Provenance controls: `artifacts/provenance_manifest.json`, `release-artifact.yml` GitHub artifact attestation, SHA-256 evidence manifest
- Anti-plagiarism gate: `python tools/validate_ip_provenance.py`

This does not prevent license violations by force. It makes origin, authorship, hashes, and release provenance explicit enough that plagiarism has to become a visible violation instead of a cute little fork costume.
