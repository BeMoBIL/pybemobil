"""Rigid body motion capture processing utilities.

Implements kinematics processing equivalent to BeMoBIL's
``bemobil_process_all_motion.m`` pipeline:

1. Identify rigid body channel groups from naming conventions (quaternion or
   Euler suffixes).
2. Convert unit quaternions to Euler angles (roll / pitch / yaw) when needed
   and unwrap them over time.
3. Optionally resample and low-pass filter the position / orientation signals.
4. Compute first derivative (velocity) with optional low-pass filtering.
5. Compute second derivative (acceleration) with optional low-pass filtering.

All operations work on :class:`mne.io.BaseRaw` objects.  Rigid body channels
are expected to follow one of two naming conventions:

* **Quaternion**: ``<rigid_body>_quat_x``, ``<rigid_body>_quat_y``,
  ``<rigid_body>_quat_z``, ``<rigid_body>_quat_w``
* **Euler angles**: ``<rigid_body>_eul_x`` (roll), ``<rigid_body>_eul_y``
  (pitch), ``<rigid_body>_eul_z`` (yaw)

Position channels follow the convention ``<rigid_body>_pos_x``,
``<rigid_body>_pos_y``, ``<rigid_body>_pos_z``.

Units: Euler angles computed from quaternions are in radians. Euler input
channels are expected in radians unless ``angle_unit="deg"`` is passed to
:func:`process_rigid_body` (many motion capture systems stream degrees);
they keep their unit in the output. Velocities and accelerations are in
the input unit per second and per second squared.
"""

# %% Imports

from __future__ import annotations

import logging
import re

import mne
import numpy as np

# %% Settings & Constants

LOGGER = logging.getLogger(__name__)

# Suffix patterns used to identify rigid body sub-channels
_QUAT_SUFFIXES = ("_quat_x", "_quat_y", "_quat_z", "_quat_w")
_EUL_SUFFIXES = ("_eul_x", "_eul_y", "_eul_z")
_POS_SUFFIXES = ("_pos_x", "_pos_y", "_pos_z")

_QUAT_RE = re.compile(r"^(.+)_quat_[xyzw]$")
_EUL_RE = re.compile(r"^(.+)_eul_[xyz]$")
_POS_RE = re.compile(r"^(.+)_pos_[xyz]$")


# %% Functions


def find_rigid_bodies(raw):
    """Detect rigid body names from channel naming conventions.

    Parameters
    ----------
    raw : mne.io.BaseRaw
        Recording whose channel names to inspect.

    Returns
    -------
    rb_names : list of str
        Unique rigid body identifiers found in the channel list.
    """
    names: set[str] = set()
    for ch in raw.ch_names:
        for pat in (_QUAT_RE, _EUL_RE, _POS_RE):
            m = pat.match(ch)
            if m:
                names.add(m.group(1))
                break
    return sorted(names)


