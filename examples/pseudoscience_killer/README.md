<!-- SPDX-License-Identifier: CC-BY-4.0 -->
<!-- Copyright (c) 2026 Yaroslav Vasylenko / neuron7xLab -->

# Pseudoscience killer — a reproducible end-to-end demonstration

This is the demonstration that the whole pipeline exists for: take the claims of
a (fabricated) paper and let each one earn its standing or be quarantined —
automatically, fail-closed, and with a tamper-evident record.

```bash
python examples/pseudoscience_killer/run_demo.py --out out/
```

## The corpus

A fake preprint claims an EEG recording proves, among other things, mind-to-mind
transfer. Five claims are extracted; the underlying signals are **white noise
generated deterministically from a seed**, so there is genuinely nothing for a
real effect to be found in. The kill is honest, not rigged.

| claim | kind | how it dies |
|-------|------|-------------|
| "...statistically significant nonlinear deterministic structure" | empirical-statistical | run through the surrogate battery on its own data → **REFUTED** |
| "neural activity in region A drives activity in region B" | causal | conditional transfer-entropy test on its own data → **UNSUPPORTED** (no directed coupling) |
| "clinicians should immediately adopt this neuro-telepathy protocol" | normative | **QUARANTINED_NORMATIVE** |
| "consciousness is a fundamental field permeating spacetime" | non-falsifiable | **QUARANTINED_NON_FALSIFIABLE** |
| "the device achieved 99 percent telepathic accuracy across continents" | *not in the source* | **QUARANTINED_UNANCHORED** (fabricated extraction) |

## What you get

- `report.json` — the machine-readable batch report with a self-verifying hash.
- `report.html` / `report.md` — the human-readable verdict page.
- `ledger.jsonl` — the hash-chained record of every verdict; `bsff ledger-verify`
  confirms nothing was altered after the fact.

The script **self-checks**: it exits non-zero if any pseudoscience claim earns a
surviving verdict. No claim is ever promoted to "true" — the strongest outcome an
empirical claim can reach is *survived falsification under stated conditions*, and
here none does. Nothing in this repository is committed as a binary signal; the
data is regenerated from seeds on every run, so the result is reproducible byte
for byte.
