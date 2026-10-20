"""Tests for bad-channel detection (get_bad_chs) and its use in the pipeline."""

import mne
import numpy as np
import pytest

from pybemobil.preproc import EEGPreprocessor, get_bad_chs


def _smooth_raw(n_ch=32, sfreq=250.0, duration=120.0, seed=0):
    """Spatially smooth EEG: a few sources projected by distance."""
    rng = np.random.default_rng(seed)
    montage = mne.channels.make_standard_montage("easycap-M1")
    names = montage.ch_names[:n_ch]
    n = int(sfreq * duration)
    pos = np.array([montage.get_positions()["ch_pos"][c] for c in names])
    src_pos = rng.normal(size=(8, 3)) * 0.05
    dist = np.linalg.norm(pos[:, None] - src_pos[None], axis=2)
    mixing = 1 / (dist + 0.03)
    sources = np.array(
        [np.convolve(s, np.ones(10) / 10, "same") for s in rng.laplace(size=(8, n))]
    )
    x = mixing @ sources
    x = x / np.abs(x).std() * 1e-5 + 1e-6 * rng.standard_normal((n_ch, n))
    raw = mne.io.RawArray(x, mne.create_info(names, sfreq, "eeg"), verbose=False)
    raw.set_montage(montage)
    return raw


def test_slow_drift_does_not_make_a_channel_bad():
    """A good channel with a slow drift is not flagged (detection is high-passed)."""
    raw = _smooth_raw()
    clean = set(get_bad_chs(raw, notch_lines=None, ransac=False)["all_bads"])
    t = raw.times
    data = raw.get_data()
    data[5] += 1e-4 * np.sin(2 * np.pi * 0.05 * t)  # 0.05 Hz, 100 uV
    drifting = raw.copy()
    drifting._data = data
    bads = set(get_bad_chs(drifting, notch_lines=None, ransac=False)["all_bads"])
    assert raw.ch_names[5] not in bads
    assert bads == clean


def test_get_bad_chs_does_not_modify_input():
    """The high-pass, reference and notch only touch an internal copy."""
    raw = _smooth_raw(duration=30.0)
    before = raw.get_data().copy()
    get_bad_chs(raw, ransac=False)
    np.testing.assert_array_equal(raw.get_data(), before)


@pytest.mark.parametrize("amp", [5e-6, 20e-6])
def test_line_noise_criterion_sees_line_noise(amp):
    """The line-noise criterion runs before the notch, so it can detect it."""
    raw = _smooth_raw(duration=60.0)
    data = raw.get_data()
    data[0] += amp * np.sin(2 * np.pi * 50 * raw.times)
    raw._data = data
    res = get_bad_chs(raw, notch_lines="europe", line_noise_crit=3, ransac=False)
    assert res["bad_by_line_noise"] == [raw.ch_names[0]]


def test_warns_when_many_channels_are_bad():
    """More than max_bad_fraction bad channels triggers a visible warning."""
    raw = _smooth_raw(n_ch=16, duration=30.0)
    data = raw.get_data()
    data[:5] = 0.0  # 5 of 16 flat channels
    raw._data = data
    with pytest.warns(RuntimeWarning, match="flagged .* of 16 EEG channels"):
        get_bad_chs(raw, notch_lines=None, ransac=False)
    # the limit is configurable
    import warnings

    with warnings.catch_warnings():
        warnings.simplefilter("error", RuntimeWarning)
        get_bad_chs(raw, notch_lines=None, ransac=False, max_bad_fraction=0.5)


def test_nan_data_raises_clear_error():
    """NaN in the data gives a clear error instead of an obscure one."""
    raw = _smooth_raw(n_ch=8, duration=10.0)
    data = raw.get_data()
    data[2, 100:200] = np.nan
    raw._data = data
    with pytest.raises(ValueError, match="contain NaN"):
        get_bad_chs(raw)


@pytest.mark.parametrize("sfreq", [100.0, 101.0])
def test_get_bad_chs_low_sampling_rate(sfreq):
    """At <= ~106 Hz the 50 Hz notch cannot be built; it is skipped, not fatal."""
    raw = _smooth_raw(n_ch=16, sfreq=sfreq, duration=30.0)
    res = get_bad_chs(raw, notch_lines="europe", ransac=False)
    assert "all_bads" in res


def test_pipeline_runs_at_100_hz():
    """run_raw works for low-rate recordings (the notch list is empty)."""
    raw = _smooth_raw(n_ch=16, sfreq=100.0, duration=40.0)
    proc = EEGPreprocessor(
        loader=None,
        line_noise_method=None,
        ica_method="picard",
        make_report=False,
        downsample_ica=None,
        get_bad_chs_kwargs={"ransac": False},
    )
    raw_clean, _, metadata = proc.run_raw(raw, fname_out=None)
    assert raw_clean.info["sfreq"] == 100.0


def test_flat_channels_are_detected_before_referencing():
    """Flat channels stay detectable: they are found before the average reference."""
    raw = _smooth_raw(n_ch=16, duration=30.0)
    data = raw.get_data()
    data[3] = 0.0
    data[7] = 5e-3  # constant DC offset
    raw._data = data
    res = get_bad_chs(raw, notch_lines=None, ransac=False)
    flat = {raw.ch_names[3], raw.ch_names[7]}
    assert flat <= set(res["pyprep"]["bad_by_flat"])
    assert flat <= set(res["all_bads"])
    assert res["bad_by_manual"] == []
