"""Tests for ICLabel-based component selection in compute_ica."""

import mne
import numpy as np
import pytest


def _small_raw(rng):
    montage = mne.channels.make_standard_montage("easycap-M1")
    info = mne.create_info(montage.ch_names[:8], 250.0, "eeg")
    raw = mne.io.RawArray(rng.standard_normal((8, 250 * 20)) * 1e-5, info)
    raw.set_montage(montage)
    return raw


def _fake_iclabel_proba(winners):
    """Stand-in for iclabel_label_components with given (label, prob) winners."""
    from mne_icalabel.config import ICALABEL_METHODS_NUMERICAL_TO_STRING

    to_idx = {v: k for k, v in ICALABEL_METHODS_NUMERICAL_TO_STRING["iclabel"].items()}

    def _label(inst, ica, backend=None):
        proba = np.full((ica.n_components_, 7), 0.0)
        for i in range(ica.n_components_):
            label, p = winners[i % len(winners)]
            proba[i] = (1 - p) / 6
            proba[i, to_idx[label]] = p
        return proba

    return _label


@pytest.mark.parametrize(
    "kwargs, winners, expected",
    [
        # uncertain brain ICs are kept (they were all excluded before)
        ({"include_labels": ["brain"]}, [("brain", 0.6)], set()),
        # confident artifacts are removed, uncertain ones kept
        (
            {"include_labels": ["brain"]},
            [("eye blink", 0.9), ("eye blink", 0.5), ("brain", 0.6)],
            {0},
        ),
        (
            {"exclude_labels": ["eye blink"]},
            [("eye blink", 0.9), ("eye blink", 0.5), ("muscle artifact", 0.95)],
            {0},
        ),
        # default keep set (all but eye blink) in threshold mode
        ({}, [("eye blink", 0.8), ("muscle artifact", 0.9)], {0}),
    ],
)
def test_compute_ica_threshold_mode(rng, kwargs, winners, expected):
    """Threshold mode removes only confident ICs of classes to remove."""
    from unittest.mock import patch

    from pybemobil.preproc import utils

    with patch.object(utils, "iclabel_label_components", _fake_iclabel_proba(winners)):
        ica, _ = utils.compute_ica(
            _small_raw(rng), thresh=0.7, ica_method="picard", rng_seed=0, **kwargs
        )
    want = [i for i in range(ica.n_components_) if (i % len(winners)) in expected]
    assert ica.exclude == want


@pytest.mark.parametrize("key", ["include_labels", "exclude_labels"])
def test_iclabel_names_are_validated(key):
    """Misspelled ICLabel classes raise instead of silently matching nothing."""
    from pybemobil.preproc import EEGPreprocessor
    from pybemobil.preproc.utils import compute_ica

    with pytest.raises(ValueError, match="Unknown ICLabel class"):
        EEGPreprocessor(loader=None, **{key: ["eye"]})
    with pytest.raises(ValueError, match="Unknown ICLabel class"):
        compute_ica(None, **{key: ["muscle"]})
