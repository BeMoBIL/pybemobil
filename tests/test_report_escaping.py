"""Tests that data-derived strings are escaped in the HTML report."""

import mne
import numpy as np

from pybemobil.preproc.make_report import _generate_bads_html, make_report


def _raw():
    rng = np.random.default_rng(0)
    montage = mne.channels.make_standard_montage("easycap-M1")
    info = mne.create_info(montage.ch_names[:8], 250.0, "eeg")
    raw = mne.io.RawArray(rng.standard_normal((8, 2500)) * 1e-6, info, verbose=False)
    raw.set_montage(montage)
    return raw


def test_report_escapes_markers_and_channel_names():
    """Marker strings and channel names cannot inject HTML into the report."""
    raw = _raw()
    raw.set_annotations(mne.Annotations([2], 0, ["<script>alert(1)</script>"]))
    report = make_report(
        raw_pre_ica=raw,
        raw_clean=raw,
        ica=mne.preprocessing.ICA(),
        ic_labels={},
        dipoles=[],
        residuals=[],
        trans=None,
        bad_ch_dict={
            "all_bads": ["<img src=x onerror=alert(2)>"],
            "pyprep": {"bad_all": ["<b>x</b>"]},
        },
    )
    html = "".join(report.html)
    assert "<script>alert(1)</script>" not in html
    assert "<img src=x onerror=alert(2)>" not in html
    assert "&lt;img src=x onerror=alert(2)&gt;" in html


def test_bads_html_escapes_every_field():
    """Keys, sub-keys and channel names are escaped; 'none' stays formatted."""
    html = _generate_bads_html(
        {"<k>": ["<a>"], "d": {"<s>": []}, "v": "<x>"}, "<t>", api_docs=None
    )
    for raw_text in ("<k>", "<a>", "<s>", "<x>", "<t>"):
        assert raw_text not in html
    assert "<em>none</em>" in html