def process_rigid_body(
    raw,
    rb_names=None,
    lowpass_orient=8.0,
    lowpass_pos=8.0,
    lowpass_deriv=24.0,
    compute_velocity=True,
    compute_acceleration=True,
    sfreq_target=None,
    unwrap=True,
    angle_unit="rad",
):
    """Process rigid body motion capture streams.

    For each rigid body found in *raw*:

    1. Convert quaternions to Euler angles (ZYX convention = yaw-pitch-roll)
       if quaternion channels are present.  The source quaternion channels are
       dropped and replaced by Euler angle channels.
    2. Unwrap the Euler angles (see *unwrap*).
       Samples where the rigid body was not tracked are bridged by linear
       interpolation first: samples where all of its channels are exactly 0
       (how :class:`~pybemobil.io.XDFLoader` fills dropouts), quaternions
       with a norm of ~0, and spans annotated ``BAD_<rb>_missing``. Such
       spans are annotated ``BAD_<rb>_missing`` in the output, so they can be
       rejected later; without bridging, filtering and differentiation would
       turn them into huge spurious velocities.
    3. Optionally resample all channels to *sfreq_target*.
    4. Optionally low-pass filter the orientation (and position) signals.
    5. Compute the first derivative (velocity) via finite differences, with an
       optional low-pass filter applied after differentiation.
    6. Compute the second derivative (acceleration) in the same way.

    Derivative channels are appended to the returned raw object with the
    naming scheme ``<rb>_<type>_vel_<axis>`` and ``<rb>_<type>_acc_<axis>``,
    where *type* is ``eul`` or ``pos`` so that orientation and position
    derivatives always have distinct names (e.g. ``head_eul_vel_x``,
    ``head_pos_vel_x``).

    Parameters
    ----------
    raw : mne.io.BaseRaw
        Source recording.  Motion channels should be of type ``"misc"``
        (which is the default when XDFLoader imports non-EEG streams).
    rb_names : list of str | None
        Rigid body identifiers to process.  If ``None``, all identifiers
        found by :func:`find_rigid_bodies` are processed.
    lowpass_orient : float | None
        Low-pass cutoff (Hz) applied to orientation channels.  ``None``
        skips this filter.
    lowpass_pos : float | None
        Low-pass cutoff (Hz) applied to position channels.  ``None`` skips.
    lowpass_deriv : float | None
        Low-pass cutoff (Hz) applied to velocity and acceleration channels
        *after* differentiation.  ``None`` skips.
    compute_velocity : bool
        Whether to compute and append velocity channels.
    compute_acceleration : bool
        Whether to compute and append acceleration channels.
    sfreq_target : float | None
        If not ``None``, resample the recording to this rate after the
        quaternion conversion and before filtering and differentiation.
        Useful to match the EEG sample rate.
    unwrap : bool
        If ``True`` (default), unwrap the Euler angles over time
        (:func:`numpy.unwrap`), as in BeMoBIL.  Angles wrap at ±π, so a
        continuous rotation otherwise produces jumps of 2π that dominate
        the filtered signal and its derivatives.  The returned orientation
        channels are then continuous and may exceed ±π (±180°).
    angle_unit : ``"rad"`` | ``"deg"``
        Unit of Euler *input* channels (``<rb>_eul_*``), used to unwrap them
        with the right period (2π or 360°). Default ``"rad"``. A warning is
        logged when ``"rad"`` is given but the angles exceed ±2π, which
        usually means degrees. Euler angles computed from quaternions are
        always in radians.

    Returns
    -------
    raw_out : mne.io.Raw
        Copy of *raw* with quaternion channels replaced by Euler channels and
        velocity / acceleration channels appended.
    rb_info : dict
        Per-rigid-body processing summary:
        ``{rb_name: {"mode": "quat->euler"|"euler", "channels": list[str],
        "n_missing": int}}`` where ``n_missing`` is the number of bridged
        samples (at the input sampling rate).
    """
    if angle_unit not in ("rad", "deg"):
        raise ValueError(f"angle_unit must be 'rad' or 'deg', got {angle_unit!r}.")
    period = 2 * np.pi if angle_unit == "rad" else 360.0
    raw_out = raw.copy().load_data()

    if rb_names is None:
        rb_names = find_rigid_bodies(raw_out)

    if not rb_names:
        LOGGER.warning("process_rigid_body: no rigid body channels found.")
        return raw_out, {}

    # ------------------------------------------------------------------
    # Pass 1: orientation as (unwrapped) Euler angles for every rigid body
    # ------------------------------------------------------------------
    rb_channels: dict = {}
    for rb in rb_names:
        LOGGER.info(f"Processing rigid body: {rb}")
        quat_chs = [
            f"{rb}{s}" for s in _QUAT_SUFFIXES if f"{rb}{s}" in raw_out.ch_names
        ]
        eul_chs = [f"{rb}{s}" for s in _EUL_SUFFIXES if f"{rb}{s}" in raw_out.ch_names]
        pos_chs = [f"{rb}{s}" for s in _POS_SUFFIXES if f"{rb}{s}" in raw_out.ch_names]

        if not quat_chs and not eul_chs:
            LOGGER.warning(f"  {rb}: no orientation channels found, skipping.")
            continue

        missing = _missing_samples(raw_out, rb, (quat_chs or eul_chs) + pos_chs)
        if quat_chs and len(quat_chs) == len(_QUAT_SUFFIXES):
            q_norm = np.linalg.norm(raw_out.get_data(picks=quat_chs), axis=0)
            missing |= q_norm < 1e-10
        if missing.all():
            LOGGER.warning(f"  {rb}: no valid samples, skipping.")
            continue
        if missing.any():
            LOGGER.info(f"  {rb}: bridging {int(missing.sum())} missing sample(s).")

        if quat_chs:
            if len(quat_chs) != len(_QUAT_SUFFIXES):
                missing = sorted(
                    f"{rb}{s}" for s in _QUAT_SUFFIXES if f"{rb}{s}" not in quat_chs
                )
                raise ValueError(
                    f"Rigid body '{rb}' has incomplete quaternion channels; "
                    f"missing {missing}."
                )
            # Order: x, y, z, w
            q_data = raw_out.get_data(picks=quat_chs)  # (4, n_times)
            q_norm = np.linalg.norm(q_data, axis=0, keepdims=True)
            q_data = q_data / np.where(q_norm > 1e-10, q_norm, 1.0)
            euler_data = _quat_to_euler_zyx(q_data)  # (3, n_times)
            euler_data = _bridge(
                euler_data, missing, period=2 * np.pi if unwrap else None
            )

            new_ch_names = [f"{rb}_eul_x", f"{rb}_eul_y", f"{rb}_eul_z"]
            euler_raw = mne.io.RawArray(
                euler_data,
                mne.create_info(new_ch_names, raw_out.info["sfreq"], ["misc"] * 3),
                verbose=False,
            )
            euler_raw.set_meas_date(raw_out.info["meas_date"])

            # Add the Euler channels before dropping the quaternions, so a
            # recording that only holds this rigid body never becomes empty.
            raw_out.add_channels([euler_raw], force_update_info=True)
            raw_out.drop_channels(quat_chs)
            orient_chs, mode = new_ch_names, "quat->euler"
        else:
            orient_chs, mode = eul_chs, "euler"
            idx = [raw_out.ch_names.index(ch) for ch in orient_chs]
            if angle_unit == "rad" and np.nanmax(np.abs(raw_out._data[idx])) > (
                2 * np.pi + 1e-6
            ):
                LOGGER.warning(
                    f"  {rb}: Euler angles exceed ±2π although angle_unit='rad'; "
                    "they are probably in degrees. Pass angle_unit='deg' so they "
                    "are unwrapped with a 360° period."
                )
            raw_out._data[idx] = _bridge(
                raw_out._data[idx], missing, period=period if unwrap else None
            )

        if pos_chs:
            pos_idx = [raw_out.ch_names.index(ch) for ch in pos_chs]
            raw_out._data[pos_idx] = _bridge(raw_out._data[pos_idx], missing)
        _annotate_missing(raw_out, rb, missing)

        rb_channels[rb] = (orient_chs, pos_chs, mode, int(missing.sum()))

    # ------------------------------------------------------------------
    # Optional resampling (after conversion: quaternions must not be
    # interpolated component-wise because of q / -q sign flips)
    # ------------------------------------------------------------------
    if sfreq_target is not None and sfreq_target != raw_out.info["sfreq"]:
        raw_out.resample(sfreq_target)
    sfreq = raw_out.info["sfreq"]

    # ------------------------------------------------------------------
    # Pass 2: filtering and derivatives
    # ------------------------------------------------------------------
    rb_info: dict = {}
    for rb, (orient_chs, pos_chs, mode, n_missing) in rb_channels.items():
        if lowpass_orient is not None:
            orient_idx = [raw_out.ch_names.index(ch) for ch in orient_chs]
            raw_out._data[orient_idx] = _lowpass_array(
                raw_out._data[orient_idx], sfreq, lowpass_orient
            )

        if pos_chs and lowpass_pos is not None:
            pos_idx = [raw_out.ch_names.index(ch) for ch in pos_chs]
            raw_out._data[pos_idx] = _lowpass_array(
                raw_out._data[pos_idx], sfreq, lowpass_pos
            )

        all_src_chs = orient_chs + pos_chs
        src_data = raw_out.get_data(picks=all_src_chs)  # (n_chs, n_times)
        appended_chs: list[str] = list(orient_chs) + list(pos_chs)

        if compute_velocity:
            vel_data = np.gradient(src_data, 1.0 / sfreq, axis=1)
            if lowpass_deriv is not None:
                vel_data = _lowpass_array(vel_data, sfreq, lowpass_deriv)
            vel_names = [_src_to_deriv(ch, "_vel") for ch in all_src_chs]
            vel_raw = mne.io.RawArray(
                vel_data,
                mne.create_info(vel_names, sfreq, ["misc"] * len(vel_names)),
                verbose=False,
            )
            vel_raw.set_meas_date(raw_out.info["meas_date"])
            raw_out.add_channels([vel_raw], force_update_info=True)
            appended_chs.extend(vel_names)

            if compute_acceleration:
                acc_data = np.gradient(vel_data, 1.0 / sfreq, axis=1)
                if lowpass_deriv is not None:
                    acc_data = _lowpass_array(acc_data, sfreq, lowpass_deriv)
                acc_names = [_src_to_deriv(ch, "_acc") for ch in all_src_chs]
                acc_raw = mne.io.RawArray(
                    acc_data,
                    mne.create_info(acc_names, sfreq, ["misc"] * len(acc_names)),
                    verbose=False,
                )
                acc_raw.set_meas_date(raw_out.info["meas_date"])
                raw_out.add_channels([acc_raw], force_update_info=True)
                appended_chs.extend(acc_names)

        rb_info[rb] = {"mode": mode, "channels": appended_chs, "n_missing": n_missing}
        LOGGER.info(f"  {rb}: processed ({mode}), channels: {appended_chs}")

    return raw_out, rb_info


