"""Tests for the head-to-MRI transform used for dipole fitting."""

from unittest.mock import patch

import mne
import numpy as np
import pytest

from pybemobil.preproc.utils import _handle_trans


def test_given_transform_needs_no_download():
    """A Transform is used as is, without fetching fsaverage."""
    trans = mne.transforms.Transform("head", "mri", np.eye(4))
    with patch("mne.datasets.fetch_fsaverage", side_effect=AssertionError("fetch")):
        assert _handle_trans(trans) is trans


def test_invalid_trans_raises_before_download():
    """An invalid trans fails immediately, also without a download."""
    with patch("mne.datasets.fetch_fsaverage", side_effect=AssertionError("fetch")):
        with pytest.raises(TypeError, match="Invalid trans"):
            _handle_trans("fsavg")


def test_coregistration_is_rigid():
    """auto_coreg_fsaverage does not estimate a scale (fsaverage is unscaled)."""
    from pybemobil.preproc import utils

    with patch.object(mne.coreg, "Coregistration") as coreg_cls:
        utils.auto_coreg_fsaverage(info=None, subjects_dir="x")
    coreg_cls.return_value.set_scale_mode.assert_called_once_with(None)


def test_dipole_fit_warns_without_fiducials():
    """Positions without fiducials trigger a warning before fitting."""
    from pybemobil.preproc.utils import _warn_if_no_fiducials

    info = mne.create_info(["Cz", "Pz"], 250.0, "eeg")
    with pytest.warns(RuntimeWarning, match="no fiducials"):
        _warn_if_no_fiducials(info)

    montage = mne.channels.make_standard_montage("easycap-M1")  # has fiducials
    info = mne.create_info(montage.ch_names[:4], 250.0, "eeg")
    info.set_montage(montage)
    import warnings

    with warnings.catch_warnings():
        warnings.simplefilter("error", RuntimeWarning)
        _warn_if_no_fiducials(info)
