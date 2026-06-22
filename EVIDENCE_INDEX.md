<!-- SPDX-License-Identifier: CC-BY-4.0 -->
<!-- Copyright (c) 2026 Yaroslav Vasylenko / neuron7xLab -->

# EVIDENCE_INDEX

Where every claim's evidence lives, and the exact command to reproduce it.

## Documents
| artifact | path |
|----------|------|
| Status (generated, single source of truth) | `STATUS.md` |
| Claim audit | `CLAIM_AUDIT.md` |
| Test-count reconciliation | `TEST_COUNT_RECONCILIATION.md` |
| Hard limitations | `LIMITATIONS_HARD.md` |
| Manuscript | `docs/MANUSCRIPT.md` |
| Constitution (invariants) | `docs/INVARIANTS.md` |
| Pipeline overview | `docs/PIPELINE.md` |
| Reviewer packet | `REVIEWER_PACKET.md` |
| Public showcase | `PUBLIC_SHOWCASE.md` |

## Validation artifacts
| artifact | path | reproduce |
|----------|------|-----------|
| Surrogate fidelity | `artifacts/surrogate_fidelity.json` | `python tools/validate_surrogate_fidelity.py` |
| Operating characteristic | `bsff.operating_characteristic` | `python tools/calibrate_operating_characteristic.py --quick` |
| Transfer-entropy OC | `artifacts/transfer_entropy_operating_characteristic.json` | `python tools/calibrate_transfer_entropy.py --quick` |
| Validation corpus v0.2.0 | `data/validation/bsff_validation_corpus_v0_2_0.npz` (+ manifest) | `python -m pytest tests/test_validation_corpus_v020_contract.py` |
| Invariants (7 axioms) | `tests/test_invariants.py` | `python -m pytest tests/test_invariants.py -q` |

## Real-data result (LOSO)
| artifact | path | reproduce |
|----------|------|-----------|
| BNCI2014_001 within-vs-LOSO | `research/bci_generalization/result_bnci2014_001_sub1-2.json` | `pip install '.[moabb]'; python research/bci_generalization/run_experiment.py --dataset BNCI2014_001 --subjects 1 2 --out r.json` |
| Harness + README | `research/bci_generalization/` | — |

## Release / provenance
| artifact | locator |
|----------|---------|
| Release v0.4.0 | https://github.com/neuron7xLab/bsff/releases/tag/v0.4.0 |
| SLSA provenance asset | `bsff-v0.4.0.intoto.jsonl` · sha256 `94b5187d11d0defefea17529c5e6f01a7f6b2732d6aa7e2936ebd4c85905f387` |
| Verify | `gh release download v0.4.0 --pattern '*.intoto.jsonl' && sha256sum bsff-v0.4.0.intoto.jsonl` |

## CI
| what | where |
|------|-------|
| Workflows | `.github/workflows/ci.yml`, `release-artifact.yml`, `security.yml`, `provenance.yml`, `scorecard.yml` |
| Runs | https://github.com/neuron7xLab/bsff/actions |
| Per-commit status | the GitHub Actions run for that commit SHA |

## One-command reproduction
```bash
git clone https://github.com/neuron7xLab/bsff && cd bsff
pip install -e '.[dev]'
python -m pytest -q                       # full suite green — live count in STATUS.md
python tools/update_status.py --check     # STATUS.md in sync
python tools/validate_surrogate_fidelity.py
```