def split_by_rigid_body(raw, rb_names=None):
    """Return a dict of per-rigid-body Raw sub-objects.

    Picks all channels whose name starts with each rigid body identifier
    (including velocity / acceleration channels appended by
    :func:`process_rigid_body`).

    Parameters
    ----------
    raw : mne.io.BaseRaw
        Recording (typically the output of :func:`process_rigid_body`).
    rb_names : list of str | None
        Rigid body names.  Detected automatically when ``None``.

    Returns
    -------
    dict of {str: mne.io.Raw}
    """
    if rb_names is None:
        rb_names = find_rigid_bodies(raw)
    out = {}
    for rb in rb_names:
        chs = [ch for ch in raw.ch_names if ch.startswith(rb + "_")]
        if chs:
            out[rb] = raw.copy().pick(chs)
    return out


# %% Private helpers


def _missing_samples(raw, rb, chs):
    """Return a boolean mask of samples where rigid body *rb* is missing."""
    data = raw.get_data(picks=chs)
    missing = np.all(data == 0, axis=0) | np.any(~np.isfinite(data), axis=0)
    ann = raw.annotations
    sel = ann.description == f"BAD_{rb}_missing"
    if sel.any():
        orig = ann.orig_time
        starts = raw.time_as_index(ann.onset[sel], use_rounding=True, origin=orig)
        stops = raw.time_as_index(
            ann.onset[sel] + ann.duration[sel], use_rounding=True, origin=orig
        )
        for start, stop in zip(starts, stops):
            missing[max(start, 0) : max(stop, start + 1)] = True
    return missing


