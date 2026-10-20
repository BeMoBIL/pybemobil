"""Tests for pybemobil.io.xdf."""

# %% Imports

import logging

import numpy as np
import pytest

from pybemobil.io.xdf import (
    _FIF_CH_ABBREVIATIONS,
    _FIF_MAX_CH_LEN,
    XDFLoader,
    _match_stream,
    _shorten_fif_ch_names,
    _unit_scale,
)

# %% _shorten_fif_ch_names


def test_shorten_passthrough_short_names():
    """Pass short names through unchanged."""
    names = ["Cz", "EEG001", "pupil_left"]
    assert _shorten_fif_ch_names(names) == names


def test_shorten_uses_abbreviation_table():
    """Replace known long names with MNE short form."""
    # "EyeballCenterX-0" is 16 chars -> triggers abbreviation lookup
    names = ["EyeballCenterX-0", "EyeballCenterX-1"]
    result = _shorten_fif_ch_names(names)
    assert result == ["eyeball_x_l", "eyeball_x_r"]


def test_shorten_all_known_eye_tracker_channels():
    """Map all long abbreviation entries correctly."""
    long_names = [n for n in _FIF_CH_ABBREVIATIONS if len(n) > _FIF_MAX_CH_LEN]
    assert long_names, "Expected at least some names > 15 chars in the table"
    result = _shorten_fif_ch_names(long_names)
    for original, shortened in zip(long_names, result):
        assert len(shortened) <= _FIF_MAX_CH_LEN, (
            f"{original!r} -> {shortened!r} is {len(shortened)} chars"
        )
        assert shortened == _FIF_CH_ABBREVIATIONS[original]


def test_shorten_fallback_truncates_unknown():
    """Truncate unknown names to exactly 15 chars."""
    name = "ThisIsAVeryLongChannelName"
    result = _shorten_fif_ch_names([name])
    assert len(result[0]) == _FIF_MAX_CH_LEN
    assert result[0] == name[:_FIF_MAX_CH_LEN]


def test_shorten_deduplicates_on_truncation():
    """Deduplicate names that truncate to same prefix."""
    # Create two names that share the first 15 characters
    base = "A" * _FIF_MAX_CH_LEN
    name1 = base + "X"
    name2 = base + "Y"
    result = _shorten_fif_ch_names([name1, name2])
    assert result[0] != result[1], "Truncated names must be disambiguated"
    assert all(len(r) <= _FIF_MAX_CH_LEN for r in result)


def test_shorten_output_all_within_limit():
    """Keep all output names within FIF limit."""
    mixed = [
        "short",
        "EyelidAngleTopLeft",  # in table
        "UnknownVeryLongChannelName",  # fallback
        "AnotherLongNameThatWontFit",  # fallback (may collide)
    ]
    result = _shorten_fif_ch_names(mixed)
    for name in result:
        assert len(name) <= _FIF_MAX_CH_LEN


def test_shorten_output_unique():
    """Returned names must be globally unique."""
    names = ["EyelidAngleTopLeft", "AnotherLongChannelNameThatTruncatesToSamePrefix"]
    result = _shorten_fif_ch_names(names)
    assert len(result) == len(set(result))


def test_shorten_logs_rename(caplog):
    """Log each rename at INFO level."""
    with caplog.at_level(logging.INFO):
        _shorten_fif_ch_names(["EyeballCenterX-0"])  # 16 chars -> triggers rename
    assert "EyeballCenterX-0" in caplog.text


# %% _unit_scale


@pytest.mark.parametrize(
    "unit, expected",
    [
        ("microvolt", 1e-6),
        ("microvolts", 1e-6),
        ("µV", 1e-6),
        ("uV", 1e-6),
        ("V", 1.0),
        ("volt", 1.0),
        ("Volt", 1.0),
        ("NA", 1.0),
        ("", 1.0),
    ],
)
def test_unit_scale_known_units(unit, expected):
    """Return correct scale factor for known units."""
    assert _unit_scale(unit) == pytest.approx(expected)


