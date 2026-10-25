"""Threshold alarm rules: boundaries are inclusive on the alarm side."""
import pytest

from app.alerts import evaluate


def _levels(vitals):
    return {(a["vital"], a["level"]) for a in evaluate(vitals)}


def test_normal_vitals_raise_nothing():
    assert evaluate({"HR": 75, "SPO2": 98, "NIBP_SBP": 120, "RR": 14, "TEMP": 36.8}) == []


@pytest.mark.parametrize("hr,level", [(40, "critical"), (41, "warning"), (50, "warning"), (51, None),
                                      (119, None), (120, "warning"), (149, "warning"), (150, "critical")])
def test_heart_rate_bands(hr, level):
    alerts = evaluate({"HR": hr})
    assert (alerts[0]["level"] if alerts else None) == level


def test_direction_in_message():
    msgs = {a["vital"]: a["message"] for a in evaluate({"HR": 35, "RR": 32})}
    assert msgs["HR"].startswith("HR low") and msgs["RR"].startswith("RR high")


def test_spo2_100_is_not_an_alarm_but_85_is_critical():
    assert evaluate({"SPO2": 100}) == []
    assert _levels({"SPO2": 85}) == {("SPO2", "critical")}


def test_missing_values_skipped():
    assert evaluate({"HR": None, "TEMP": None}) == []
