import pytest

from app.alerts import RULES, evaluate

# The expected bands are read from RULES itself, so these tests check how
# evaluate() applies the table (boundaries, direction, skipping), not any
# clinical reference value.
IDS = [r[0] for r in RULES]


@pytest.mark.parametrize("rule", RULES, ids=IDS)
def test_low_critical_boundary_is_inclusive(rule):
    key, lo_c, lo_w, hi_w, hi_c, unit = rule
    (a,) = evaluate({key: lo_c})
    assert (a["vital"], a["level"]) == (key, "critical")
    assert a["message"] == f"{key} low ({lo_c} {unit})"
    assert evaluate({key: lo_c - 1})[0]["level"] == "critical"


@pytest.mark.parametrize("rule", RULES, ids=IDS)
def test_low_warning_band(rule):
    key, lo_c, lo_w, hi_w, hi_c, unit = rule
    (a,) = evaluate({key: lo_w})
    assert (a["level"], a["message"]) == ("warning", f"{key} low ({lo_w} {unit})")
    mid = (lo_c + lo_w) / 2
    assert evaluate({key: mid})[0]["level"] == "warning"
    assert evaluate({key: lo_w + 0.01}) == [] or lo_w + 0.01 >= hi_w


@pytest.mark.parametrize("rule", RULES, ids=IDS)
def test_high_side(rule):
    key, lo_c, lo_w, hi_w, hi_c, unit = rule
    if hi_w == hi_c:
        # the table has no separate warning band on the high side for this vital
        assert evaluate({key: hi_w - 0.01}) == []
        (a,) = evaluate({key: hi_c})
        assert (a["level"], a["message"]) == ("critical", f"{key} high ({hi_c} {unit})")
        return
    (w,) = evaluate({key: hi_w})
    assert (w["level"], w["message"]) == ("warning", f"{key} high ({hi_w} {unit})")
    assert evaluate({key: hi_w - 0.01}) == []
    (c,) = evaluate({key: hi_c})
    assert c["level"] == "critical" and "high" in c["message"]
    assert evaluate({key: hi_c - 0.01})[0]["level"] == "warning"


@pytest.mark.parametrize("rule", RULES, ids=IDS)
def test_value_strictly_between_warnings_is_silent(rule):
    key, lo_c, lo_w, hi_w, hi_c, unit = rule
    assert evaluate({key: (lo_w + hi_w) / 2}) == []


def test_missing_none_and_unknown_vitals_are_skipped():
    assert evaluate({}) == []
    assert evaluate({RULES[0][0]: None}) == []
    assert evaluate({"NOT_A_VITAL": 1e9}) == []


def test_multiple_alerts_follow_rule_order():
    vals = {r[0]: r[1] for r in RULES}  # every vital at its low-critical bound
    assert [a["vital"] for a in evaluate(vals)] == IDS
    reversed_input = dict(reversed(list(vals.items())))
    assert [a["vital"] for a in evaluate(reversed_input)] == IDS