def test_unit_scale_unknown_unit_warns(caplog):
    """Warn and return 1.0 for unknown units."""
    with caplog.at_level(logging.WARNING):
        scale = _unit_scale("furlong", ch_name="ch0")
    assert scale == pytest.approx(1.0)
    assert "furlong" in caplog.text


def test_unit_scale_case_insensitive():
    """Verify _unit_scale matches unit strings case-insensitively."""
    assert _unit_scale("MICROVOLT") == pytest.approx(1e-6)
    assert _unit_scale("MicroVolt") == pytest.approx(1e-6)


# %% _match_stream


def _make_stream(name="EEG", stream_type="EEG", source_id="device01"):
    """Return a minimal XDF stream dict."""
    return {
        "info": {
            "name": [name],
            "type": [stream_type],
            "source_id": [source_id],
            "channel_count": ["1"],
        },
        "time_series": [],
        "time_stamps": [],
    }


def test_match_stream_by_name():
    """Verify _match_stream finds a stream matching by name."""
    streams = [_make_stream("EEG"), _make_stream("EMG")]
    result = _match_stream(streams, name="EEG")
    assert result["info"]["name"][0] == "EEG"


def test_match_stream_by_type():
    """Verify _match_stream finds a stream matching by stream_type."""
    streams = [
        _make_stream("A", stream_type="EEG"),
        _make_stream("B", stream_type="EMG"),
    ]
    result = _match_stream(streams, stream_type="EMG")
    assert result["info"]["name"][0] == "B"


def test_match_stream_by_source_id():
    """Verify _match_stream finds a stream matching by source_id."""
    streams = [
        _make_stream(source_id="device01"),
        _make_stream(source_id="device02"),
    ]
    result = _match_stream(streams, source_id="device02")
    assert result["info"]["source_id"][0] == "device02"


def test_match_stream_no_match_returns_none():
    """Return None when no stream matches."""
    streams = [_make_stream("EEG")]
    result = _match_stream(streams, name="NonExistent")
    assert result is None


def test_match_stream_allow_multiple():
    """Return all matching streams when allow_multiple=True."""
    streams = [_make_stream("EEG", stream_type="EEG")] * 3
    result = _match_stream(streams, stream_type="EEG", allow_multiple=True)
    assert isinstance(result, list)
    assert len(result) == 3


def test_match_stream_allow_multiple_no_match_returns_empty_list():
    """Return empty list when allow_multiple and no match."""
    streams = [_make_stream("EEG")]
    result = _match_stream(streams, name="Ghost", allow_multiple=True)
    assert result == []


def test_match_stream_multiple_warns_and_returns_first(caplog):
    """Warn and return first when multiple streams match."""
    streams = [_make_stream("EEG")] * 2
    with caplog.at_level(logging.WARNING):
        result = _match_stream(streams, name="EEG")
    assert result is not None
    assert "Multiple" in caplog.text


# %% XDFLoader._build_raw with synthetic streams


def _stream(name, stype, ts, data, srate, labels=None, units=None, ch_type="misc"):
    data = data if isinstance(data, list) else np.asarray(data)
    n_ch = len(data[0]) if len(data) else 1
    info = {
        "name": [name],
        "type": [stype],
        "source_id": [name],
        "nominal_srate": [str(srate)],
        "effective_srate": float(srate),
        "channel_count": [str(n_ch)],
        "desc": [None],
    }
    if labels:
        units = units or ["NA"] * len(labels)
        chans = [
            {"label": [lab], "type": [ch_type], "unit": [u]}
            for lab, u in zip(labels, units)
        ]
        info["desc"] = [{"channels": [{"channel": chans}]}]
    return {"info": info, "time_stamps": np.asarray(ts, float), "time_series": data}


T0 = 1000.0


@pytest.fixture
def eeg_stream():
    """Two-channel 500 Hz EEG stream lasting 10 s."""
    ts = T0 + np.arange(0, 10, 1 / 500)
    data = np.random.default_rng(0).standard_normal((len(ts), 2))
    return _stream("eeg", "EEG", ts, data, 500, ["Cz", "Pz"], ["uV", "uV"], "eeg")


