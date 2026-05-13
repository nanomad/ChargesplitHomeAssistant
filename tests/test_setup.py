"""v0.0.7 setup contract.

Captures the entity registry, device registry, and a few state-value
spot checks produced by the v0.0.7 codebase against a scrubbed fixture.

The v0.1.0 migration test on the pr-9 branch should NOT re-use this
pattern verbatim. The right shape for that test is: pre-populate the
entity + device registries with the EXPECTED_V007 / EXPECTED_DEVICES
rows below, THEN call async_setup under v0.1.0 code, THEN assert
nothing was renamed, orphaned, or had its statistics-keying attributes
flipped (state_class, unit_of_measurement, device_class). Setting up a
fresh entry under v0.1.0 doesn't exercise migration.
"""

from pathlib import Path
from unittest.mock import patch

from homeassistant.helpers import device_registry as dr, entity_registry as er
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.Chargesplit.api import ChargesplitApi

FIXTURE = Path(__file__).parent / "fixtures" / "wallbox_response.json"


def _entity_snapshot(hass, e):
    state = hass.states.get(e.entity_id)
    attrs = state.attributes if state else {}
    return {
        "entity_id": e.entity_id,
        "unique_id": e.unique_id,
        "platform": e.platform,
        "original_name": e.original_name,
        "entity_category": e.entity_category.value if e.entity_category else None,
        "disabled_by": e.disabled_by.value if e.disabled_by else None,
        "has_entity_name": e.has_entity_name,
        "device_class": attrs.get("device_class"),
        "unit_of_measurement": attrs.get("unit_of_measurement"),
        "state_class": attrs.get("state_class"),
    }


def _device_snapshot(d):
    return {
        "identifiers": sorted(d.identifiers),
        "manufacturer": d.manufacturer,
        "model": d.model,
        "sw_version": d.sw_version,
        "name": d.name,
    }


async def test_setup_produces_correct_entities(hass):
    data = FIXTURE.read_bytes()

    entry = MockConfigEntry(
        version=1,
        domain="Chargesplit",
        data={"serial": "TESTSERIAL", "code": "TESTSECRET"},
        title="TESTSERIAL",
    )
    entry.add_to_hass(hass)

    with patch.object(ChargesplitApi, "get_data", return_value=data):
        assert await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()

    entity_registry = er.async_get(hass)
    entries = [
        _entity_snapshot(hass, e)
        for e in entity_registry.entities.values()
        if e.config_entry_id == entry.entry_id
    ]

    device_registry = dr.async_get(hass)
    devices = [
        _device_snapshot(d)
        for d in device_registry.devices.values()
        if entry.entry_id in d.config_entries
    ]

    by_unique_id = lambda e: e["unique_id"]
    assert sorted(entries, key=by_unique_id) == sorted(EXPECTED_V007, key=by_unique_id)

    by_identifiers = lambda d: str(d["identifiers"])
    assert sorted(devices, key=by_identifiers) == sorted(EXPECTED_DEVICES, key=by_identifiers)

    # State-value assertions: every sensor's JSON-key -> state wiring is locked.
    for entity_id, expected in EXPECTED_STATES.items():
        actual = hass.states.get(entity_id).state
        assert actual == expected, f"{entity_id}: expected {expected!r}, got {actual!r}"