def _bridge(data, missing, period=None):
    """Unwrap (if *period*) and linearly interpolate rows across *missing*."""
    data = np.array(data, dtype=float)
    valid = ~missing
    if period is not None:
        data[:, valid] = np.unwrap(data[:, valid], axis=1, period=period)
    if missing.any():
        idx = np.arange(data.shape[1])
        for row in data:
            row[missing] = np.interp(idx[missing], idx[valid], row[valid])
    return data


def _annotate_missing(raw, rb, missing):
    """Annotate runs of *missing* as ``BAD_<rb>_missing`` unless already marked."""
    if not missing.any():
        return
    desc = f"BAD_{rb}_missing"
    sfreq = raw.info["sfreq"]
    already = np.zeros_like(missing)
    ann = raw.annotations
    sel = ann.description == desc
    if sel.any():
        orig = ann.orig_time
        a0 = raw.time_as_index(ann.onset[sel], use_rounding=True, origin=orig)
        a1 = raw.time_as_index(
            ann.onset[sel] + ann.duration[sel], use_rounding=True, origin=orig
        )
        for start, stop in zip(a0, a1):
            already[max(start, 0) : max(stop, start + 1)] = True
    todo = missing & ~already
    padded = np.concatenate([[False], todo, [False]])
    starts = np.flatnonzero(np.diff(padded.astype(int)) == 1)
    stops = np.flatnonzero(np.diff(padded.astype(int)) == -1)
    # Annotation onsets are relative to orig_time (meas_date) when it is
    # set, which raw.times is not: shift by first_time in that case.
    offset = raw.first_time if ann.orig_time is not None else 0.0
    for start, stop in zip(starts, stops):
        raw.annotations.append(raw.times[start] + offset, (stop - start) / sfreq, desc)