def test_build_raw_multichannel_markers(eeg_stream):
    """Each marker sample yields one annotation, channels joined by '/'."""
    mk = _stream("mk", "Markers", [T0 + 1, T0 + 5], [["a", "x"], ["b", "y"]], 0)
    raw, _, _, _ = XDFLoader()._build_raw([eeg_stream, mk])
    assert list(raw.annotations.description) == ["a/x", "b/y"]
    np.testing.assert_allclose(raw.annotations.onset, [1, 5])


def test_build_raw_drops_markers_outside_recording(eeg_stream, caplog):
    """Markers before the first EEG sample are not added with negative onsets."""
    mk = _stream("mk", "Markers", [T0 - 2, T0 + 3], [["early"], ["ok"]], 0)
    with caplog.at_level(logging.WARNING):
        raw, _, _, _ = XDFLoader()._build_raw([eeg_stream, mk])
    assert list(raw.annotations.description) == ["ok"]
    assert "outside the recorded EEG range" in caplog.text


def test_build_raw_irregular_special_stream_goes_to_events(eeg_stream):
    """An irregular special stream ends up in events under its label."""
    fix = _stream("fixations", "Fixations", [T0 + 3, T0 + 4], [["f1"], ["f2"]], 0)
    loader = XDFLoader(special_streams={"fix": {"name": "fixations"}})
    _, _, events, _ = loader._build_raw([eeg_stream, fix])
    assert list(events) == ["fix"]
    descriptions, ts = events["fix"]
    assert descriptions == ["f1", "f2"]
    np.testing.assert_allclose(ts, [3, 4])


def test_build_raw_millivolt_units():
    """EEG in millivolts is scaled to volts."""
    ts = T0 + np.arange(0, 2, 1 / 100)
    eeg = _stream("eeg", "EEG", ts, np.ones((len(ts), 1)), 100, ["Cz"], ["mV"], "eeg")
    raw, _, _, _ = XDFLoader()._build_raw([eeg])
    np.testing.assert_allclose(raw.get_data()[0], 1e-3)


def test_build_raw_aux_aligns_to_eeg_samples(eeg_stream):
    """t=0 is the first EEG sample and aux data match the EEG sample times."""
    ts = T0 + 2.0013 + np.arange(0, 6, 1 / 120)  # not on the EEG sample grid
    gaze = _stream("gaze", "Gaze", ts, np.c_[ts - T0, ts - T0], 120, ["gx", "gy"])
    mk = _stream("mk", "Markers", [T0 + 4.0], [["m"]], 0)
    loader = XDFLoader(special_streams={"gaze": {"name": "gaze"}})
    raw, _, _, session_t0 = loader._build_raw([eeg_stream, gaze, mk])

    eeg_ts = eeg_stream["time_stamps"]
    assert session_t0 == pytest.approx(eeg_ts[0])
    assert raw.n_times == len(eeg_ts)
    # gaze holds its own LSL time, so where it covers the EEG it must equal
    # the EEG sample time
    covered = (eeg_ts >= ts[0]) & (eeg_ts <= ts[-1])
    np.testing.assert_allclose(
        raw.get_data(picks="gx")[0, covered], eeg_ts[covered] - T0, atol=1e-9
    )
    np.testing.assert_allclose(
        raw.annotations.onset[raw.annotations.description == "m"],
        [T0 + 4.0 - session_t0],
    )


def test_loader_rejects_crop_with_explanation():
    """Cropping is not offered because of frequent MoBI dropouts."""
    with pytest.raises(ValueError, match="dropouts"):
        XDFLoader(on_mismatch="crop")


def test_build_raw_missing_annotation_covers_last_sample(eeg_stream):
    """A gap annotation that reaches the end covers the final sample too."""
    ts = T0 + np.arange(0, 8, 1 / 100)  # ends 2 s before the EEG
    gaze = _stream("gaze", "Gaze", ts, np.c_[np.sin(ts)], 100, ["gx"])
    loader = XDFLoader(special_streams={"gaze": {"name": "gaze"}}, on_mismatch="pad")
    raw, _, _, _ = loader._build_raw([eeg_stream, gaze])
    (onset,), (duration,) = raw.annotations.onset, raw.annotations.duration
    assert onset + duration == pytest.approx(raw.times[-1] + 1 / 500)


