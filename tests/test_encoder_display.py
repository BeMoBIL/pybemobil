"""NumpyEncoder handles numpy scalars; the report's display check per OS."""

import importlib
import json

import numpy as np
import pytest

from pybemobil.io.utils import NumpyEncoder

# pybemobil.preproc.make_report is shadowed by the function of that name
mr = importlib.import_module("pybemobil.preproc.make_report")


def test_numpy_encoder_scalars_and_arrays():
    """Integers, floats, bools and arrays become native JSON values."""
    data = {
        "n": np.int64(3),
        "x": np.float32(0.5),
        "ok": np.bool_(True),
        "a": np.arange(3),
    }
    assert json.loads(json.dumps(data, cls=NumpyEncoder)) == {
        "n": 3,
        "x": 0.5,
        "ok": True,
        "a": [0, 1, 2],
    }


@pytest.mark.parametrize(
    "platform, env, expected",
    [
        ("darwin", {}, True),
        ("win32", {}, True),
        ("linux", {}, False),
        ("linux", {"DISPLAY": ":0"}, True),
        ("linux", {"WAYLAND_DISPLAY": "wayland-0"}, True),
    ],
)
def test_gui_available(monkeypatch, platform, env, expected):
    """Windows and macOS have a display without DISPLAY; Linux needs one set."""
    monkeypatch.setattr(mr.sys, "platform", platform)
    monkeypatch.delenv("DISPLAY", raising=False)
    monkeypatch.delenv("WAYLAND_DISPLAY", raising=False)
    for key, value in env.items():
        monkeypatch.setenv(key, value)
    assert mr._gui_available() is expected
