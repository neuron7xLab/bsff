# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (c) 2026 Yaroslav Vasylenko / neuron7xLab
#
# Reproducible BSFF container. A run started from this image reproduces a verdict
# from hash-locked inputs (see docs/BIDS_APP.md). The base tag is pinned so the
# software-version manifest is stable.
FROM python:3.12-slim

# Deterministic, non-interactive, no bytecode noise.
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /opt/bsff

# Copy project sources (the .dockerignore excludes .git, artifacts, data, dist,
# and caches so the build context stays minimal and reproducible).
COPY . /opt/bsff

# Install the package with the dev + leakage extras. scikit-learn (leakage)
# powers the MI-based feature-selection leakage detector; dev brings the test
# and lint toolchain used by the in-container gates.
RUN python -m pip install --upgrade pip \
    && python -m pip install ".[dev,leakage]"

# Drop privileges: the BIDS dataset is mounted read-only at run time.
RUN useradd --create-home --uid 1000 bsff
USER bsff

ENTRYPOINT ["bsff"]
CMD ["--help"]
