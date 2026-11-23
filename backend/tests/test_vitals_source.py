import numpy as np
import pytest

from app import vitals_source as vs

NAN = np.nan
TEMP_COL = vs.VITAL_KEYS.index("TEMP")
HR_COL = vs.VITAL_KEYS.index("HR")


def series(rows):
    return np.array(rows, dtype=float)


def test_track_tables_are_consistent():
    assert len(vs.TRACK_NAMES) == len(vs.VITAL_KEYS) == len(set(vs.VITAL_KEYS))
    assert vs.WAVEFORM_KEYS == ["ECG", "PLETH"]


def test_forward_fill_per_column_without_mutating_input():
    raw = series([[1, NAN], [NAN, 5], [NAN, NAN], [7, NAN]])
    out = vs._forward_fill(raw)
    assert out[:, 0].tolist() == [1, 1, 1, 7]
    assert np.isnan(out[0, 1]) and out[1:, 1].tolist() == [5, 5, 5]  # leading gap stays missing
    assert np.isnan(raw[1, 0])  # original untouched


def test_mask_implausible_uses_inclusive_bounds_and_only_configured_keys():
    lo, hi = vs.PLAUSIBLE_RANGES["TEMP"]
    raw = np.zeros((5, len(vs.VITAL_KEYS)))
    raw[:, TEMP_COL] = [lo, hi, lo - 0.01, hi + 0.01, (lo + hi) / 2]
    raw[:, HR_COL] = [-5, 0, 1e6, 1, 2]
    out = vs._mask_implausible(raw, vs.VITAL_KEYS)
    assert np.isnan(out[:, TEMP_COL]).tolist() == [False, False, True, True, False]
    assert not np.isnan(out[:, HR_COL]).any()  # no bounds configured for HR
    assert not np.isnan(raw).any()  # input untouched


def make_source(vitaldb_fake, rows, **kw):
    vitaldb_fake.case_data = lambda cid, tracks, interval: series(rows)
    return vs.BedSource("Bed-T", 5, **kw)


def full_row(**kw):
    row = [1.0] * len(vs.VITAL_KEYS)
    for k, v in kw.items():
        row[vs.VITAL_KEYS.index(k)] = v
    return row


def test_bedsource_masks_then_forward_fills_temperature(vitaldb_fake):
    lo, hi = vs.PLAUSIBLE_RANGES["TEMP"]
    src = make_source(vitaldb_fake, [full_row(TEMP=36.6), full_row(TEMP=lo - 5), full_row(TEMP=hi + 5)])
    assert [src.tick(t)["TEMP"] for t in range(3)] == [36.6, 36.6, 36.6]  # dropouts hold the last good value


def test_bedsource_leading_dropout_reports_none(vitaldb_fake):
    lo, hi = vs.PLAUSIBLE_RANGES["TEMP"]
    src = make_source(vitaldb_fake, [full_row(TEMP=lo - 1), full_row(TEMP=36.0)])
    assert src.tick(0)["TEMP"] is None
    assert src.tick(1)["TEMP"] == 36.0


def test_tick_rounds_to_one_decimal_wraps_and_maps_keys(vitaldb_fake):
    src = make_source(vitaldb_fake, [full_row(HR=80.04), full_row(HR=80.06)])
    assert src.length == 2
    assert src.tick(0)["HR"] == 80.0
    assert src.tick(1)["HR"] == 80.1
    assert src.tick(2) == src.tick(0) and src.tick(3) == src.tick(1)  # t % length
    assert set(src.tick(0)) == set(vs.VITAL_KEYS)


def test_load_case_called_with_numeric_tracks_at_one_second(vitaldb_fake):
    make_source(vitaldb_fake, [full_row()])
    assert ("load_case", 5, tuple(vs.TRACK_NAMES), vs.SAMPLE_INTERVAL_SEC) in vitaldb_fake.calls


