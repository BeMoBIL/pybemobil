"""Tests for dependency fallbacks, provenance and reproducibility."""

import sys

import mne
import numpy as np
import pytest

from pybemobil.preproc.preprocessing import EEGPreprocessor


def _fake_iclabel(labels):
    """Return a stand-in for iclabel_label_components with fixed winners."""
    from mne_icalabel.config import ICALABEL_METHODS_NUMERICAL_TO_STRING

    to_idx = {v: k for k, v in ICALABEL_METHODS_NUMERICAL_TO_STRING["iclabel"].items()}

    def _label(inst, ica, backend=None):
        proba = np.full((ica.n_components_, 7), 0.01)
        for i in range(ica.n_components_):
            proba[i, to_idx[labels[i % len(labels)]]] = 0.9
        return proba

    return _label


# %% Visible fallbacks and provenance of the ICA fit


def _small_raw(rng):
    montage = mne.channels.make_standard_montage("easycap-M1")
    info = mne.create_info(montage.ch_names[:8], 250.0, "eeg")
    raw = mne.io.RawArray(rng.standard_normal((8, 250 * 20)) * 1e-5, info)
    raw.set_montage(montage)
    return raw


def test_compute_ica_jamica_fallback_is_visible(rng, monkeypatch):
    """Without jamica, the picard fallback warns visibly and is recorded."""
    from unittest.mock import patch

    from pybemobil.preproc import utils

    monkeypatch.setitem(sys.modules, "jamica", None)  # import jamica -> ImportError
    labels = ["brain", "other"]
    with patch.object(utils, "iclabel_label_components", _fake_iclabel(labels)):
        with pytest.warns(RuntimeWarning, match="falls back to extended-infomax"):
            ica, _ = utils.compute_ica(
                _small_raw(rng), filter_bands_ica=(1.0, None), ica_method="jamica"
            )
    info = ica.pybemobil_fit_info_
    assert info["method"] == "picard"
    assert info["requested_method"] == "jamica"
    assert info["n_components"] == ica.n_components_
    assert info["n_epochs"] >= info["n_epochs_dropped_faster"] >= 0


@pytest.mark.parametrize(
    "method, module",
    [("adaptive", "mne_denoise.zapline"), ("dss_line", "meegkit.dss")],
)
def test_remove_line_missing_dependency_raises(rng, monkeypatch, method, module):
    """A missing required dependency is an error, not a silent no-op."""
    from pybemobil.preproc.utils import remove_line

    monkeypatch.setitem(sys.modules, module, None)
    with pytest.raises(ImportError, match="required"):
        remove_line(_small_raw(rng), noise_freqs=50.0, method=method)


# %% Provenance: seed and ICA fit


def _mixed_raw(n_ch=16, n_src=6, sfreq=250.0, duration=40.0, seed=0):
    """EEG Raw whose channels share a few sources, so they correlate."""
    rng = np.random.default_rng(seed)
    montage = mne.channels.make_standard_montage("easycap-M1")
    n_times = int(sfreq * duration)
    sources = rng.laplace(size=(n_src, n_times))
    data = rng.normal(size=(n_ch, n_src)) @ sources
    data += 0.1 * rng.standard_normal((n_ch, n_times))
    info = mne.create_info(montage.ch_names[:n_ch], sfreq, "eeg")
    raw = mne.io.RawArray(data * 1e-6, info, verbose=False)
    raw.set_montage(montage, on_missing="ignore")
    return raw


def test_run_raw_records_actual_ica_method():
    """The ICA step records the method and settings actually used."""
    from pybemobil.preproc.utils import get_descriptor

    proc = EEGPreprocessor(
        loader=None,
        line_noise_method=None,
        ica_method="picard",
        make_report=False,
        rng_seed=7,
        get_bad_chs_kwargs={"ransac": False},
    )
    raw_out, _, _ = proc.run_raw(_mixed_raw(), fname_out=None)
    steps = {s["name"]: s for s in get_descriptor(raw_out)["steps"]}
    assert steps["ica"]["method"] == "picard"
    assert steps["ica"]["requested_method"] == "picard"
    assert steps["ica"]["rng_seed"] == 7
    assert "fit_params" in steps["ica"]
