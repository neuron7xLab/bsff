<!-- SPDX-License-Identifier: CC-BY-4.0 -->

# BSFF IP Protection Model

BSFF is open source with explicit origin, attribution, citation, and provenance controls.

## Threat model

| Threat | Control |
|---|---|
| Public fork removes original author | `NOTICE`, `AUTHORS.md`, `CITATION.cff`, file-level SPDX headers, `tools/validate_ip_provenance.py` |
| Package is republished under another name | GPL-3.0-or-later license, release provenance manifest, wheel artifact attestation |
| Blog/paper/demo copies the method without credit | CC-BY-4.0 documentation license, citation file, canonical attribution block |
| Malicious PR weakens license/security gates | CODEOWNERS, branch ruleset, CI provenance gate, security workflow, dependency review |
| Built artifact is swapped after release | GitHub artifact attestation + SHA-256 evidence manifest |

## Chosen license posture

Code is licensed as `GPL-3.0-or-later`. This is intentional. A permissive license would be convenient for adoption but weaker against silent rebranding. GPL keeps the project open when redistributed and forces copyright/license preservation.

Documentation and specifications use `CC-BY-4.0`; every reuse must preserve title, author, source, license, and modification notice.

## Non-goals

This model does not prevent someone from violating the license. It gives you enforceable records and machine-verifiable evidence when they do. Software cannot stop plagiarism by itself; it can make theft embarrassingly easy to prove.
