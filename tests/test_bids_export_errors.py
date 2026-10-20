"""Tests for BIDS dataset description fields and batch export errors."""

import json

from pybemobil.io.bids_export import make_bids_dataset_description


def test_dataset_description_omits_unset_fields(tmp_path):
    """Unset License and DOI are left out instead of written as ''."""
    make_bids_dataset_description(tmp_path, name="x")
    desc = json.loads((tmp_path / "dataset_description.json").read_text())
    assert "License" not in desc
    assert "DatasetDOI" not in desc
    make_bids_dataset_description(tmp_path, name="x", data_license="CC0", doi="doi:1")
    desc = json.loads((tmp_path / "dataset_description.json").read_text())
    assert desc["License"] == "CC0"
