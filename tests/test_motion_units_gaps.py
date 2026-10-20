"""Tests for motion processing: angle units, dropouts and defaults."""

import logging

import mne
import numpy as np
import pytest

from pybemobil.preproc import process_rigid_body


def _euler_raw(yaw, sfreq=100.0):
    n = yaw.size
    data = np.vstack([np.zeros(n), np.zeros(n), yaw])
    info = mne.create_info(["rb_eul_x", "rb_eul_y", "rb_eul_z"], sfreq, "misc")
    return mne.io.RawArray(data, info, verbose=False)


def _wrap(x, period):
    return (x + period / 2) % period - period / 2


def test_euler_degrees_are_unwrapped_with_360_period():
    """A continuous rotation in degrees comes out continuous with angle_unit='deg'."""
    t = np.arange(0, 5, 0.01)
    yaw = 120.0 * t  # 120 deg/s, wraps at +-180
    raw = _euler_raw(_wrap(yaw, 360.0))
    out, _ = process_rigid_body(
        raw, angle_unit="deg", lowpass_orient=None, compute_velocity=False
    )
    got = out.get_data(picks="rb_eul_z")[0]
    np.testing.assert_allclose(got - got[0], yaw - yaw[0], atol=1e-9)


def test_euler_degrees_with_rad_unit_warns(caplog):
    """Angles beyond 2*pi with angle_unit='rad' log a hint about degrees."""
    yaw = _wrap(90.0 * np.sin(2 * np.pi * np.arange(0, 3, 0.01)), 360.0)
    with caplog.at_level(logging.WARNING):
        process_rigid_body(_euler_raw(yaw), lowpass_orient=None)
    assert "probably in degrees" in caplog.text


def test_invalid_angle_unit_raises():
    """Unknown angle units are rejected."""
    with pytest.raises(ValueError, match="angle_unit"):
        process_rigid_body(_euler_raw(np.zeros(100)), angle_unit="gradians")
