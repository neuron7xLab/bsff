<!-- SPDX-License-Identifier: CC-BY-4.0 -->

# BSFF validation corpus v0.1.5

This directory contains a deterministic synthetic validation corpus used to
calibrate BSFF development gates. It contains no human, clinical, private, or
regulated data.

The corpus exists for three reasons:

1. keep falsification behavior reproducible across machines;
2. provide enough multichannel signal mass to exercise adaptive pipeline stages;
3. make release artifacts large enough to carry real validation material instead
   of cosmetic empty packaging, because civilization apparently requires this.

Generate it with:

```bash
python tools/generate_validation_corpus.py
```

The manifest records array shapes, byte size, seed, and SHA-256 hash.
