# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (c) 2026 Yaroslav Vasylenko / neuron7xLab
"""Decoders under test for BSFF-CASE-001.

Two decoders are provided. The falsification result is *decoder-agnostic* — the
cross-subject generalization gap is a property of the data/evaluation protocol, not
of a particular model — and showing the gap under more than one decoder is stronger
evidence than showing it under one.

* ``logvar_lda`` — band-pass (mu/beta) -> log-variance per channel -> LDA. Fully
  deterministic, sklearn-only, fast enough for permutation nulls and LOSO. This is
  the workhorse engine and the default.
* ``eegnet`` — the actual architecture the popular claim is about (Lawhern et al.,
  2018), in PyTorch, CPU, seeded and run with deterministic algorithms. Optional;
  enabled with ``--decoder eegnet`` when torch is available.

Both expose the same ``fit_predict(x_train, y_train, x_test) -> y_pred`` contract so
the split harness is identical regardless of decoder.
"""

from __future__ import annotations

from typing import Protocol

import numpy as np
from numpy.typing import NDArray
from scipy.signal import butter, sosfiltfilt

FloatArray = NDArray[np.float64]
IntArray = NDArray[np.int_]


class Decoder(Protocol):
    name: str

    def fit_predict(
        self, x_train: FloatArray, y_train: IntArray, x_test: FloatArray
    ) -> IntArray: ...


def bandpass_logvar(x: FloatArray, sfreq: float, low: float, high: float) -> FloatArray:
    """Band-pass each (trial, channel, time) then take log-variance per channel.

    Returns ``(n_trials, n_channels)``. Log-variance of mu/beta band power is the
    canonical motor-imagery feature (ERD/ERS); using it keeps the decoder honest and
    decoder choice from doing the heavy lifting.
    """
    nyq = 0.5 * sfreq
    low_n = max(1e-4, min(0.99, low / nyq))
    high_n = max(low_n + 1e-3, min(0.999, high / nyq))
    sos = butter(4, [low_n, high_n], btype="band", output="sos")
    filtered = sosfiltfilt(sos, x, axis=-1)
    var = filtered.var(axis=-1)
    return np.log(var + 1e-12)


class LogVarLDA:
    """Band-pass log-variance features + Linear Discriminant Analysis."""

    name = "logvar_lda"

    def __init__(self, sfreq: float, low: float = 8.0, high: float = 30.0) -> None:
        self.sfreq = sfreq
        self.low = low
        self.high = high

    def _features(self, x: FloatArray) -> FloatArray:
        return bandpass_logvar(np.asarray(x, dtype=float), self.sfreq, self.low, self.high)

    def fit_predict(self, x_train: FloatArray, y_train: IntArray, x_test: FloatArray) -> IntArray:
        from sklearn.discriminant_analysis import LinearDiscriminantAnalysis
        from sklearn.pipeline import make_pipeline
        from sklearn.preprocessing import StandardScaler

        clf = make_pipeline(StandardScaler(), LinearDiscriminantAnalysis())
        clf.fit(self._features(x_train), np.asarray(y_train))
        return np.asarray(clf.predict(self._features(x_test)), dtype=int)


class FeatureLDA:
    """LDA on already-extracted features (no filtering).

    The split battery filters once up front (``bandpass_logvar``) and hands the
    feature matrix to this decoder, so the heavy band-pass is not recomputed on every
    fold and every permutation. Mathematically identical to :class:`LogVarLDA` because
    band-pass + log-variance is independent per trial, but orders of magnitude faster
    for the permutation nulls. Fits the scaler on train only (no test-set leak).
    """

    name = "feature_lda"

    def fit_predict(self, x_train: FloatArray, y_train: IntArray, x_test: FloatArray) -> IntArray:
        from sklearn.discriminant_analysis import LinearDiscriminantAnalysis
        from sklearn.pipeline import make_pipeline
        from sklearn.preprocessing import StandardScaler

        clf = make_pipeline(StandardScaler(), LinearDiscriminantAnalysis())
        clf.fit(np.asarray(x_train, dtype=float), np.asarray(y_train))
        return np.asarray(clf.predict(np.asarray(x_test, dtype=float)), dtype=int)