@pytest.mark.parametrize("kind", ["fif", "elc", "name", "object"])
def test_set_montage_sources(tmp_path, kind):
    """Montages can be given as FIF/ELC files, standard names or objects."""
    import mne

    montage = mne.channels.make_standard_montage("easycap-M1")
    raw = mne.io.RawArray(
        np.zeros((2, 10)), mne.create_info(["Cz", "Pz"], 100.0, "eeg")
    )
    if kind == "fif":
        spec = tmp_path / "cap-dig.fif"
        montage.save(spec)
    elif kind == "elc":
        spec = str(tmp_path / "cap.elc")
        pos = montage.get_positions()["ch_pos"]
        lines = ["NumberPositions= 2", "UnitPosition m", "Positions"]
        lines += [" ".join(map(str, pos[ch])) for ch in ("Cz", "Pz")]
        lines += ["Labels", "Cz", "Pz"]
        (tmp_path / "cap.elc").write_text("\n".join(lines) + "\n")
    elif kind == "name":
        spec = "easycap-M1"
    else:
        spec = montage
    XDFLoader(montage=spec)._set_montage(raw)
    got = raw.get_montage().get_positions()["ch_pos"]
    assert set(got) == {"Cz", "Pz"}


# %% Timing: nominal rate, dropouts, drift


def test_build_raw_uses_nominal_srate():
    """The sampling rate is nominal_srate, not pyxdf's effective_srate."""
    ts = T0 + np.arange(0, 4, 1 / 500)
    eeg = _stream("eeg", "EEG", ts, np.zeros((len(ts), 1)), 500, ["Cz"], ["uV"], "eeg")
    eeg["info"]["effective_srate"] = 400.0  # e.g. lowered by a dropout
    raw, _, _, _ = XDFLoader()._build_raw([eeg])
    assert raw.info["sfreq"] == 500


def _gap_eeg(sfreq=500.0, gap=(4.0, 6.0), duration=10.0):
    t = np.arange(0, duration, 1 / sfreq)
    t = t[(t < gap[0]) | (t >= gap[1])]
    ts = T0 + t
    x = np.sin(2 * np.pi * 10 * t)
    eeg = _stream("eeg", "EEG", ts, np.c_[x], sfreq, ["Cz"], ["V"], "eeg")
    eeg["info"]["effective_srate"] = (len(ts) - 1) / (ts[-1] - ts[0])
    return eeg


def test_build_raw_fills_eeg_dropout(caplog):
    """A dropout is filled and annotated, and markers keep their LSL times."""
    eeg = _gap_eeg()
    mk = _stream("mk", "Markers", [T0 + 3.0, T0 + 8.0], [["a"], ["b"]], 0)
    with caplog.at_level(logging.WARNING):
        raw, _, _, _ = XDFLoader()._build_raw([eeg, mk])
    assert raw.info["sfreq"] == 500
    assert raw.n_times == 5000
    ann = {
        d: (o, dur)
        for d, o, dur in zip(
            *(
                raw.annotations.description,
                raw.annotations.onset,
                raw.annotations.duration,
            )
        )
    }
    np.testing.assert_allclose(ann["a"][0], 3.0)
    np.testing.assert_allclose(ann["b"][0], 8.0)
    np.testing.assert_allclose(ann["BAD_eeg_missing"], (4.0, 2.0), atol=1e-9)
    # samples after the gap are at their true time again
    t = raw.times
    after = t >= 6.0
    np.testing.assert_allclose(
        raw.get_data()[0, after], np.sin(2 * np.pi * 10 * t[after]), atol=1e-9
    )
    assert "dropout" in caplog.text


def test_build_raw_gap_aux_alignment_matches_eeg_grid():
    """Aux streams are aligned to the filled grid, including after the gap."""
    eeg = _gap_eeg()
    ts = T0 + np.arange(0, 10, 1 / 100)
    clock = _stream("clk", "Clock", ts, np.c_[ts - T0], 100, ["clk"])
    loader = XDFLoader(special_streams={"clk": {"name": "clk"}})
    raw, _, _, _ = loader._build_raw([eeg, clock])
    covered = raw.times <= 9.99  # the clock stream ends 8 ms before the EEG
    np.testing.assert_allclose(
        raw.get_data(picks="clk")[0, covered], raw.times[covered], atol=1e-6
    )


