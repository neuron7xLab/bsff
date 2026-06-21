<!-- SPDX-License-Identifier: CC-BY-4.0 -->
<!-- Copyright (c) 2026 Yaroslav Vasylenko / neuron7xLab -->

# Honesty automation — the anti-lie property, machine-enforced

## The first principle

A safety property that lives in prose is a promise. A safety property enforced
by an exit code is a guarantee. BSFF's honesty claims (no decorative `VERIFIED`,
no soft status, no unsourced threshold, no implicit null, no stale count) were
prose. This layer makes the *specific, enumerated* set of those lies **unable to
merge** — checked deterministically, fail-closed, with no network and no human.

## The bounded, honest guarantee

No software is "100% incapable of lying", and this document does not claim that —
claiming it would itself be the kind of decoration the gate exists to stop. What
the gate **does** guarantee is that the following enumerated decorative lies fail
CI:

| forbidden | enforced by |
|-----------|-------------|
| a `VERIFIED` claim with no command or no value | `tools/validate_claim_audit.py` |
| a soft status (`PASS`/`OK`/`LIKELY`/`STRONG`/…) | `tools/validate_claim_audit.py` |
| a status not in {VERIFIED, NOT VERIFIED, FALSE, UNPROVEN, NEEDS_EXTERNAL_CHECK} | `tools/validate_claim_audit.py` |
| an UNPROVEN / NEEDS_EXTERNAL_CHECK with no reason | `tools/validate_claim_audit.py` |
| a threshold with no value+reason+source | `tools/validate_threshold_registry.py` |
| a p-value with no registered null hypothesis | `tools/validate_null_registry.py` |
| a hand-typed / stale test count | `tools/update_status.py --check` |
| a self-falsification control giving the wrong verdict | `tools/verify_controls.py` |
| a contract promise silently unmet (vs honestly UNVERIFIABLE) | `tools/run_contract_conformance.py` |

## The gate

```bash
python tools/verify_honesty.py    # fail-closed conjunction of all sub-checks
```

It runs each sub-check, writes `artifacts/honesty/HONESTY_GATE.json`, and exits
non-zero if any fails. It is wired into the test suite
(`tests/test_honesty_gate.py`), so a change that introduces any enumerated lie
turns CI red. The gate also ships negative tests: a fabricated audit with a
command-less `VERIFIED`, and one with a soft state, are both shown to be rejected.

## Why not a heavy framework

The Anthropic-style first principle is *minimal, deterministic, auditable
enforcement* — not ceremony. Adding a large policy framework would be cargo-cult:
more surface, more trust, less verifiability. Every check here is a few lines of
stdlib that an external reviewer can read in full. The strength is that the gate
is small enough to be obviously correct, and strict enough to block the lie.

## Self-application note

On its first run the claim-audit validator rejected a real defect in BSFF's own
`CLAIM_AUDIT.md` (a `VERIFIED` row whose command cell said "same" instead of an
explicit command). It was fixed before this layer shipped. The gate works because
it has already caught its author.