EXPECTED_V007 = [
    {
        "entity_id": "sensor.chargesplit_domus_actual_amps",
        "unique_id": "Chargesplit-TESTSERIAL-Actual Amps-TESTSERIAL",
        "platform": "Chargesplit",
        "original_name": "Actual Amps",
        "entity_category": None,
        "disabled_by": None,
        "has_entity_name": False,
        "device_class": "current",
        "unit_of_measurement": "A",
        "state_class": "measurement",
    },
    {
        "entity_id": "sensor.chargesplit_domus_actual_house_consumption",
        "unique_id": "Chargesplit-TESTSERIAL-Actual House Consumption-TESTSERIAL",
        "platform": "Chargesplit",
        "original_name": "Actual House Consumption",
        "entity_category": None,
        "disabled_by": None,
        "has_entity_name": False,
        "device_class": "power",
        "unit_of_measurement": "kW",
        "state_class": "measurement",
    },
    {
        "entity_id": "sensor.chargesplit_domus_actual_solar_power",
        "unique_id": "Chargesplit-TESTSERIAL-Actual solar power-TESTSERIAL",
        "platform": "Chargesplit",
        "original_name": "Actual solar power",
        "entity_category": None,
        "disabled_by": None,
        "has_entity_name": False,
        "device_class": "power",
        "unit_of_measurement": "kW",
        "state_class": "measurement",
    },
    {
        "entity_id": "sensor.chargesplit_domus_car_charging_power",
        "unique_id": "Chargesplit-TESTSERIAL-Car Charging Power-TESTSERIAL",
        "platform": "Chargesplit",
        "original_name": "Car Charging Power",
        "entity_category": None,
        "disabled_by": None,
        "has_entity_name": False,
        "device_class": "power",
        "unit_of_measurement": "kW",
        "state_class": "measurement",
    },
    {
        "entity_id": "sensor.chargesplit_domus_charged_kwh",
        "unique_id": "Chargesplit-TESTSERIAL-Charged kWh-TESTSERIAL",
        "platform": "Chargesplit",
        "original_name": "Charged kWh",
        "entity_category": None,
        "disabled_by": None,
        "has_entity_name": False,
        "device_class": "energy",
        "unit_of_measurement": "kWh",
        "state_class": "total_increasing",
    },
    {
        "entity_id": "sensor.chargesplit_domus_daily_house_wh",
        "unique_id": "Chargesplit-TESTSERIAL-Daily House Wh-TESTSERIAL",
        "platform": "Chargesplit",
        "original_name": "Daily House Wh",
        "entity_category": None,
        "disabled_by": None,
        "has_entity_name": False,
        "device_class": "energy",
        "unit_of_measurement": "Wh",
        "state_class": "total_increasing",
    },
    {
        "entity_id": "sensor.chargesplit_domus_daily_solar_wh",
        "unique_id": "Chargesplit-TESTSERIAL-Daily Solar Wh-TESTSERIAL",
        "platform": "Chargesplit",
        "original_name": "Daily Solar Wh",
        "entity_category": None,
        "disabled_by": None,
        "has_entity_name": False,
        "device_class": "energy",
        "unit_of_measurement": "Wh",
        "state_class": "total_increasing",
    },
    {
        "entity_id": "sensor.chargesplit_domus_pilot_amps",
        "unique_id": "Chargesplit-TESTSERIAL-Pilot Amps-TESTSERIAL",
        "platform": "Chargesplit",
        "original_name": "Pilot Amps",
        "entity_category": None,
        "disabled_by": None,
        "has_entity_name": False,
        "device_class": "current",
        "unit_of_measurement": "A",
        "state_class": "measurement",
    },
    {
        "entity_id": "sensor.chargesplit_domus_schedule",
        "unique_id": "Chargesplit-TESTSERIAL-Schedule-TESTSERIAL",
        "platform": "Chargesplit",
        "original_name": "Schedule",
        "entity_category": "diagnostic",
        "disabled_by": None,
        "has_entity_name": False,
        "device_class": None,
        "unit_of_measurement": None,
        "state_class": None,
    },
    {
        "entity_id": "sensor.chargesplit_domus_temperature",
        "unique_id": "Chargesplit-TESTSERIAL-Temperature-TESTSERIAL",
        "platform": "Chargesplit",
        "original_name": "Temperature",
        "entity_category": None,
        "disabled_by": None,
        "has_entity_name": False,
        "device_class": "temperature",
        "unit_of_measurement": "°C",
        "state_class": "measurement",
    },
    {
        "entity_id": "sensor.chargesplit_domus_voltage_l1",
        "unique_id": "Chargesplit-TESTSERIAL-Voltage L1-TESTSERIAL",
        "platform": "Chargesplit",
        "original_name": "Voltage L1",
        "entity_category": None,
        "disabled_by": None,
        "has_entity_name": False,
        "device_class": "voltage",
        "unit_of_measurement": "V",
        "state_class": "measurement",
    },
    {
        "entity_id": "sensor.chargesplit_domus_voltage_l2",
        "unique_id": "Chargesplit-TESTSERIAL-Voltage L2-TESTSERIAL",
        "platform": "Chargesplit",
        "original_name": "Voltage L2",
        "entity_category": None,
        "disabled_by": None,
        "has_entity_name": False,
        "device_class": "voltage",
        "unit_of_measurement": "V",
        "state_class": "measurement",
    },
    {
        "entity_id": "sensor.chargesplit_domus_voltage_l3",
        "unique_id": "Chargesplit-TESTSERIAL-Voltage L3-TESTSERIAL",
        "platform": "Chargesplit",
        "original_name": "Voltage L3",
        "entity_category": None,
        "disabled_by": None,
        "has_entity_name": False,
        "device_class": "voltage",
        "unit_of_measurement": "V",
        "state_class": "measurement",
    },
    {
        "entity_id": "sensor.chargesplit_domus_wallbox_model",
        "unique_id": "Chargesplit-TESTSERIAL-Wallbox Model-TESTSERIAL",
        "platform": "Chargesplit",
        "original_name": "Wallbox Model",
        "entity_category": "diagnostic",
        "disabled_by": None,
        "has_entity_name": False,
        "device_class": None,
        "unit_of_measurement": None,
        "state_class": None,
    },
    {
        "entity_id": "sensor.chargesplit_domus_wallbox_status",
        "unique_id": "Chargesplit-TESTSERIAL-Wallbox Status-TESTSERIAL",
        "platform": "Chargesplit",
        "original_name": "Wallbox Status",
        "entity_category": None,
        "disabled_by": None,
        "has_entity_name": False,
        "device_class": None,
        "unit_of_measurement": None,
        "state_class": None,
    },
    {
        "entity_id": "sensor.chargesplit_domus_wallbox_firmware",
        "unique_id": "Chargesplit-TESTSERIAL-Wallbox firmware-TESTSERIAL",
        "platform": "Chargesplit",
        "original_name": "Wallbox firmware",
        "entity_category": "diagnostic",
        "disabled_by": None,
        "has_entity_name": False,
        "device_class": None,
        "unit_of_measurement": None,
        "state_class": None,
    },
    {
        "entity_id": "sensor.chargesplit_domus_wallbox_serial",
        "unique_id": "Chargesplit-TESTSERIAL-Wallbox serial-TESTSERIAL",
        "platform": "Chargesplit",
        "original_name": "Wallbox serial",
        "entity_category": "diagnostic",
        "disabled_by": None,
        "has_entity_name": False,
        "device_class": None,
        "unit_of_measurement": None,
        "state_class": None,
    },
    {
        "entity_id": "select.chargesplit_domus_send_lock_unlock_command",
        "unique_id": "TESTSERIAL-lock_mode",
        "platform": "Chargesplit",
        "original_name": "Send Lock/unlock command",
        "entity_category": "config",
        "disabled_by": None,
        "has_entity_name": False,
        "device_class": None,
        "unit_of_measurement": None,
        "state_class": None,
    },
    {
        "entity_id": "select.chargesplit_domus_select_chargepoint_power_amps",
        "unique_id": "TESTSERIAL-operation_mode",
        "platform": "Chargesplit",
        "original_name": "Select Chargepoint Power AMPS",
        "entity_category": "config",
        "disabled_by": None,
        "has_entity_name": False,
        "device_class": None,
        "unit_of_measurement": None,
        "state_class": None,
    },
    {
        "entity_id": "select.chargesplit_domus_send_pause_restart_command",
        "unique_id": "TESTSERIAL-pause_mode",
        "platform": "Chargesplit",
        "original_name": "Send pause/restart command",
        "entity_category": "config",
        "disabled_by": None,
        "has_entity_name": False,
        "device_class": None,
        "unit_of_measurement": None,
        "state_class": None,
    },
]

