"""Tests for motion processing: angle units, dropouts and defaults."""

import logging

import mne
import numpy as np
import pytest

from pybemobil.preproc import process_rigid_body


def _euler_raw(yaw, sfreq=100.0):
    n = yaw.size
    data = np.vstack([np.full(n, 0.1), np.zeros(n), yaw])
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


def _static_body_with_dropout(sfreq=100.0, duration=20.0, gap=(8.0, 8.5)):
    """Make a resting rigid body with a 0.5 s dropout zero-filled by the loader."""
    n = int(sfreq * duration)
    t = np.arange(n) / sfreq
    quat = np.tile([[0.0], [0.0], [0.38268343], [0.92387953]], (1, n))  # 45 deg yaw
    pos = np.tile([[1.2], [0.4], [1.7]], (1, n))
    data = np.vstack([quat, pos])
    in_gap = (t >= gap[0]) & (t < gap[1])
    data[:, in_gap] = 0.0
    names = [f"rb_quat_{a}" for a in "xyzw"] + [f"rb_pos_{a}" for a in "xyz"]
    return mne.io.RawArray(data, mne.create_info(names, sfreq, "misc"), verbose=False)


def test_zero_filled_dropout_does_not_create_velocity():
    """Bridged dropouts give no spurious velocity or acceleration."""
    raw = _static_body_with_dropout()
    out, info = process_rigid_body(raw)
    assert info["rb"]["n_missing"] == 50
    for kind in ("pos_vel", "pos_acc", "eul_vel", "eul_acc"):
        data = out.get_data(picks=[f"rb_{kind}_{a}" for a in "xyz"])
        assert np.abs(data).max() < 1e-6, kind
    np.testing.assert_allclose(out.get_data(picks="rb_pos_z")[0], 1.7, atol=1e-6)
    np.testing.assert_allclose(out.get_data(picks="rb_eul_z")[0], np.pi / 4, atol=1e-6)


def test_dropout_is_annotated_once():
    """Bridged spans are marked BAD_<rb>_missing, without duplicating loader marks."""
    raw = _static_body_with_dropout()
    out, _ = process_rigid_body(raw)
    ann = out.annotations[out.annotations.description == "BAD_rb_missing"]
    assert len(ann) == 1
    np.testing.assert_allclose([ann.onset[0], ann.duration[0]], [8.0, 0.5])

    raw.annotations.append(8.0, 0.5, "BAD_rb_missing")  # as XDFLoader does
    out, _ = process_rigid_body(raw)
    assert (out.annotations.description == "BAD_rb_missing").sum() == 1
