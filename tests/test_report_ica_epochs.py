"""The ICA section of the report gets a bounded, EEG-only set of epochs."""

import importlib

import mne
import numpy as np

# pybemobil.preproc.make_report is shadowed by the function of that name
mr = importlib.import_module("pybemobil.preproc.make_report")


def _raw(duration=400.0, sfreq=100.0):
    rng = np.random.default_rng(0)
    info = mne.create_info(["Cz", "Pz", "ecg"], sfreq, ["eeg", "eeg", "ecg"])
    data = rng.standard_normal((3, int(duration * sfreq))) * 1e-6
    return mne.io.RawArray(data, info, verbose=False)


def test_ica_report_epochs_are_capped_and_eeg_only():
    """Long recordings give max_epochs evenly spaced, loaded EEG epochs."""
    epochs = mne.make_fixed_length_epochs(_raw(), duration=1.0, preload=False)
    out = mr._epochs_for_ica_report(epochs, max_epochs=50)
    assert len(out) == 50
    assert out.ch_names == ["Cz", "Pz"]
    assert out.preload
    onsets = out.events[:, 0] / out.info["sfreq"]
    assert onsets[0] == 0 and onsets[-1] == 399  # spread over the recording


def test_ica_report_epochs_short_recording_kept_whole():
    """Fewer epochs than max_epochs are all kept."""
    epochs = mne.make_fixed_length_epochs(_raw(30.0), duration=1.0, preload=False)
    assert len(mr._epochs_for_ica_report(epochs, max_epochs=50)) == 30
