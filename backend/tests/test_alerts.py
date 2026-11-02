from __future__ import annotations

from app import alerts


def test_normal_vitals_raise_nothing():
    assert alerts.evaluate({"HR": 80, "SPO2": 98, "NIBP_SBP": 120, "RR": 16, "TEMP": 37.0}) == []


def test_missing_vitals_are_skipped():
    assert alerts.evaluate({"HR": None}) == []
    assert alerts.evaluate({}) == []


def test_warning_and_critical_levels():
    out = alerts.evaluate({"HR": 125, "SPO2": 84})
    by_vital = {a["vital"]: a for a in out}
    assert by_vital["HR"]["level"] == "warning"
    assert by_vital["HR"]["message"] == "HR high (125 bpm)"
    assert by_vital["SPO2"]["level"] == "critical"
    assert by_vital["SPO2"]["message"] == "SPO2 low (84 %)"


def test_thresholds_are_inclusive():
    assert alerts.evaluate({"HR": 150})[0]["level"] == "critical"
    assert alerts.evaluate({"HR": 50})[0]["level"] == "warning"


def test_full_spo2_is_not_an_alarm():
    assert alerts.evaluate({"SPO2": 100}) == []
