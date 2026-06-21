<!-- SPDX-License-Identifier: CC-BY-4.0 -->

<div align="center">

```text
██████╗ ███████╗███████╗███████╗
██╔══██╗██╔════╝██╔════╝██╔════╝
██████╔╝███████╗█████╗  █████╗  
██╔══██╗╚════██║██╔══╝  ██╔══╝  
██████╔╝███████║██║     ██║     
╚═════╝ ╚══════╝╚═╝     ╚═╝     
```

# BSFF — BCI Signal Falsification Framework

**A mathematical guillotine for neuroscience hype.**

[![CI](https://img.shields.io/github/actions/workflow/status/neuron7xLab/bsff/ci.yml?branch=main&style=flat-square&label=CI&color=2d2d2d)](https://github.com/neuron7xLab/bsff/actions/workflows/ci.yml)
[![Security](https://img.shields.io/github/actions/workflow/status/neuron7xLab/bsff/security.yml?branch=main&style=flat-square&label=security&color=2d2d2d)](https://github.com/neuron7xLab/bsff/actions/workflows/security.yml)
[![Provenance](https://img.shields.io/github/actions/workflow/status/neuron7xLab/bsff/provenance.yml?branch=main&style=flat-square&label=provenance&color=2d2d2d)](https://github.com/neuron7xLab/bsff/actions/workflows/provenance.yml)
[![Tests](https://img.shields.io/badge/tests-see%20STATUS.md-2d6a2d?style=flat-square)](STATUS.md)
[![Python](https://img.shields.io/badge/python-3.10%2B-2d2d2d?style=flat-square)](pyproject.toml)
[![License](https://img.shields.io/badge/code-GPL--3.0--or--later-2d2d2d?style=flat-square)](LICENSE)
[![Docs](https://img.shields.io/badge/docs-CC--BY--4.0-2d2d2d?style=flat-square)](NOTICE)
[![SPDX](https://img.shields.io/badge/SPDX-enforced-2d2d2d?style=flat-square)](tools/validate_ip_provenance.py)

**BSFF does not trust. It tests.**

</div>

---

## The problem

Every week, a company, paper, demo, or investor deck claims to read intention, decode emotion, restore movement, or extract cognitive state from neural signals.

Most claims are never independently stress-tested. Some collapse to chance after one leakage path, temporal artifact, global normalization leak, or non-stationary signal assumption is removed. Apparently, reality still insists on being measured rather than admired in a slide deck.

BSFF automates that scrutiny. You give it a claim and a signal. It returns a machine-readable verdict.

A claim can only be labelled `SURVIVED`, `REFUTED`, or `UNSUPPORTED`. Never “proven true”. That wording is intentional.

---

## What it does

```text
ClaimSpec
   │
   ▼
StationarityGate ──► LeakageProbe ──► SurrogateEngine ──► VerdictJSON
   │                     │                  │                 │
   │              KPSS/channel check   MIAAFT null       SURVIVED
   │              block-design leak?   convergence       REFUTED
   │              feature MI leak?     diagnostics       UNSUPPORTED
   └──────────────────────── evidence + caveats ───────────────► JSON artifact
```

**Four attacks on every claim:**

1. **Stationarity** — does the signal violate the assumptions needed for surrogate testing?
2. **Leakage** — does accuracy depend on a methodological artifact?
3. **Surrogate** — is the signal distinguishable from cross-channel, spectrally matched null data?
4. **Verdict** — is the output reproducible, evidence-backed, and honest about caveats?

BSFF does **not** prove BCI claims. It tries to break them before someone mistakes a leaderboard artifact for neuroscience.

---

## The full pipeline

The four-attack signal verdict above is the core. Around it, BSFF is now a
complete claim-adjudication engine — from a raw recording or a publication's
claims through to a tamper-evident verdict ledger and a human-readable report.
One chain, fail-closed at every link; see [`docs/PIPELINE.md`](docs/PIPELINE.md).

```
raw signal (.edf/.bdf/.csv/.npy) ─► normalize ─► raw-signal guard ─┐
publication claim (verbatim quote) ─► anchor ─► classify tier ─────┤
                                                                   ▼
        route { empirical → surrogate battery | causal → conditional transfer entropy
              | logical → argument structure  | else → quarantine }
                                                                   ▼
                       verdict ─► hash-chained ledger ─► HTML/Markdown report
```

| command | what it does |
|---------|--------------|
| `bsff falsify` | falsify one signal claim (ClaimSpec + signal) |
| `bsff normalize` | read raw EDF/EDF+/BDF → canonical array (pure Python, zero deps) |
| `bsff adjudicate-data` | data-driven verdict on a raw signal you supply |
| `bsff ingest --arxiv <id>` | fetch a paper's abstract as a provenance-stamped source |
| `bsff adjudicate` | anchor, classify, route, and ledger a source's claims |
| `bsff adjudicate-batch` | adjudicate a corpus, with extraction accountability |
| `bsff render` | render a verdict report as HTML or Markdown |
| `bsff ledger-verify` | check a truth ledger's hash-chain integrity |

The raw-signal guard refuses feature tables, accuracy matrices, and labels — it
tests the signal, not someone's preprocessing. No disposition is ever "true":
the strongest an empirical claim earns is *survived falsification under stated
conditions*. Details: [`docs/ADJUDICATION.md`](docs/ADJUDICATION.md),
[`docs/TRANSFER_ENTROPY.md`](docs/TRANSFER_ENTROPY.md),
[`docs/DATASETS.md`](docs/DATASETS.md).

---

## Current status

**Version:** `v0.4.0`  
**State:** Phase 1 kernel + adaptive architecture + external claim/EEG adjudication + open-source security/provenance control plane  
**Repository target:** `neuron7xLab/bsff`

> The single, machine-generated source of truth for version, live test count, CLI
> surface, available evidence paths, and known blockers is [`STATUS.md`](STATUS.md)
> — regenerated by `python tools/update_status.py` and gated in CI
> (`tools/update_status.py --check`). Do not hand-edit status numbers here.

This repository is ready to be published as an open-source project with CI, security scanning, attribution controls, provenance manifests, issue/PR governance, and truth-contract validation.

---

## Implemented scope

```text
src/bsff/
├── schemas.py          — ClaimSpec · VerdictJSON
├── json_schema.py      — JSON Schema (draft 2020-12) export for the contracts
├── synthetic.py        — AR(1) · Hénon · block-design fixtures
├── stationarity.py     — KPSS per-channel stationarity gate
├── surrogate_engine.py — multivariate IAAFT-style surrogate engine
├── leakage_detector.py — block-design leakage · optional MI feature leakage
├── leakage_deep.py      — phase-locking + phase-amplitude-coupling leakage probes
├── bayesian.py         — optional Bayes-factor evidence layer
├── policy.py           — smoke/standard/strict adaptive policy profiles
├── registry.py         — deterministic plugin/stage registry
├── evidence.py         — hashable stage results and evidence graph
├── stages.py           — stationarity/leakage/surrogate/bayesian stages
├── pipeline.py         — adaptive falsification pipeline + verdict collapse
├── verdict_engine.py   — legacy compatibility evaluator
├── calibration.py      — surrogate-budget and rank-order calibration helpers
├── validation.py       — Phase 1 artifact contract and digest validation
├── provenance.py       — repository provenance manifest generation
├── report.py           — write VerdictJSON artifacts
└── cli.py              — bsff-validate operational gate
```

Open-source control plane:

```text
.github/workflows/
├── ci.yml               — Python 3.10/3.11/3.12 tests + truth gates
├── security.yml         — CodeQL · dependency review · pip-audit
├── scorecard.yml        — OpenSSF Scorecard
├── provenance.yml       — SPDX/provenance/attribution validation
└── release-artifact.yml — build + GitHub artifact attestations
```

Governance and protection:

```text
CODEOWNERS · Dependabot · PR template · issue templates · SECURITY.md
CONTRIBUTING.md · CODE_OF_CONDUCT.md · SUPPORT.md · CITATION.cff
NOTICE · AUTHORS.md · SPDX headers · GPL/CC-BY license texts
```

---


## v0.2.0 development package

This release adds reference-covariance surrogate validation, a published MIAAFT
benchmark matrix, a `pipeline.run()` alias, a deterministic `UNSUPPORTED` verdict
test, a MOABB falsification example, and a JOSS paper scaffold — on top of the
v0.1.5 deterministic synthetic validation corpus and development control plane.
It keeps the open-source security/provenance layer from v0.1.3 and the adaptive architecture from v0.1.4, then adds corpus validation and release-mass integrity.

```text
pytest: 80/80 passing
validation corpus: synthetic-only, non-clinical, SHA-256 pinned
package mass target: 7-10 MB
license: GPL-3.0-or-later for code; CC-BY-4.0 for documentation/specs
```

## Verified performance

Measured in the current package, not emotionally inferred, because the CPU does not care about our ambitions.

| Gate | Value | Status |
|---|---:|---|
| Test suite | 80 / 80 passed | ✓ |
| CLI validation | `SURVIVED_PHASE_1_GATES` | ✓ |
| MIAAFT M=32, N=1024 convergence | 33 / 200 iterations | ✓ tol=1e-3 |
| Verdict-path null convergence | enforced per surrogate | ✓ fail-closed → UNSUPPORTED |
| Artifact self-hash | recomputed + verified | ✓ tamper-detectable |
| Convergence delta | 0.000506 | ✓ |
| Covariance relative RMSD | 0.001307 | ✓ < 0.35 smoke threshold |
| Relative spectrum error | 0.014962 | ✓ reported, not hidden |
| AR(1) null smoke | p=0.40 | ✓ not rejected |
| Hénon nonlinear smoke | p=0.05 | ✓ survived configured attack |
| Block-design leakage fixture | flagged=True | ✓ refutable leakage path |
| Truth contract | PASS | ✓ |
| OSS readiness | PASS | ✓ |
| GitHub Actions policy | PASS | ✓ |
| Secret scan | PASS | ✓ |
| Architecture contract | PASS | ✓ |
| IP/provenance validation | PASS | ✓ |
| Markdown validation | PASS | ✓ |
| Wheel build | PASS | ✓ |

### MIAAFT performance matrix

Measured single-surrogate wall-clock on CPU (`max_iter=200`, `tol=1e-3`, `seed=0`),
reproducible via `PYTHONPATH=src python tools/benchmark_miaaft.py`. Every cell
converges; covariance fidelity is reported, not assumed.

| channels | samples | time (s) | converged | iters | rel. covariance |
|---:|---:|---:|:--:|---:|---:|
| 4  | 512  | 0.003 | ✓ | 14 | 0.0025 |
| 4  | 8192 | 0.105 | ✓ | 41 | 0.0001 |
| 8  | 4096 | 0.107 | ✓ | 49 | 0.0003 |
| 16 | 4096 | 0.314 | ✓ | 60 | 0.0002 |
| 32 | 4096 | 0.589 | ✓ | 61 | 0.0002 |
| 32 | 8192 | 1.155 | ✓ | 58 | 0.0001 |

Worst case in the 4–32 channel × 512–8192 sample grid stays well under the 30 s
budget. Full grid: `artifacts/benchmark_miaaft.json`.

The primary machine-readable validation artifact is:

```bash
artifacts/bsff_phase1_validation.json
```

The repository-level provenance manifest is:

```bash
artifacts/provenance_manifest.json
```

---


## Adaptive architecture

BSFF now has a composable architecture layer instead of a single monolithic evaluator.

```text
ClaimSpec + signal
      │
      ▼
adapt_policy_for_signal()
      │
      ▼
StageRegistry[stationarity, leakage, surrogate, bayes]
      │
      ▼
EvidenceGraph(nodes + sha256)
      │
      ▼
PipelineVerdict(contract_sha256)
```

Use the new pipeline API for development:

```python
from bsff import ClaimSpec, evaluate_claim_pipeline
from bsff.synthetic import henon_series

spec = ClaimSpec(
    claim_id="demo_pipeline",
    signal_type="EEG",
    task_type="nonlinear_structure",
    sampling_rate_hz=250.0,
    n_channels=1,
    n_samples=768,
    statistic="lagged_quadratic",
    surrogate_count=19,
)

result = evaluate_claim_pipeline(spec, henon_series(n_samples=768), policy="smoke")
print(result.verdict, result.contract_sha256)
```

Policy profiles are explicit: `smoke`, `standard`, and `strict`. The architecture contract is validated by:

```bash
python tools/validate_architecture_contract.py
```

See `docs/ARCHITECTURE.md` and `docs/DEVELOPMENT_PACKAGE.md`.

## Quickstart

```bash
git clone https://github.com/neuron7xLab/bsff
cd bsff
python -m venv .venv
. .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -e '.[dev,leakage]'
python -m pytest tests/ -v --tb=short
```

Expected current result:

```text
26 passed
```

---

## Install

From PyPI (once the first release is published via Trusted Publishing):

```bash
python -m pip install bsff
```

From source, minimal runtime install:

```bash
python -m pip install -e .
```

Development install:

```bash
python -m pip install -e '.[dev,leakage]'
```

Optional statistical layer:

```bash
python -m pip install -e '.[dev,leakage,stats]'
```

Dependency model:

| Layer | Dependencies | Purpose |
|---|---|---|
| Core | NumPy, SciPy, statsmodels | signal/surrogate/stationarity kernel |
| Dev | pytest, pytest-cov, ruff, build | tests, quality, packaging |
| Leakage extra | scikit-learn | MI-based upstream feature-selection leakage detector |
| Stats extra | pingouin | JZS Bayes-factor path |

---

## A claim in five lines

```python
from bsff import ClaimSpec, evaluate_claim
from bsff.synthetic import henon_series

spec = ClaimSpec(
    claim_id="demo_henon_nonlinear_structure",
    signal_type="EEG",
    task_type="nonlinear_structure",
    sampling_rate_hz=250,
    n_channels=1,
    n_samples=768,
    statistic="lagged_quadratic",
)

verdict = evaluate_claim(spec, henon_series())
print(verdict.verdict, verdict.p_value)
# SURVIVED 0.05
```

---

## Falsify an external claim from the command line

The library above tests an in-memory signal. To aim BSFF at *someone else's*
published claim and dataset, use the `falsify` subcommand: it loads a `ClaimSpec`
file and a raw signal file, runs the fail-closed pipeline, and emits a
provenance-stamped verdict case-file.

```bash
# verdict to stdout
bsff falsify --claim claim.json --signal signal.csv --policy strict

# persist a self-verifying dossier (byte-level signal hash + artifact_sha256)
bsff falsify --claim claim.json --signal signal.npy --policy strict --out case.json
```

- `--claim` accepts `.json` (or `.yaml` with the `yaml` extra). Unknown fields are
  rejected fail-closed.
- `--signal` accepts `.npy`, `.csv`, or `.tsv`; the shape must match the claim's
  `n_channels × n_samples` exactly or the run aborts.
- A runnable, reproducible example lives in [`examples/falsify/`](examples/falsify/).

---

## Case studies

A **case** aims BSFF at a famous, externally-recognizable claim and records a
hash-bound verdict. Cases live in [`cases/`](cases/); each ships a falsifiable
reduction of the claim, a pre-registered split/control battery, and a machine-readable
dossier.

| case | target claim | verdict |
|---|---|---|
| [001 — PhysioNet EEGNet generalization](cases/001_physionet_eegnet/) | within/global-validation motor-imagery accuracy reflects *generalizable* decoding | **REFUTED** |

BSFF-CASE-001 attacks the cross-subject generalization that within-subject EEGMMI
numbers are often read to imply. On real PhysioNet data a decoder that is significantly
above chance within subjects falls to chance leave-one-subject-out (permutation
p = 0.98), with the label-shuffle control passing. The same harness is shown to be
two-sided on labelled ground truth — it returns `SURVIVED` when a genuinely
subject-shared signal is present and `UNSUPPORTED` on noise — so the `REFUTED` verdict
is not a one-sided artefact. This is **not** a claim that motor imagery is undecodable;
it falsifies the *generalization inference*, not the within-subject result. See
[`cases/001_physionet_eegnet/REPORT.md`](cases/001_physionet_eegnet/REPORT.md).

```bash
PYTHONPATH=src python cases/001_physionet_eegnet/run_case.py \
    --source synthetic --config headline --out /tmp/case001   # offline ground-truth
```

---

## Verdict schema

```json
{
  "claim_id": "demo_henon_nonlinear_structure",
  "verdict": "SURVIVED",
  "p_value": 0.05,
  "original_statistic": 0.670,
  "surrogate_min": 0.041,
  "surrogate_max": 0.144,
  "leakage_flags": {},
  "caveats": [
    "Low surrogate count: suitable for CI smoke, not final evidence."
  ]
}
```

Verdict semantics:

| Verdict | Meaning |
|---|---|
| `SURVIVED` | Claim survived the configured falsification attacks. |
| `REFUTED` | Leakage or null-model evidence broke the claim. |
| `UNSUPPORTED` | Available evidence is too weak or underpowered to classify as survived/refuted. |

---

## Operational commands

Three commands tell a new user everything about the state of an install:

```bash
python -m pip install -e '.[dev,leakage,stats,yaml]'   # install + strict evidence path
bsff doctor                                             # which evidence paths are available
bsff release-check --strict --output artifacts/release  # full evidence bundle + verdict
```

| Command | Purpose |
| --- | --- |
| `bsff doctor [--require-strict]` | Environment health + which evidence paths are available |
| `bsff capabilities [--out F]` | Machine-readable dependency/capability report |
| `bsff validate` | Operational-kernel self-validation + capability check |
| `bsff falsify --claim C --signal S --policy strict` | Falsify an external claim (strict fails closed without its evidence path) |
| `bsff reproduce --case CASE.json` | Re-run a saved verdict case-file and confirm byte-identical reproduction |
| `bsff release-check --strict` | Run the gate battery → one `artifacts/release/` evidence bundle |
| `bsff bids-app --bids-dir D --output-dir O --participant-label 01` | BIDS-App: falsify EEG recordings from a BIDS dataset |

Full reference: [`docs/CLI_CONTRACT.md`](docs/CLI_CONTRACT.md).

## One-command local gate

```bash
python -m pip install -e '.[dev,leakage,stats,yaml]' \
  && python -m pytest tests/ -v --tb=short \
  && bsff-validate --output artifacts/bsff_phase1_validation.json \
  && bsff doctor --require-strict \
  && python tools/validate_truth_contract.py \
  && python tools/validate_open_source_readiness.py \
  && python tools/check_github_actions_policy.py \
  && python tools/scan_secrets.py \
  && python tools/generate_provenance_manifest.py \
  && python tools/validate_ip_provenance.py \
  && python tools/validate_markdown.py \
  && python tools/validate_tisean_reference.py \
  && python tools/validate_real_eeg_case.py \
  && python tools/update_status.py --check \
  && bsff release-check --strict --output artifacts/release \
  && python -m build
```

This is the local “do not embarrass yourself in public” command.

---

## Documentation

| Topic | Document |
| --- | --- |
| Status / single source of truth | [`STATUS.md`](STATUS.md) |
| Methodology (claim → surrogate → verdict) | [`docs/METHODOLOGY.md`](docs/METHODOLOGY.md) |
| Validation evidence (tiered) | [`docs/VALIDATION.md`](docs/VALIDATION.md) |
| False-positive control / operating characteristic | [`docs/FALSE_POSITIVE_CONTROL.md`](docs/FALSE_POSITIVE_CONTROL.md) · [`docs/OPERATING_CHARACTERISTIC.md`](docs/OPERATING_CHARACTERISTIC.md) |
| External surrogate reference (TISEAN-class) | [`docs/TISEAN_VALIDATION.md`](docs/TISEAN_VALIDATION.md) |
| Real EEG / BIDS validation path | [`docs/REAL_EEG_VALIDATION.md`](docs/REAL_EEG_VALIDATION.md) · [`docs/BIDS_APP.md`](docs/BIDS_APP.md) |
| Container / DataLad provenance | [`docs/DATALAD_PROVENANCE.md`](docs/DATALAD_PROVENANCE.md) |
| EEG artifact battery | [`docs/EEG_ARTIFACT_BATTERY.md`](docs/EEG_ARTIFACT_BATTERY.md) |
| Out-of-scope / invalid use | [`docs/INVALID_USE.md`](docs/INVALID_USE.md) |
| CLI contract | [`docs/CLI_CONTRACT.md`](docs/CLI_CONTRACT.md) |

---

## Architecture

The scientific core is a multivariate IAAFT-style surrogate engine. Unlike naive univariate surrogates, BSFF preserves cross-channel structure so multichannel BCI claims are attacked against a more physically plausible null.

```text
Input signal X ∈ R^(channels × samples)
   │
   ├── stationarity diagnostics
   ├── leakage diagnostics
   ├── common-phase surrogate attack
   ├── convergence monitor
   ├── covariance/spectrum diagnostics
   └── deterministic VerdictJSON
```

Design principle:

> BSFF is not a neuroscience decoder. It is an epistemic gateway for claims about neural decoders.

---

## Security and anti-plagiarism controls

BSFF is open source, not authorless source. Tiny distinction, apparently still beyond the reach of many copy-paste mammals.

| Control | File / workflow | Purpose |
|---|---|---|
| Code license | `LICENSE`, `LICENSES/GPL-3.0-or-later.txt` | Copyleft source redistribution terms |
| Docs/spec license | `LICENSES/CC-BY-4.0.txt`, `NOTICE` | Attribution for documentation/specification reuse |
| Author identity | `AUTHORS.md`, `NOTICE`, `CITATION.cff` | Canonical authorship marker |
| SPDX headers | source, docs, workflows, tools | Machine-readable license metadata |
| Provenance manifest | `artifacts/provenance_manifest.json` | SHA-256 hashes of tracked source/docs/workflows |
| IP gate | `tools/validate_ip_provenance.py` | Fails if attribution/provenance controls are removed |
| Release attestation | `.github/workflows/release-artifact.yml` | Build provenance for release artifacts |
| Secret scan | `tools/scan_secrets.py` + GitHub secret scanning | Low-cost pre-push and platform-side secret defense |
| Supply chain | Dependabot, dependency review, pip-audit | Dependency drift and vulnerability control |
| Code scanning | CodeQL | Static security analysis |
| Scorecard | OpenSSF Scorecard | Public repo security posture signal |

License model:

- Code: `GPL-3.0-or-later`.
- Documentation/specifications/diagrams/text: `CC-BY-4.0`, unless a file-level SPDX marker states otherwise.
- Required attribution files: `NOTICE`, `AUTHORS.md`, `CITATION.cff`, `LICENSE`, `LICENSES/*`, and file-level SPDX headers.
- Release provenance: `release-artifact.yml` generates attestations, while `artifacts/provenance_manifest.json` records SHA-256 digests.

---

## Roadmap

```text
v0.1.0  kernel: MIAAFT · LeakageProbe · VerdictJSON
v0.1.1  Phase 1: convergence monitor · stationarity gate · validation artifact
v0.1.2  OSS control plane: CI · security · Scorecard · Dependabot · evidence gates
v0.1.3  IP/provenance: GPL · CC-BY · SPDX · NOTICE · citation · attestations
v0.2.0  reference covariance validation · benchmark matrix · run() alias ·
        deterministic UNSUPPORTED · MOABB example · JOSS paper scaffold
v0.3.0  frequentist-AND-Bayesian conjunction gate · measured operating
        characteristic · SLSA release provenance · hash-pinned actions  [current]
v0.4.0  BIDS-App container · DataLad provenance · real EEG dataset path
v1.0.0  JOSS submission candidate
```

---

## Scientific position

BSFF is not a mind-reading project. It is not a clinical device. It is not a regulatory artifact. It is not a vendor benchmark.

It is an epistemological instrument: a deterministic falsification harness for claims about neural signal decoding.

The strength of evidence is not in how loudly a claim is made. It is in how hard it survives an attempt to destroy it.

---

## Known limits

- MIAAFT is **not externally validated against TISEAN**; this remains the hard pre-JOSS gate.
- The rank-order p-value is anti-conservative for strongly autocorrelated linear-Gaussian nulls (finite-N IAAFT bias). The shipped frequentist-AND-Bayesian conjunction gate restores nominal specificity (measured FPR ≤ α at full power); see [`docs/OPERATING_CHARACTERISTIC.md`](docs/OPERATING_CHARACTERISTIC.md).
- CI thresholds are smoke/engineering thresholds, **not regulatory validation**.
- BSFF does **not** prove BCI claims; it only reports whether they survived the configured falsification attacks.
- Current validation fixtures are synthetic; real EEG/BIDS validation remains Phase 3.
- BIDS-App, DataLad provenance, containerization, and GPU/JAX batched FFT are not implemented yet.
- MI-based leakage detection requires `bsff[leakage]`.
- JZS Bayes factor requires `bsff[stats]`; without `pingouin`, the fallback is a lightweight approximation path.

---

## Citations

The methodology is grounded in:

- Prichard & Theiler (1994). *Generating Surrogate Data for Time Series with Several Simultaneously Measured Variables.* Physical Review Letters, 73:951.
- Schreiber & Schmitz (1996). *Improved Surrogate Data for Nonlinearity Tests.* Physical Review Letters, 77:635.
- Schreiber & Schmitz (2000). *Surrogate time series.* Physica D, 142:346.
- Theiler et al. (1992). *Testing for nonlinearity in time series.* Physica D, 58:77.
- Kugiumtzis (2002). *Surrogate data test for nonlinearity including nonmonotonic transforms.* Physical Review E, 62:R25.
- Li et al. (2021). *The Perils and Pitfalls of Block Design for EEG Classification.* IEEE TPAMI, 43(1):316.
- Kapoor & Narayanan (2023). *Leakage and the Reproducibility Crisis in Machine-learning-based Science.* Patterns, 4(9):100804.

---

## Publish checklist

Before making the repository public:

```bash
python tools/generate_evidence_bundle.py
python -m pytest tests/ -v --tb=short
python tools/validate_truth_contract.py
python tools/validate_open_source_readiness.py
python tools/check_github_actions_policy.py
python tools/scan_secrets.py
python tools/generate_provenance_manifest.py
python tools/validate_ip_provenance.py
python tools/validate_markdown.py
python -m build
```

Then follow:

```bash
docs/GITHUB_PUBLICATION_RUNBOOK.md
```

Enable repository-level controls in GitHub UI: branch protection, tag protection, secret scanning with push protection, CodeQL/code scanning, Dependabot alerts, private vulnerability reporting, and release artifact attestations.

---

<div align="center">

**BSFF does not trust. It tests.**

`GPL-3.0-or-later` code · `CC-BY-4.0` docs · Open science · No vendor affiliation

</div>
