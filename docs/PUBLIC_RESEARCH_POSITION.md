<!-- SPDX-License-Identifier: CC-BY-4.0 -->

# Public Research Position

BSFF is public because the claim boundary must be public.

The project is not positioned as vibe-coded software, a private demo, or a decorative
AI-generated repository. It is positioned as an independent research-software artifact
whose value is measured by whether its claims can survive falsification, provenance,
statistical uncertainty, and external reproduction.

## Position

BSFF exists to make weak BCI and signal-processing claims harder to publish, sell, or
repeat without evidence.

It does not ask the reviewer to believe the author. It asks the reviewer to run the gate.

## Research identity

The repository follows one identity:

> a claim is not accepted because it sounds intelligent; it is accepted only when it
> survives a declared adversarial path.

This is the practical standard:

- every claim must have a failure condition;
- every dataset must have provenance;
- every metric must have uncertainty;
- every positive statement must have a null model;
- every release must have evidence artifacts;
- every rank label must be bounded by public reproduction.

## Public boundary

BSFF does not claim:

- clinical diagnosis;
- regulatory readiness;
- therapeutic effect;
- universal BCI authority;
- final proof of brain dynamics;
- R6/R7 completion before external hostile reproduction.

## Demonstration standard

The public demonstration is not a screenshot, a social post, or an impressive README.

The demonstration is:

```bash
python tools/validate_r6_contracts.py
bash reproduce.sh --clean --verify
```

If these commands fail, the claim does not move forward.

If they pass locally, the project still remains pre-R6 until an external reviewer can
reproduce the central evidence from public materials without private author explanation.
