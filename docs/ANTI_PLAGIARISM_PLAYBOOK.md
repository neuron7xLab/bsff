<!-- SPDX-License-Identifier: CC-BY-4.0 -->

# Anti-Plagiarism Playbook

## Before publishing

1. Publish the first public release from `neuron7xLab/bsff`.
2. Create a signed/tagged release such as `v0.1.3`.
3. Run `python tools/generate_evidence_bundle.py`.
4. Preserve generated artifacts in the release assets.
5. Enable GitHub security features listed in `docs/GITHUB_PUBLICATION_RUNBOOK.md`.
6. Archive the release externally with a DOI service such as Zenodo if you need academic timestamping.

## If someone copies and removes attribution

1. Compare their files against `artifacts/provenance_manifest.json` hashes and commit timestamps.
2. Capture public evidence: repository URL, commit hash, release URL, package URL, screenshots, dates.
3. Check whether they preserved `LICENSE`, `NOTICE`, `AUTHORS.md`, `CITATION.cff`, and SPDX headers.
4. Open a polite issue first if it looks accidental. Humans occasionally fail without malice, a charming design flaw.
5. If ignored, prepare a license-compliance notice referencing GPL-3.0-or-later and the removed attribution files.
6. For platforms, use the platform’s copyright/license violation reporting flow.

## What not to do

- Do not hide secret watermark logic in open source code. It will be removed.
- Do not invent custom “open but cannot copy” terms. That stops being open source and creates legal sludge.
- Do not rely on README claims alone. Use license text, NOTICE, SPDX, signed provenance, releases, and citations.
