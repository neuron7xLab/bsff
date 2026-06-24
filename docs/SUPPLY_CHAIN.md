<!-- SPDX-License-Identifier: CC-BY-4.0 -->
# Supply chain

BSFF ships supply-chain evidence so a consumer can verify what they install.

## SBOM
- CycloneDX: `artifacts/sbom/bsff.cyclonedx.json`
- SPDX: `artifacts/sbom/bsff.spdx.json`
- Hash: `artifacts/sbom/bsff.sbom.sha256`
- Generated + checked in CI by `.github/workflows/provenance-sbom.yml`.

## Dependency / vulnerability audit
- `pip-audit` runs in CI (`.github/workflows/security.yml`, `ci.yml`); a severe finding blocks
  the gate unless explicitly waived with a recorded reason.
- Secret scanning: `tools/scan_secrets.py` (CI). Static checks: `zizmor` (Actions audit),
  `codeql-python`.

## Provenance
- `tools/generate_provenance_manifest.py` + `tools/validate_ip_provenance.py` (CI) bind the
  release surface to its sources; SLSA-style provenance attestation is emitted by the
  provenance workflow where the runner supports it.

## Reproducible verification (consumer side)
```bash
bsff evidence verify        # coherence + hashes + release gate + raw-data hygiene
sha256sum -c artifacts/release/bonn_bright_line/HASHES.sha256
sha256sum -c artifacts/sbom/bsff.sbom.sha256
```

## Trust boundary
The SBOM and audits cover the **package and its dependencies**. They do not, and cannot,
establish clinical, regulatory, or scientific validity — those are out of scope (see
`docs/VERDICT_SEMANTICS.md` and `artifacts/release/CURRENT_TRUTH.json`).
