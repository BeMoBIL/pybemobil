"""Tests for EpochPreparer defaults, provenance and deprecated names."""

import json

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


def test_tshift_defaults_to_zero(tmp_path):
    """By default events are not shifted; epochs start at the marker."""
    prep = EpochPreparer({"c": {"A/x": "target"}})
    assert prep.tshift == 0.0
    epochs = prep.run(_raw_with_trials(), tmp_path / "s", "c")["target"]
    np.testing.assert_allclose(
        epochs.events[:, 0] / epochs.info["sfreq"], [2.0, 6.0, 10.0]
    )


def test_epoching_settings_are_recorded(tmp_path):
    """The time shift and epoch window end up in the epochs' provenance."""
    prep = EpochPreparer({"c": {"A/x": "target"}}, tshift=0.025)
    epochs = prep.run(_raw_with_trials(), tmp_path / "s", "c")["target"]
    steps = json.loads(epochs.info["description"])["steps"]
    step = next(s for s in steps if s["name"] == "epoching")
    assert step["tshift"] == 0.025
    assert (step["tmin"], step["tmax"]) == (-0.2, 0.8)


def test_epoch_tlimes_is_a_deprecated_alias():
    """The misspelled epoch_tlimes still works but warns."""
    with pytest.warns(FutureWarning, match="epoch_tlims"):
        prep = EpochPreparer({"c": {}}, epoch_tlimes=(-0.1, 0.4))
    assert prep.epoch_tlims == (-0.1, 0.4)
    assert prep.epoch_tlimes == (-0.1, 0.4)