class EEGNetDecoder:
    """EEGNet (Lawhern et al., 2018) in PyTorch, CPU, deterministic.

    Kept optional so the case harness and CI never require torch. The architecture
    is the one the popular "robust decoding" claim is built on, so running it closes
    the loop on the *named* model rather than a stand-in.
    """

    name = "eegnet"

    def __init__(self, sfreq: float, epochs: int = 60, seed: int = 20260621) -> None:
        self.sfreq = sfreq
        self.epochs = epochs
        self.seed = seed

    def fit_predict(self, x_train: FloatArray, y_train: IntArray, x_test: FloatArray) -> IntArray:
        import torch
        from torch import nn

        torch.manual_seed(self.seed)
        np.random.seed(self.seed)  # any incidental numpy RNG in the path is pinned too
        torch.use_deterministic_algorithms(True, warn_only=True)
        if hasattr(torch.backends, "cudnn"):
            torch.backends.cudnn.deterministic = True
            torch.backends.cudnn.benchmark = False

        n_ch = x_train.shape[1]
        n_t = x_train.shape[2]
        f1, depth, f2 = 8, 2, 16
        kern = min(64, n_t // 2)

        class EEGNet(nn.Module):
            def __init__(self) -> None:
                super().__init__()
                self.block1 = nn.Sequential(
                    nn.Conv2d(1, f1, (1, kern), padding=(0, kern // 2), bias=False),
                    nn.BatchNorm2d(f1),
                    nn.Conv2d(f1, f1 * depth, (n_ch, 1), groups=f1, bias=False),
                    nn.BatchNorm2d(f1 * depth),
                    nn.ELU(),
                    nn.AvgPool2d((1, 4)),
                    nn.Dropout(0.25),
                )
                self.block2 = nn.Sequential(
                    nn.Conv2d(f1 * depth, f2, (1, 16), padding=(0, 8), bias=False),
                    nn.BatchNorm2d(f2),
                    nn.ELU(),
                    nn.AvgPool2d((1, 8)),
                    nn.Dropout(0.25),
                )
                feat = f2 * (((n_t // 4) // 8) or 1)
                self.head = nn.Linear(feat, 2)

            def forward(self, x: torch.Tensor) -> torch.Tensor:
                x = self.block1(x)
                x = self.block2(x)
                x = x.flatten(1)
                return self.head(x)  # type: ignore[no-any-return]

        def standardize(a: FloatArray, mean: FloatArray, std: FloatArray) -> FloatArray:
            return (a - mean) / std

        mean = x_train.mean(axis=(0, 2), keepdims=True)
        std = x_train.std(axis=(0, 2), keepdims=True) + 1e-7
        xtr = standardize(np.asarray(x_train, dtype=float), mean, std)
        xte = standardize(np.asarray(x_test, dtype=float), mean, std)

        model = EEGNet()
        opt = torch.optim.Adam(model.parameters(), lr=1e-3)
        loss_fn = nn.CrossEntropyLoss()
        xt = torch.tensor(xtr, dtype=torch.float32).unsqueeze(1)
        yt = torch.tensor(np.asarray(y_train), dtype=torch.long)
        model.train()
        for _ in range(self.epochs):
            opt.zero_grad()
            out = model(xt)
            loss = loss_fn(out, yt)
            loss.backward()
            opt.step()
        model.eval()
        with torch.no_grad():
            pred = model(torch.tensor(xte, dtype=torch.float32).unsqueeze(1)).argmax(1)
        return np.asarray(pred.numpy(), dtype=int)


def build_decoder(name: str, sfreq: float, *, seed: int = 20260621) -> Decoder:
    if name == "logvar_lda":
        return LogVarLDA(sfreq)
    if name == "eegnet":
        return EEGNetDecoder(sfreq, seed=seed)
    raise ValueError(f"unknown decoder '{name}'; known: logvar_lda, eegnet")