@pytest.mark.parametrize("kind", ["jitter", "chunked"])
def test_build_raw_no_false_gaps(kind, caplog):
    """Timestamp jitter and chunked timestamps are not mistaken for dropouts."""
    sfreq = 500.0
    t = np.arange(0, 10, 1 / sfreq)
    if kind == "jitter":
        t = t + np.random.default_rng(1).uniform(-0.45, 0.45, t.size) / sfreq
    else:  # 20 samples share the timestamp of the chunk's last sample
        t = (np.floor(np.arange(t.size) / 20) * 20 + 19) / sfreq
    eeg = _stream(
        "eeg", "EEG", T0 + t, np.zeros((t.size, 1)), sfreq, ["Cz"], ["V"], "eeg"
    )
    with caplog.at_level(logging.WARNING):
        raw, _, _, _ = XDFLoader()._build_raw([eeg])
    assert raw.n_times == t.size
    assert "BAD_eeg_missing" not in raw.annotations.description
    assert "dropout" not in caplog.text


def test_build_raw_markers_follow_clock_drift(caplog):
    """With a drifting device clock, markers stay on the sample they belong to."""
    sfreq = 500.0
    n = 5000
    ts = T0 + np.arange(n) / (sfreq * 1.005)  # device runs 0.5 % fast
    eeg = _stream("eeg", "EEG", ts, np.zeros((n, 1)), sfreq, ["Cz"], ["V"], "eeg")
    mk = _stream("mk", "Markers", [ts[4000]], [["m"]], 0)
    with caplog.at_level(logging.WARNING):
        raw, _, _, _ = XDFLoader()._build_raw([eeg, mk])
    np.testing.assert_allclose(raw.annotations.onset, [4000 / sfreq])
    assert "differs from the nominal" in caplog.text


def _write_xdf(path, eeg_ts, eeg_data, sfreq, markers):
    """Write a minimal XDF file (EEG stream plus one marker stream)."""
    import struct

    def chunk(tag, content):
        body = struct.pack("<H", tag) + content
        return struct.pack("<B", 4) + struct.pack("<I", len(body)) + body

    def varlen(n):
        return struct.pack("<B", 4) + struct.pack("<I", n)

    chans = "".join(
        f"<channel><label>ch{i}</label><type>EEG</type><unit>microvolts</unit>"
        "</channel>"
        for i in range(eeg_data.shape[1])
    )
    eeg_xml = (
        '<?xml version="1.0"?><info><name>eeg</name><type>EEG</type>'
        f"<channel_count>{eeg_data.shape[1]}</channel_count>"
        f"<nominal_srate>{sfreq}</nominal_srate><channel_format>float32"
        "</channel_format><source_id>eeg</source_id>"
        f"<desc><channels>{chans}</channels></desc></info>"
    )
    mk_xml = (
        '<?xml version="1.0"?><info><name>mk</name><type>Markers</type>'
        "<channel_count>1</channel_count><nominal_srate>0</nominal_srate>"
        "<channel_format>string</channel_format><source_id>mk</source_id></info>"
    )
    eeg_samples = struct.pack("<I", 1) + varlen(len(eeg_ts))
    for t, row in zip(eeg_ts, eeg_data):
        eeg_samples += (
            struct.pack("<B", 8)
            + struct.pack("<d", t)
            + struct.pack(f"<{len(row)}f", *row)
        )
    mk_samples = struct.pack("<I", 2) + varlen(len(markers))
    for t, s in markers:
        b = s.encode()
        mk_samples += struct.pack("<B", 8) + struct.pack("<d", t) + varlen(len(b)) + b

    def footer(sid, first, last, n):
        xml = (
            f'<?xml version="1.0"?><info><first_timestamp>{first}</first_timestamp>'
            f"<last_timestamp>{last}</last_timestamp><sample_count>{n}"
            "</sample_count><clock_offsets></clock_offsets></info>"
        )
        return chunk(6, struct.pack("<I", sid) + xml.encode())

    blob = b"XDF:" + chunk(
        1, b'<?xml version="1.0"?><info><version>1.0</version></info>'
    )
    blob += chunk(2, struct.pack("<I", 1) + eeg_xml.encode())
    blob += chunk(2, struct.pack("<I", 2) + mk_xml.encode())
    blob += chunk(3, eeg_samples) + chunk(3, mk_samples)
    blob += footer(1, eeg_ts[0], eeg_ts[-1], len(eeg_ts))
    blob += footer(2, markers[0][0], markers[-1][0], len(markers))
    path.write_bytes(blob)


