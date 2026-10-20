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


@pytest.fixture
def epochs_abc(raw_abc):
    """Epochs of the a/b/c events."""
    events, event_id = mne.events_from_annotations(raw_abc, verbose=False)
    return mne.Epochs(
        raw_abc, events, event_id, tmin=-0.2, tmax=0.8, preload=True, verbose=False
    )


def test_psd_ci_spans_epochs_for_one_object(epochs_abc):
    """With a single Epochs object the CI is computed across its epochs."""
    psd = plotting._prepare_psd({"a": epochs_abc["a"]}, fmin=1, fmax=30, picks=["Cz"])
    assert psd["a"]["all"].shape[0] == len(epochs_abc["a"])
    assert np.all(psd["a"]["all"].std(axis=0) > 0)  # a band of non-zero width


def test_psd_accepts_spectrum_baseline(epochs_abc):
    """Spectrum baselines (as documented) are accepted."""
    spec = epochs_abc["b"].compute_psd(fmin=1, fmax=30, verbose=False)
    fig = plotting.plot_PSD({"a": epochs_abc["a"]}, 1, 30, baseline_dict={"a": spec})
    assert fig is not None
    plt.close("all")


@pytest.mark.parametrize("kwargs", [{"combine": "mean"}, {}])
def test_erp_spans_drawn_on_used_axes(epochs_abc, kwargs):
    """Baseline and ROI spans are drawn with and without channel combination."""
    fig = plotting.plot_ERP(
        {"a": epochs_abc["a"]},
        picks=["Cz", "Pz"],
        baseline=(-0.2, 0),
        roi=(0.3, 0.5),
        **kwargs,
    )
    assert sum(len(ax.patches) for ax in fig.axes) >= 2
    plt.close("all")


def test_tfr_on_ica_sources_without_picks(raw_abc, epochs_abc):
    """plot_TFR plots ICA sources (misc channels) when picks is None."""
    ica = mne.preprocessing.ICA(n_components=4, method="picard", random_state=0)
    ica.fit(raw_abc.copy().filter(1, None, verbose=False), verbose=False)
    sources = ica.get_sources(epochs_abc)
    out = plotting.plot_TFR(
        {"a": sources["a"]}, freqs=np.arange(4, 12.0), is_sources=True
    )
    assert out
    plt.close("all")
