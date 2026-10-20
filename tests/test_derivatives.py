"""Tests for writing derivatives: overwrite checks and stale files."""

from unittest.mock import patch

import mne
import numpy as np
import pytest

from pybemobil.preproc import EEGPreprocessor
from pybemobil.preproc.preprocessing import get_derivative_paths


def _raw(n_ch=8, seed=0):
    rng = np.random.default_rng(seed)
    montage = mne.channels.make_standard_montage("easycap-M1")
    info = mne.create_info(montage.ch_names[:n_ch], 250.0, "eeg")
    raw = mne.io.RawArray(rng.standard_normal((n_ch, 2500)) * 1e-6, info, verbose=False)
    raw.set_montage(montage)
    return raw


def _fname(tmp_path):
    return (
        tmp_path
        / "derivatives"
        / "pybemobil"
        / "sub-01"
        / "eeg"
        / ("sub-01_task-walk_eeg.fif")
    )


def _plant_old_run(paths):
    """Create files an earlier run with ICA, dipoles and a report left behind."""
    paths["clean"].parent.mkdir(parents=True, exist_ok=True)
    for key in ("ica", "trans"):
        paths[key].write_bytes(b"old")
    paths["iclabels"].write_text("{}")
    paths["report"].write_text("<html>old</html>")
    paths["dipoles"].mkdir()
    (paths["dipoles"] / "ic-00-dip.bdip").write_bytes(b"old")
    (paths["dipoles"] / "ic-05-dip.bdip").write_bytes(b"old")
    paths["figures"].mkdir()
    (paths["figures"] / "joint-a.png").write_bytes(b"old")


def test_overwrite_removes_stale_derivatives(tmp_path):
    """A re-run with overwrite=True leaves no files from the earlier run."""
    fname_out = _fname(tmp_path)
    paths = get_derivative_paths(fname_out)
    _plant_old_run(paths)
    raw = _raw()
    proc = EEGPreprocessor(loader=None, fit_ica=False)
    proc._save_outputs(
        fname_out,
        raw_clean=raw,
        raw_pre_ica=raw,
        ica=mne.preprocessing.ICA(n_components=2),
        ic_labels={},
        dipoles=None,
        residuals=None,
        trans=None,
        bad_ch_dict={"all_bads": []},
        overwrite=True,
    )
    assert paths["clean"].exists() and paths["pre_ica"].exists()
    for key in ("ica", "iclabels", "trans", "report", "dipoles", "figures"):
        assert not paths[key].exists(), key


def test_existing_derivatives_fail_before_computing(tmp_path):
    """Without overwrite, existing outputs raise before any processing."""
    fname_out = _fname(tmp_path)
    paths = get_derivative_paths(fname_out)
    paths["clean"].parent.mkdir(parents=True)
    paths["report"].write_text("<html>old</html>")
    proc = EEGPreprocessor(loader=None, fit_ica=False, make_report=False)
    with patch(
        "pybemobil.preproc.preprocessing.get_bad_chs",
        side_effect=AssertionError("computation started"),
    ):
        with pytest.raises(FileExistsError, match="overwrite=True"):
            proc.run_raw(_raw(), fname_out=fname_out)