def _quat_to_euler_zyx(q):
    """Convert unit quaternions to ZYX Euler angles (yaw-pitch-roll).

    Parameters
    ----------
    q : ndarray, shape (4, n_times)
        Rows are qx, qy, qz, qw.

    Returns
    -------
    euler : ndarray, shape (3, n_times)
        Rows are roll (x), pitch (y), yaw (z) in radians.
    """
    qx, qy, qz, qw = q[0], q[1], q[2], q[3]

    # Roll (x)
    sinr_cosp = 2.0 * (qw * qx + qy * qz)
    cosr_cosp = 1.0 - 2.0 * (qx**2 + qy**2)
    roll = np.arctan2(sinr_cosp, cosr_cosp)

    # Pitch (y) - clamped to avoid arcsin domain errors from floating point
    sinp = 2.0 * (qw * qy - qz * qx)
    sinp = np.clip(sinp, -1.0, 1.0)
    pitch = np.arcsin(sinp)

    # Yaw (z)
    siny_cosp = 2.0 * (qw * qz + qx * qy)
    cosy_cosp = 1.0 - 2.0 * (qy**2 + qz**2)
    yaw = np.arctan2(siny_cosp, cosy_cosp)

    return np.vstack([roll, pitch, yaw])


def _lowpass_array(data, sfreq, cutoff):
    """Apply a zero-phase FIR low-pass filter to each row of *data*."""
    from mne.filter import filter_data

    return filter_data(
        data.astype(np.float64),
        sfreq=sfreq,
        l_freq=None,
        h_freq=float(cutoff),
        method="fir",
        fir_window="hamming",
        verbose=False,
    )


def _src_to_deriv(ch_name, suffix):
    """Rename a source channel to its derivative counterpart.

    Preserves the segment type so that orientation and position derivatives
    have distinct names and do not collide:

    ``head_eul_x`` → ``head_eul_vel_x`` (for suffix ``"_vel"``)
    ``head_pos_x`` → ``head_pos_vel_x`` (for suffix ``"_vel"``)
    """
    for segment in ("_eul_", "_pos_", "_vel_", "_quat_"):
        if segment in ch_name:
            axis = ch_name.split(segment)[-1]
            rb = ch_name.split(segment)[0]
            seg_type = segment.strip("_")  # "eul", "pos", "vel", "quat"
            return f"{rb}_{seg_type}{suffix}_{axis}"
    return f"{ch_name}{suffix}"
