<!-- SPDX-License-Identifier: CC-BY-4.0 -->
<!-- Copyright (c) 2026 Yaroslav Vasylenko / neuron7xLab -->

# BSFF — the whole pipeline, in one picture

BSFF takes a claim about a signal and returns a machine-readable, provenance-
bound verdict. Nothing is ever promoted to "true": the strongest an empirical
claim can earn is *survived falsification under stated conditions*. Everything
below is one chain, not a pile of parts.

```
   raw signal                         a publication's claim
   (.edf/.bdf/.csv/.npy)              (verbatim quote + proposer)
        │                                      │
        ▼                                      ▼
   normalize ──► raw-signal guard         anchor (verbatim, or QUARANTINED_UNANCHORED)
   (EDF/BDF reader,                            │
    physical units)                            ▼
        │                              classify falsifiability tier
        ▼                                      │
   ┌─────────────────────── route ───────────────────────┐
   │ EMPIRICAL_STATISTICAL → surrogate battery (MIAAFT + Bayes conjunction)
   │ EMPIRICAL / causal     → conditional transfer entropy (directed)
   │ LOGICAL                → argument-structure check (not soundness)
   │ DEFINITIONAL/NORMATIVE/NON_FALSIFIABLE → quarantine
   └──────────────────────────────────────────────────────┘
        │
        ▼
   verdict ──► hash-chained truth ledger ──► human-readable report (HTML/MD)
                    │
            corpus / batch: many sources at once, with extraction accountability
```

## Stages

| stage | module | guarantee |
|-------|--------|-----------|
| ingest | `normalize`, `datasets.load_series` | reads EDF/EDF+/BDF/CSV/NPY in pure Python; fail-closed |
| raw-signal guard | `datasets.check_rawness` | refuses feature tables / accuracy matrices / labels — tests the signal, not someone's preprocessing |
| anchor | `adjudication.source` | a claim absent from its source is quarantined, never judged (anti-fabrication floor) |
| classify | `adjudication.falsifiability` | deterministic, auditable tier; default fail-closed `NON_FALSIFIABLE` |
| route → empirical | `verdict_engine`, `surrogate_engine` | MIAAFT surrogate null + effect-size conjunction gate |
| route → causal | `transfer_entropy` | directed, conditional; calibrated operating characteristic |
| route → logical | `adjudication.argument` | detects argument structure, never claims soundness |
| ledger | `adjudication.ledger` | append-only hash chain; tampering breaks it |
| report | `adjudication.report_render` | faithful HTML/Markdown with provenance hash |
| corpus | `adjudication.batch` | many sources, consolidated, with proposer accountability |

## Dispositions (none of them is "true")

`SURVIVED_FALSIFICATION` · `DIRECTED_COUPLING_SURVIVED` ·
`DIRECTED_COUPLING_UNCONDITIONED` · `REFUTED` · `UNSUPPORTED` ·
`PENDING_EVIDENCE` · `LOGICAL_STRUCTURE_PRESENT` / `_INCOMPLETE` /
`NOT_AN_ARGUMENT` · `QUARANTINED_{UNANCHORED,DEFINITIONAL,NORMATIVE,NON_FALSIFIABLE}`

## Command index

| command | does |
|---------|------|
| `bsff selftest` | run the operational-kernel self-validation |
| `bsff falsify --claim spec.json --signal s.npy` | falsify one signal claim with a ClaimSpec |
| `bsff normalize --input rec.edf [--list\|--channel\|--out]` | read raw EDF/BDF → canonical array |
| `bsff adjudicate-data --data s.edf --test nonlinear_structure\|directed_coupling` | data-driven verdict (bring your own raw signal) |
| `bsff ingest --arxiv <id>` | fetch a paper's abstract as a provenance-stamped source |
| `bsff adjudicate --source-text t.txt --claims c.json` | anchor, classify, route, ledger a source's claims |
| `bsff adjudicate-batch --manifest corpus.json` | adjudicate a corpus + extraction accountability |
| `bsff render --report r.json --format html\|md` | render a verdict for human reading |
| `bsff ledger-verify --ledger l.jsonl` | check the hash-chain integrity of a ledger |

## Calibration (measured, not asserted)

The empirical engines are validated against labelled ground truth
(`bsff.operating_characteristic`, `bsff.te_operating_characteristic`, and the
v0.2.0 validation corpus): genuine nonlinear structure survives, matched
linear/IID nulls are refuted, a causal pair is called directionally, a null pair
is not, and a common-drive confound that fools pairwise transfer entropy
collapses under conditioning. The residual at small sample sizes is documented,
not hidden — see `OPERATING_CHARACTERISTIC.md` and `TRANSFER_ENTROPY.md`.

## Boundaries

- BSFF does not decide truth; it decides what scrutiny a claim admits and applies
  it. It does **not** prove BCI claims true.
- The signal engines are linear/spectral. Nonlinear directed coupling (k-NN
  transfer entropy) and non-time-series designs (two-group, cohort) are out of
  scope and would need their own validated tests.
- It is **not externally validated against TISEAN** and carries **not regulatory
  validation**. It is one auditable, reproducible pass — not a replacement for
  peer review.
