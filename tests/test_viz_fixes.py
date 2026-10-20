"""Regression tests for plotting functions in pybemobil.viz."""

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt  # noqa: E402
import mne  # noqa: E402
import numpy as np  # noqa: E402
import pytest  # noqa: E402

from pybemobil.viz import plotting  # noqa: E402

CHS = ["Fz", "Cz", "Pz", "Oz", "C3", "C4", "P3", "P4"]


@pytest.fixture
def raw_abc():
    """Raw with three alternating events a, b and c."""
    rng = np.random.default_rng(0)
    raw = mne.io.RawArray(
        rng.standard_normal((8, 6000)) * 1e-6,
        mne.create_info(CHS, 100.0, "eeg"),
        verbose=False,
    )
    raw.set_montage(mne.channels.make_standard_montage("easycap-M1"))
    onsets = np.arange(2, 58, 2.0)
    raw.set_annotations(
        mne.Annotations(onsets, 0, [["a", "b", "c"][i % 3] for i in range(len(onsets))])
    )
    return raw


def test_various_erps_subtraction_keeps_other_events(raw_abc):
    """Subtracting b from a still plots the non-target event c."""
    fig = plotting.plot_various_ERPs(
        raw_abc,
        event_id={"a": 1, "b": 2, "c": 3},
        subtraction_event="b",
        subtraction_targets=["a"],
    )
    assert fig is not None
    plt.close("all")


def test_various_erps_subtraction_group_mode(raw_abc):
    """Group mode with a subtraction event works (b is not plotted)."""
    fig = plotting.plot_various_ERPs(
        [raw_abc, raw_abc.copy()],
        event_id={"a": 1, "b": 2},
        subtraction_event="b",
        subtraction_targets=["a"],
    )
    assert fig is not None
    plt.close("all")
