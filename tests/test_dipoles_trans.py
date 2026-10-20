"""Tests for the head-to-MRI transform used for dipole fitting."""

from unittest.mock import patch

import mne


def test_coregistration_is_rigid():
    """auto_coreg_fsaverage does not estimate a scale (fsaverage is unscaled)."""
    from pybemobil.preproc import utils

    with patch.object(mne.coreg, "Coregistration") as coreg_cls:
        utils.auto_coreg_fsaverage(info=None, subjects_dir="x")
    coreg_cls.return_value.set_scale_mode.assert_called_once_with(None)
