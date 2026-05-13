import logging

from custom_components.Chargesplit.coordinator import _coerce_numeric


def test_casts_strings_and_ints_to_their_target_types():
    result = _coerce_numeric({"AMP": "13.5", "VOLT1": 230, "PILOTLIMIT": "25"})
    assert result["AMP"] == 13.5 and isinstance(result["AMP"], float)
    # 230 is int in input; float caster must lift it to 230.0 (Python's ==
    # treats 230 == 230.0 as True, so the isinstance check is what catches a
    # regression where the lift gets dropped).
    assert result["VOLT1"] == 230.0 and isinstance(result["VOLT1"], float)
    assert result["PILOTLIMIT"] == 25 and isinstance(result["PILOTLIMIT"], int)


def test_pilotlimit_handles_stringified_float():
    # Wallbox may send "25.0" as PILOTLIMIT; int("25.0") raises, but _to_int
    # goes through float() and truncates so the Select's str() compare works.
    result = _coerce_numeric({"PILOTLIMIT": "25.0"})
    assert result["PILOTLIMIT"] == 25 and isinstance(result["PILOTLIMIT"], int)


def test_warns_on_bad_value_and_leaves_it_unchanged(caplog):
    with caplog.at_level(logging.WARNING):
        result = _coerce_numeric({"AMP": "not-a-number"})
    assert result == {"AMP": "not-a-number"}
    # Locks the format: key, value, and target type all appear so a debugger
    # can identify the offending field and intent.
    assert "AMP" in caplog.text
    assert "not-a-number" in caplog.text
    assert "float" in caplog.text


def test_does_not_mutate_input():
    original = {"AMP": "13.5"}
    _coerce_numeric(original)
    assert original == {"AMP": "13.5"}


def test_skips_none_values():
    assert _coerce_numeric({"AMP": None}) == {"AMP": None}


def test_passes_through_non_numeric_keys():
    assert _coerce_numeric({"STATUS": "SCHEDULE", "MODEL": "WB132H"}) == {
        "STATUS": "SCHEDULE",
        "MODEL": "WB132H",
    }
