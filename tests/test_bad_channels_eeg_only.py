"""get_bad_chs works on an EEG-only copy; other channels must not matter."""

import mne
import numpy as np

from pybemobil.preproc import get_bad_chs


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


def _with_aux(raw, seed=1):
    """Add a misc and an EOG channel with unrelated data."""
    rng = np.random.default_rng(seed)
    aux = mne.io.RawArray(
        rng.standard_normal((2, raw.n_times)),
        mne.create_info(["misc1", "VEOG"], raw.info["sfreq"], ["misc", "eog"]),
        verbose=False,
    )
    return raw.copy().add_channels([aux], force_update_info=True)


def test_non_eeg_channels_do_not_change_the_result():
    """Adding aux channels, one of them marked bad, gives the same bads."""
    raw = _smooth_raw()
    expected = get_bad_chs(raw, notch_lines=None, ransac=False)["all_bads"]

    raw_aux = _with_aux(raw)
    raw_aux.info["bads"] = ["misc1"]
    out = get_bad_chs(
        raw_aux,
        notch_lines=None,
        ransac=False,
        pyprep_kwargs={"bad_by_manual": ["VEOG"]},
    )
    assert set(out["all_bads"]) - {"misc1", "VEOG"} == set(expected)
    assert set(out["bad_by_manual"]) == {"misc1", "VEOG"}
    # the caller's object is untouched
    assert raw_aux.info["bads"] == ["misc1"]
    assert len(raw_aux.ch_names) == len(raw.ch_names) + 2