EXPECTED_DEVICES = [
    {
        "identifiers": [("Chargesplit", "TESTSERIAL")],
        "manufacturer": "Chargesplit Domus",
        "model": "WB132H",
        "sw_version": "2.34",
        "name": "Chargesplit Domus",
    },
]

EXPECTED_STATES = {
    # TODO(v0.0.8): The next five suffer from type-passthrough.
    # HOUSEPWR/SOLARPWR/CHARGINGPWR/TOTALCHARGED come from the wallbox API
    # as JSON strings even at rest; AMP is an int in this fixture but is
    # expected to return as a string during active charging (the fixture
    # only captures the resting state). The sensor doesn't cast, so HA's
    # recorder coerces via float() for stats and logs a warning every
    # cycle. v0.0.8 should cast in the coordinator. When that lands,
    # "0.00" becomes "0.0" here; AMP's "0" may also shift to "0.0".
    "sensor.chargesplit_domus_actual_amps": "0",
    "sensor.chargesplit_domus_actual_house_consumption": "0.52",
    "sensor.chargesplit_domus_actual_solar_power": "0.52",
    "sensor.chargesplit_domus_car_charging_power": "0.00",
    "sensor.chargesplit_domus_charged_kwh": "0.00",
    # DAYHOUSE in the fixture is 5450.409999999997; HA rounds for display/stats.
    "sensor.chargesplit_domus_daily_house_wh": "5450.41",
    "sensor.chargesplit_domus_daily_solar_wh": "0",
    "sensor.chargesplit_domus_pilot_amps": "25",
    "sensor.chargesplit_domus_schedule": "1",
    "sensor.chargesplit_domus_temperature": "21.2",
    "sensor.chargesplit_domus_voltage_l1": "0",
    "sensor.chargesplit_domus_voltage_l2": "0",
    "sensor.chargesplit_domus_voltage_l3": "0",
    "sensor.chargesplit_domus_wallbox_firmware": "2.34",
    "sensor.chargesplit_domus_wallbox_model": "WB132H",
    "sensor.chargesplit_domus_wallbox_serial": "TESTSERIAL",
    "sensor.chargesplit_domus_wallbox_status": "SCHEDULE",
}