@pytest.mark.parametrize("dejitter", [False, True])
def test_load_real_xdf_with_dropout(tmp_path, dejitter):
    """End to end through pyxdf: a 2 s dropout keeps rate, spectrum and events."""
    sfreq = 500.0
    t = np.arange(0, 10, 1 / sfreq)
    t = t[(t < 4) | (t >= 6)]
    x = 10 * np.sin(2 * np.pi * 50 * t)
    path = tmp_path / "gap.xdf"
    _write_xdf(
        path, T0 + t, np.c_[x, x], sfreq, [(T0 + 3.0, "pre"), (T0 + 8.0, "post")]
    )

    raw = XDFLoader(dejitter_timestamps=dejitter).load(path).raw
    assert raw.info["sfreq"] == sfreq
    desc = list(raw.annotations.description)
    onsets = dict(zip(desc, raw.annotations.onset))
    assert set(desc) == {"pre", "post", "BAD_eeg_missing"}
    np.testing.assert_allclose([onsets["pre"], onsets["post"]], [3.0, 8.0], atol=1e-6)
    good = raw.copy().crop(6.0, None)
    psd = good.compute_psd(fmax=100, picks="ch0", verbose=False)
    assert psd.freqs[np.argmax(psd.get_data()[0])] == pytest.approx(50, abs=1)


# %% Units of auxiliary streams


def test_build_raw_scales_aux_voltage_units(eeg_stream):
    """An ECG in microvolts from a separate amplifier is converted to volts."""
    ts = T0 + np.arange(0, 10, 1 / 250)
    ecg = _stream(
        "ecg", "ECG", ts, np.full((len(ts), 1), 1000.0), 250, ["ECG"], ["uV"], "ecg"
    )
    loader = XDFLoader(special_streams={"ecg": {"name": "ecg"}})
    raw, _, _, _ = loader._build_raw([eeg_stream, ecg])
    np.testing.assert_allclose(raw.get_data(picks="ECG")[0, :-10], 1e-3)


def test_build_raw_keeps_non_voltage_aux_units(eeg_stream, caplog):
    """Gaze in pixels is not rescaled and does not warn about volts."""
    ts = T0 + np.arange(0, 10, 1 / 120)
    gaze = _stream("gaze", "Gaze", ts, np.full((len(ts), 1), 640.0), 120, ["gx"])
    gaze["info"]["desc"][0]["channels"][0]["channel"][0]["unit"] = ["pixels"]
    loader = XDFLoader(special_streams={"gaze": {"name": "gaze"}})
    with caplog.at_level(logging.WARNING):
        raw, _, _, _ = loader._build_raw([eeg_stream, gaze])
    np.testing.assert_allclose(raw.get_data(picks="gx")[0, :-10], 640.0)
    assert "Unrecognised unit" not in caplog.text


# %% Option validation


@pytest.mark.parametrize(
    "kwargs",
    [
        {"on_mismatch": "trim"},
        {"alignment_method": "cubic"},
        {"special_streams": {"ecg": {"name": "ecg", "method": "spline"}}},
    ],
)
def test_loader_rejects_invalid_options(kwargs):
    """Typos in option values raise instead of silently using a default."""
    with pytest.raises(ValueError, match="must be"):
        XDFLoader(**kwargs)


def test_align_rejects_unknown_method():
    """align_stream_to_timestamps does not fall back to linear for typos."""
    from pybemobil.io.alignment import align_stream_to_timestamps

    ts = np.arange(10.0)
    with pytest.raises(ValueError, match="Unknown alignment method"):
        align_stream_to_timestamps(ts, ts, ts, method="cubic")
