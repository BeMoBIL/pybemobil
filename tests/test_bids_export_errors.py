"""Tests for BIDS dataset description fields and batch export errors."""

import json

import mne
import numpy as np
import pytest

from pybemobil.io.bids_export import batch_export_to_bids, make_bids_dataset_description


def test_dataset_description_omits_unset_fields(tmp_path):
    """Unset License and DOI are left out instead of written as ''."""
    make_bids_dataset_description(tmp_path, name="x")
    desc = json.loads((tmp_path / "dataset_description.json").read_text())
    assert "License" not in desc
    assert "DatasetDOI" not in desc
    make_bids_dataset_description(tmp_path, name="x", data_license="CC0", doi="doi:1")
    desc = json.loads((tmp_path / "dataset_description.json").read_text())
    assert desc["License"] == "CC0"


def _bad_entry():
    info = mne.create_info(["Cz"], 250.0, "eeg")
    raw = mne.io.RawArray(np.zeros((1, 250)), info, verbose=False)
    return {"raw": raw, "subject": "01", "run": "x/y"}  # invalid run label


def test_batch_export_can_raise(tmp_path):
    """With on_error='raise' a failing run stops the batch."""
    with pytest.raises(Exception):
        batch_export_to_bids([_bad_entry()], tmp_path, on_error="raise")


def test_batch_export_warns_and_continues(tmp_path):
    """By default a failure is a visible warning and the batch continues."""
    with pytest.warns(RuntimeWarning, match="BIDS export failed for sub-01"):
        assert batch_export_to_bids([_bad_entry()], tmp_path) == []
