<!-- SPDX-License-Identifier: CC-BY-4.0 -->
# Dataset provenance audit

- **Dataset:** Andrzejak et al. 2001 Bonn EEG. **DOI:** `10.1103/PhysRevE.64.061907`.
- **Canonical source:** UPF NTSA `https://www.upf.edu/web/ntsa/downloads`
  (`epileptologie-bonn.de` offline since 2024).
- **Acquisition method:** the UPF document endpoint is Cloudflare-gated, so `curl`/`wget`
  receive an HTML challenge. The per-set zips (`Z.zip`=A, `O.zip`=B, `S.zip`=E) were fetched
  once via an authenticated browser session and staged as `bonn_data/{A,B,E}/*.txt`.
- **Sets used:** A (healthy, eyes open), B (healthy, eyes closed), E (ictal/seizure).
  100 segments each.
- **Sample-count convention:** 4097 samples/segment (UPF canonical export; 4096 also
  documented in the literature and accepted by the loader).
- **Hash policy:** per-file SHA256 + per-zip SHA256 recorded in
  `artifacts/bonn_bright_line/DATASET_MANIFEST.json`; artifact hashes in
  `artifacts/release/bonn_bright_line/HASHES.sha256`.
- **Raw-data storage policy:** raw `.txt` segments are **NOT committed** (gitignored:
  `examples/bonn_bright_line/bonn_data/`). Only manifests, hashes, verdicts, logs, and code
  are committed. Verified: `git ls-files | grep bonn_data` → empty.

## Forbidden derivative datasets (must never substitute)
- UCI "Epileptic Seizure Recognition" **178-feature** variant — excluded.
- Kaggle re-uploads or any undocumented mirror without a hash manifest — excluded.
