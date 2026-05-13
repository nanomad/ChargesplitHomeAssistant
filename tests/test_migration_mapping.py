"""Unit tests for migrate_unique_id — the pure-function part of the migration."""

import pytest

from custom_components.chargesplit.migration import migrate_unique_id


SERIAL = "TESTSERIAL"


# Every (old_unique_id, expected_new_unique_id) pair derivable from the
# v0.0.7 contract (see tests/test_setup.py EXPECTED_V007 on `main`).
SENSOR_CASES = [
    ("Chargesplit-TESTSERIAL-Voltage L1-TESTSERIAL", "TESTSERIAL_voltage_l1"),
    ("Chargesplit-TESTSERIAL-Voltage L2-TESTSERIAL", "TESTSERIAL_voltage_l2"),
    ("Chargesplit-TESTSERIAL-Voltage L3-TESTSERIAL", "TESTSERIAL_voltage_l3"),
    ("Chargesplit-TESTSERIAL-Temperature-TESTSERIAL", "TESTSERIAL_temperature"),
    ("Chargesplit-TESTSERIAL-Wallbox Status-TESTSERIAL", "TESTSERIAL_status"),
    ("Chargesplit-TESTSERIAL-Wallbox Model-TESTSERIAL", "TESTSERIAL_model"),
    ("Chargesplit-TESTSERIAL-Wallbox firmware-TESTSERIAL", "TESTSERIAL_firmware"),
    ("Chargesplit-TESTSERIAL-Wallbox serial-TESTSERIAL", "TESTSERIAL_serial"),
    ("Chargesplit-TESTSERIAL-Charged kWh-TESTSERIAL", "TESTSERIAL_total_charged_kwh"),
    ("Chargesplit-TESTSERIAL-Pilot Amps-TESTSERIAL", "TESTSERIAL_pilot_amps"),
    ("Chargesplit-TESTSERIAL-Actual Amps-TESTSERIAL", "TESTSERIAL_actual_amps"),
    ("Chargesplit-TESTSERIAL-Actual solar power-TESTSERIAL", "TESTSERIAL_solar_power"),
    ("Chargesplit-TESTSERIAL-Actual House Consumption-TESTSERIAL", "TESTSERIAL_house_power"),
    ("Chargesplit-TESTSERIAL-Car Charging Power-TESTSERIAL", "TESTSERIAL_charging_power"),
    ("Chargesplit-TESTSERIAL-Daily House Wh-TESTSERIAL", "TESTSERIAL_daily_house_wh"),
    ("Chargesplit-TESTSERIAL-Daily Solar Wh-TESTSERIAL", "TESTSERIAL_daily_solar_wh"),
    ("Chargesplit-TESTSERIAL-Schedule-TESTSERIAL", "TESTSERIAL_schedule"),
]

SELECT_CASES = [
    ("TESTSERIAL-operation_mode", "TESTSERIAL_operation_mode"),
    ("TESTSERIAL-lock_mode", "TESTSERIAL_lock_mode"),
    ("TESTSERIAL-pause_mode", "TESTSERIAL_pause_mode"),
]


@pytest.mark.parametrize("old, new", SENSOR_CASES + SELECT_CASES)
def test_recognized(old, new):
    assert migrate_unique_id(old, SERIAL) == new


@pytest.mark.parametrize(
    "old",
    [
        # Already in the new format — not a v0.0.x id, leave it alone.
        "TESTSERIAL_voltage_l1",
        # Wrong serial.
        "Chargesplit-OTHERSERIAL-Voltage L1-OTHERSERIAL",
        # Unknown description — fail closed.
        "Chargesplit-TESTSERIAL-Cosmic Rays-TESTSERIAL",
        # Garbage.
        "",
        "TESTSERIAL",
    ],
)
def test_unrecognized(old):
    assert migrate_unique_id(old, SERIAL) is None


def test_serial_with_dash_is_parsed_safely():
    # Hyphenated serials are anchored end-to-end; the description in the
    # middle still resolves cleanly.
    serial = "ABC-123"
    assert (
        migrate_unique_id(
            f"Chargesplit-{serial}-Voltage L1-{serial}", serial
        )
        == f"{serial}_voltage_l1"
    )
    assert (
        migrate_unique_id(f"{serial}-operation_mode", serial)
        == f"{serial}_operation_mode"
    )
