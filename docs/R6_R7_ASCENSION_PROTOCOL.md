<!-- SPDX-License-Identifier: CC-BY-4.0 -->

# ⊛ BSFF R6/R7 Ascension Protocol

## Scientific Validity, Research Prestige, and Engineering Excellence Work Order

**Version:** 2026.06  
**Status:** foundational architecture scaffold  
**Target:** R6 independently reproducible research software → R7 field-standard falsification framework

---

## 1. Mission

BSFF must advance from a strong solo-engineered research repository into a credible,
externally reproducible, publication-grade scientific software artifact.

The target is not more code. The target is higher epistemic pressure.

BSFF must convert uncertain BCI, EEG, and signal-processing claims into falsifiable
contracts, reproducible experiments, adversarial null tests, provenance-backed evidence,
and externally auditable conclusions.

The repository must no longer merely state that it tests claims. It must demonstrate that
every scientific claim either survives a hostile reproducibility gate or is explicitly
rejected.

---

## 2. Target Rank

### Current operating rank

**R5.2 — advanced research software artifact**

This means:

- serious architecture;
- strong testing culture;
- meaningful CI and security posture;
- publishable direction;
- not yet externally replicated;
- not yet field-standard;
- not yet stable v1.0;
- not yet institutionally validated.

### Target rank

**R6 — independently reproducible research software**

Required properties:

- clean install from zero;
- deterministic reproduction path;
- complete claim registry;
- dataset provenance;
- statistical contract;
- artifact hashes;
- DOI release;
- reproducible paper figures and tables;
- external reproduction by at least one independent party.

### Aspirational rank

**R7 — field-standard scientific falsification framework**

Required properties:

- accepted peer-reviewed software paper;
- multiple independent replications;
- downstream users;
- stable API;
- cited usage;
- maintained releases;
- recognized as a falsification instrument, not just a codebase.

---

## 3. Governing law

> No scientific claim may exist without a falsification path.

Every claim must have:

- scope;
- dataset;
- null model;
- metric;
- uncertainty estimate;
- failure condition;
- reproducibility command;
- evidence artifact;
- reviewer-facing explanation.

A claim without a failure condition is not science.  
A metric without uncertainty is not evidence.  
A figure without a reproduction command is decoration.  
A passing internal test without external reproduction is only a local signal.

---

## 4. Core research values

### 4.1 Truth before performance

The system must prefer a correct negative result over an impressive unsupported positive
result. BSFF's prestige comes from rejecting weak claims, not from producing attractive
graphs.

### 4.2 Falsification before optimization

Optimization is secondary. The first task is to expose where the claim breaks.

### 4.3 Provenance before convenience

Every dataset, transformation, dependency, and output must be traceable.

Unknown origin means invalid evidence.

### 4.4 Reproducibility before narrative

The paper must be generated from the repository, not manually decorated after the fact.

### 4.5 External audit before status

Internal green CI is not enough. A serious scientific artifact must survive a hostile
reviewer with no private context.

---

## 5. Mandatory workstreams

| Workstream | Required artifact | Purpose |
|---|---|---|
| A | `CLAIMS.md`, `claims.yaml` | Bind every scientific statement to falsifiable scope. |
| B | `DATASET_PROVENANCE.md`, `data_registry.json` | Make evidence lineage explicit and auditable. |
| C | `STATISTICAL_CONTRACT.md`, `src/bsff/statistics/contracts.py` | Define failure semantics, uncertainty, nulls, and metric contracts. |
| D | `REPRODUCE.md`, `reproduce.sh` | Provide one-command clean reproduction. |
| E | `ARTIFACT_EVALUATION.md`, `artifact_manifest.json`, `reviewer_quickstart.md` | Prepare an external reviewer package. |
| F | `SUPPLY_CHAIN.md` | Bind security maturity to release evidence. |
| G | `RELEASE_CHECKLIST.md` | Prevent v1.0 before stable API, DOI, and external reproduction. |

---

## 6. Release ladder

### v0.5.0 — validation candidate

Allowed only when:

- claim registry is complete;
- dataset registry is complete;
- statistical contract is implemented;
- reproduction command exists;
- paper draft is aligned with evidence.

### v0.6.0 — external review candidate

Allowed only when:

- artifact evaluation package is complete;
- clean Docker reproduction exists;
- DOI draft release exists;
- reviewer quickstart is usable without private context;
- security and provenance gates are green.

### v1.0.0 — stable scientific release

Allowed only when:

- public API is stable;
- core claims are externally reproduced;
- release archive has DOI;
- paper is submitted or accepted;
- documentation is reviewer-grade;
- all critical gates are green.

---

## 7. Explicit prohibitions

Do not:

- inflate claims;
- hide negative results;
- call internal tests validation;
- use one dataset as universal proof;
- present exploratory analysis as confirmed evidence;
- ship v1.0 without a stable API contract;
- polish the paper beyond the evidence;
- confuse engineering complexity with scientific status.

---

## 8. Final definition of value

BSFF's highest value is not that it analyzes signals.

Its value is that it forces signal claims to survive a hostile chain:

```text
claim
→ dataset provenance
→ null model
→ statistical uncertainty
→ reproducible execution
→ artifact hash
→ external reviewer
→ public release
→ citation
```

If a claim survives this chain, it becomes evidence. If it fails, BSFF has still succeeded.

BSFF is a falsification engine for weak BCI and signal-processing claims. Its elite form is
not a larger repository. Its elite form is a stricter epistemic machine.
