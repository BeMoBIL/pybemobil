"""Tests for EpochPreparer defaults, provenance and deprecated names."""

import mne
import numpy as np
import pytest

from pybemobil.preproc import EpochPreparer


def _raw_with_trials(sfreq=250.0):
    rng = np.random.default_rng(0)
    raw = mne.io.RawArray(
        rng.standard_normal((2, int(sfreq * 20))) * 1e-6,
        mne.create_info(["Cz", "Pz"], sfreq, "eeg"),
        verbose=False,
    )
    onsets = [2.0, 6.0, 10.0]
    raw.set_annotations(
        mne.Annotations(onsets, 0.0, ["trialStart;condition:A;stimulus:x"] * 3)
    )
    return raw


def test_epoch_tlimes_is_a_deprecated_alias():
    """The misspelled epoch_tlimes still works but warns."""
    with pytest.warns(FutureWarning, match="epoch_tlims"):
        prep = EpochPreparer({"c": {}}, epoch_tlimes=(-0.1, 0.4))
    assert prep.epoch_tlims == (-0.1, 0.4)
    assert prep.epoch_tlimes == (-0.1, 0.4)