def test_encounter_length_defaults_to_case_length_unless_overridden(vitaldb_fake):
    rows = [full_row()] * 4
    assert make_source(vitaldb_fake, rows).encounter_length == 4
    assert make_source(vitaldb_fake, rows, encounter_length=40).encounter_length == 40


def wave_source(vitaldb_fake, n=300):
    src = make_source(vitaldb_fake, [full_row()])
    w = np.column_stack([np.arange(n, dtype=float), np.arange(n, dtype=float) * 10])
    w[7, 0] = NAN
    vitaldb_fake.case_data = lambda cid, tracks, interval: w
    return src


def test_waveform_lazy_loaded_once(vitaldb_fake):
    src = wave_source(vitaldb_fake)
    assert src.waveform is None and src.waveform_length == 0
    src.ensure_waveform_loaded()
    first = src.waveform
    n_calls = len(vitaldb_fake.calls)
    src.ensure_waveform_loaded()
    assert src.waveform is first and len(vitaldb_fake.calls) == n_calls
    assert src.waveform_length == 300
    assert ("load_case", 5, tuple(vs.WAVEFORM_TRACK_NAMES), 1 / vs.WAVEFORM_HZ) in vitaldb_fake.calls


def test_waveform_window_is_half_open_with_hz_samples_and_none_for_nan(vitaldb_fake):
    src = wave_source(vitaldb_fake)
    out = src.waveform_window(0, 1)
    assert set(out) == {"ECG", "PLETH"}
    assert len(out["ECG"]) == vs.WAVEFORM_HZ
    # sample 7 was NaN; forward-filled from sample 6
    assert out["ECG"][6] == 6.0 and out["ECG"][7] == 6.0 and out["ECG"][8] == 8.0
    assert out["PLETH"][3] == 30.0
    nxt = src.waveform_window(1, 2)
    assert nxt["ECG"][0] == 100.0  # window [1,2) starts right where [0,1) ended
    assert len(src.waveform_window(0, 3)["ECG"]) == 3 * vs.WAVEFORM_HZ


def test_waveform_window_wraps_around_case_length(vitaldb_fake):
    src = wave_source(vitaldb_fake, n=250)
    out = src.waveform_window(2, 3)  # starts at sample 200, 100 samples -> wraps past 250
    assert out["ECG"][0] == 200.0 and out["ECG"][49] == 249.0 and out["ECG"][50] == 0.0
    assert src.waveform_window(5, 6)["ECG"][0] == 0.0  # 500 % 250


def test_waveform_nan_with_no_prior_value_is_none(vitaldb_fake):
    src = make_source(vitaldb_fake, [full_row()])
    w = np.full((100, 2), NAN)
    vitaldb_fake.case_data = lambda cid, tracks, interval: w
    out = src.waveform_window(0, 1)
    assert out["ECG"][0] is None and out["PLETH"][99] is None


def test_pick_case_ids_even_spacing_and_guard(vitaldb_fake, monkeypatch):
    monkeypatch.setattr(vitaldb_fake, "find_cases", lambda tracks: list(range(100, 130)))
    assert vs.pick_case_ids(3) == [100, 110, 120]
    assert vs.pick_case_ids(30) == list(range(100, 130))
    monkeypatch.setattr(vitaldb_fake, "find_cases", lambda tracks: [1, 2, 3, 4])
    assert vs.pick_case_ids(3) == [1, 2, 3]  # step floors to 1
    with pytest.raises(RuntimeError, match="only 4 cases"):
        vs.pick_case_ids(5)


def test_temperature_mask_keeps_febrile_values_and_drops_probe_dropout():
    raw = np.array([[41.5], [15.0], [30.0], [42.0]])
    out = vs._mask_implausible(raw, ["TEMP"])
    assert out[0, 0] == 41.5 and out[2, 0] == 30.0 and out[3, 0] == 42.0
    assert np.isnan(out[1, 0])
