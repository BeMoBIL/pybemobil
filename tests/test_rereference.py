"""Tests for the final interpolation and average-reference stage."""

import mne
import numpy as np

from pybemobil.preproc import EEGPreprocessor
from pybemobil.preproc.preprocessing import _interpolate_and_rereference


def _raw_with_bads(n_ch=24, n_bad=6, seed=0):
    rng = np.random.default_rng(seed)
    montage = mne.channels.make_standard_montage("easycap-M1")
    sources = rng.laplace(size=(6, 250 * 40))
    data = rng.normal(size=(n_ch, 6)) @ sources + 0.1 * rng.standard_normal(
        (n_ch, sources.shape[1])
    )
    info = mne.create_info(montage.ch_names[:n_ch], 250.0, "eeg")
    raw = mne.io.RawArray(data * 1e-6, info, verbose=False)
    raw.set_montage(montage)
    raw.info["bads"] = montage.ch_names[:n_bad]
    return raw


def test_final_data_is_average_referenced_after_interpolation():
    """After the final stage the EEG channels sum to zero, interpolated included."""
    raw = _raw_with_bads()
    raw.set_eeg_reference("average", projection=True)
    _interpolate_and_rereference(raw)
    data = raw.get_data(picks="eeg")
    assert raw.info["bads"] == []
    assert np.abs(data.mean(axis=0)).max() < 1e-12 * data.std()


def test_eog_channels_are_not_interpolated_or_referenced():
    """EOG channels keep their data; only EEG channels enter the reference."""
    raw = _raw_with_bads(n_bad=2)
    eog = mne.io.RawArray(
        np.random.default_rng(1).standard_normal((1, raw.n_times)) * 1e-5,
        mne.create_info(["VEOG"], 250.0, "eog"),
        verbose=False,
    )
    raw.add_channels([eog], force_update_info=True)
    raw.info["bads"] = raw.info["bads"] + ["VEOG"]
    before = raw.get_data(picks="VEOG").copy()
    raw.set_eeg_reference("average", projection=True)
    _interpolate_and_rereference(raw)
    np.testing.assert_array_equal(raw.get_data(picks="VEOG"), before)


def test_run_raw_output_is_average_referenced():
    """End to end: raw_clean is average-referenced over all EEG channels."""
    raw = _raw_with_bads()
    proc = EEGPreprocessor(
        loader=None,
        line_noise_method=None,
        fit_ica=False,
        make_report=False,
        get_bad_chs_kwargs={"ransac": False},
    )
    raw_clean, _, _ = proc.run_raw(raw, fname_out=None)
    data = raw_clean.get_data(picks="eeg")
    assert np.abs(data.mean(axis=0)).max() < 1e-12 * data.std()
