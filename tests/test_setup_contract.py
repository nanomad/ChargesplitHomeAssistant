"""v0.1.0 setup contract.

Captures the entity registry, device registry, and state-value spot checks
produced by v0.1.0 on a *fresh* install against the scrubbed fixture.

This is the post-rename baseline. The companion migration test in
`test_migration.py` covers what existing v0.0.x installs end up with after
auto-migration — and intentionally diverges from this contract on the
entity_id field, because migration preserves the v0.0.7 entity_ids
(statistics history is keyed on entity_id) while a fresh install computes
new ones from `has_entity_name=True` + the v0.1.0 names.
"""

from operator import itemgetter
from pathlib import Path
from unittest.mock import patch

from homeassistant.helpers import device_registry as dr, entity_registry as er
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.chargesplit.api import ChargesplitApi

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


async def test_v010_fresh_install_contract(hass):
    data = FIXTURE.read_bytes()

    entry = MockConfigEntry(
        version=1,
        domain="chargesplit",
        data={"serial": "TESTSERIAL", "code": "TESTSECRET"},
        title="TESTSERIAL",
    )
    entry.add_to_hass(hass)

    with patch.object(ChargesplitApi, "get_data", return_value=data):
        assert await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()

    entity_registry = er.async_get(hass)
    registry_entries = [
        e
        for e in entity_registry.entities.values()
        if e.config_entry_id == entry.entry_id
    ]
    entries = [_entity_snapshot(hass, e) for e in registry_entries]

    device_registry = dr.async_get(hass)
    devices = [
        _device_snapshot(d)
        for d in device_registry.devices.values()
        if entry.entry_id in d.config_entries
    ]

    device_ids = {e.device_id for e in registry_entries}
    assert (
        len(device_ids) == 1
    ), f"expected entities to share one device, got {device_ids}"

    assert sorted(entries, key=itemgetter("unique_id")) == sorted(
        EXPECTED_V010, key=itemgetter("unique_id")
    )
    assert sorted(devices, key=itemgetter("identifiers")) == sorted(
        EXPECTED_DEVICES, key=itemgetter("identifiers")
    )

    for entity_id, expected in EXPECTED_STATES.items():
        state = hass.states.get(entity_id)
        assert state is not None, f"{entity_id} did not register"
        assert (
            state.state == expected
        ), f"{entity_id}: expected {expected!r}, got {state.state!r}"


EXPECTED_V010 = [
    {
        "entity_id": "sensor.chargesplit_testserial_actual_amps",
        "unique_id": "TESTSERIAL_actual_amps",
        "platform": "chargesplit",
        "original_name": "Actual Amps",
        "entity_category": None,
        "disabled_by": None,
        "has_entity_name": True,
        "device_class": "current",
        "unit_of_measurement": "A",
        "state_class": "measurement",
    },
    {
        "entity_id": "sensor.chargesplit_testserial_charging_power",
        "unique_id": "TESTSERIAL_charging_power",
        "platform": "chargesplit",
        "original_name": "Charging Power",
        "entity_category": None,
        "disabled_by": None,
        "has_entity_name": True,
        "device_class": "power",
        "unit_of_measurement": "kW",
        "state_class": "measurement",
    },
    {
        "entity_id": "sensor.chargesplit_testserial_daily_house_energy",
        "unique_id": "TESTSERIAL_daily_house_wh",
        "platform": "chargesplit",
        "original_name": "Daily House Energy",
        "entity_category": None,
        "disabled_by": None,
        "has_entity_name": True,
        "device_class": "energy",
        "unit_of_measurement": "Wh",
        "state_class": "total_increasing",
    },
    {
        "entity_id": "sensor.chargesplit_testserial_daily_solar_energy",
        "unique_id": "TESTSERIAL_daily_solar_wh",
        "platform": "chargesplit",
        "original_name": "Daily Solar Energy",
        "entity_category": None,
        "disabled_by": None,
        "has_entity_name": True,
        "device_class": "energy",
        "unit_of_measurement": "Wh",
        "state_class": "total_increasing",
    },
    {
        "entity_id": "sensor.chargesplit_testserial_firmware",
        "unique_id": "TESTSERIAL_firmware",
        "platform": "chargesplit",
        "original_name": "Firmware",
        "entity_category": "diagnostic",
        "disabled_by": None,
        "has_entity_name": True,
        "device_class": None,
        "unit_of_measurement": None,
        "state_class": None,
    },
    {
        "entity_id": "sensor.chargesplit_testserial_house_consumption",
        "unique_id": "TESTSERIAL_house_power",
        "platform": "chargesplit",
        "original_name": "House Consumption",
        "entity_category": None,
        "disabled_by": None,
        "has_entity_name": True,
        "device_class": "power",
        "unit_of_measurement": "kW",
        "state_class": "measurement",
    },
    {
        "entity_id": "select.chargesplit_testserial_lock",
        "unique_id": "TESTSERIAL_lock_mode",
        "platform": "chargesplit",
        "original_name": "Lock",
        "entity_category": "config",
        "disabled_by": None,
        "has_entity_name": True,
        "device_class": None,
        "unit_of_measurement": None,
        "state_class": None,
    },
    {
        "entity_id": "sensor.chargesplit_testserial_model",
        "unique_id": "TESTSERIAL_model",
        "platform": "chargesplit",
        "original_name": "Model",
        "entity_category": "diagnostic",
        "disabled_by": None,
        "has_entity_name": True,
        "device_class": None,
        "unit_of_measurement": None,
        "state_class": None,
    },
    {
        "entity_id": "select.chargesplit_testserial_power_limit",
        "unique_id": "TESTSERIAL_operation_mode",
        "platform": "chargesplit",
        "original_name": "Power Limit",
        "entity_category": "config",
        "disabled_by": None,
        "has_entity_name": True,
        "device_class": None,
        "unit_of_measurement": None,
        "state_class": None,
    },
    {
        "entity_id": "select.chargesplit_testserial_pause",
        "unique_id": "TESTSERIAL_pause_mode",
        "platform": "chargesplit",
        "original_name": "Pause",
        "entity_category": "config",
        "disabled_by": None,
        "has_entity_name": True,
        "device_class": None,
        "unit_of_measurement": None,
        "state_class": None,
    },
    {
        "entity_id": "sensor.chargesplit_testserial_pilot_amps",
        "unique_id": "TESTSERIAL_pilot_amps",
        "platform": "chargesplit",
        "original_name": "Pilot Amps",
        "entity_category": None,
        "disabled_by": None,
        "has_entity_name": True,
        "device_class": "current",
        "unit_of_measurement": "A",
        "state_class": "measurement",
    },
    {
        "entity_id": "sensor.chargesplit_testserial_schedule",
        "unique_id": "TESTSERIAL_schedule",
        "platform": "chargesplit",
        "original_name": "Schedule",
        "entity_category": "diagnostic",
        "disabled_by": None,
        "has_entity_name": True,
        "device_class": None,
        "unit_of_measurement": None,
        "state_class": None,
    },
    {
        "entity_id": "sensor.chargesplit_testserial_serial",
        "unique_id": "TESTSERIAL_serial",
        "platform": "chargesplit",
        "original_name": "Serial",
        "entity_category": "diagnostic",
        "disabled_by": None,
        "has_entity_name": True,
        "device_class": None,
        "unit_of_measurement": None,
        "state_class": None,
    },
    {
        "entity_id": "sensor.chargesplit_testserial_solar_power",
        "unique_id": "TESTSERIAL_solar_power",
        "platform": "chargesplit",
        "original_name": "Solar Power",
        "entity_category": None,
        "disabled_by": None,
        "has_entity_name": True,
        "device_class": "power",
        "unit_of_measurement": "kW",
        "state_class": "measurement",
    },
    {
        "entity_id": "sensor.chargesplit_testserial_wallbox_status",
        "unique_id": "TESTSERIAL_status",
        "platform": "chargesplit",
        "original_name": "Wallbox Status",
        "entity_category": None,
        "disabled_by": None,
        "has_entity_name": True,
        "device_class": None,
        "unit_of_measurement": None,
        "state_class": None,
    },
    {
        "entity_id": "sensor.chargesplit_testserial_temperature",
        "unique_id": "TESTSERIAL_temperature",
        "platform": "chargesplit",
        "original_name": "Temperature",
        "entity_category": None,
        "disabled_by": None,
        "has_entity_name": True,
        "device_class": "temperature",
        "unit_of_measurement": "°C",
        "state_class": "measurement",
    },
    {
        "entity_id": "sensor.chargesplit_testserial_total_charged",
        "unique_id": "TESTSERIAL_total_charged_kwh",
        "platform": "chargesplit",
        "original_name": "Total Charged",
        "entity_category": None,
        "disabled_by": None,
        "has_entity_name": True,
        "device_class": "energy",
        "unit_of_measurement": "kWh",
        "state_class": "total_increasing",
    },
    {
        "entity_id": "sensor.chargesplit_testserial_voltage_l1",
        "unique_id": "TESTSERIAL_voltage_l1",
        "platform": "chargesplit",
        "original_name": "Voltage L1",
        "entity_category": None,
        "disabled_by": None,
        "has_entity_name": True,
        "device_class": "voltage",
        "unit_of_measurement": "V",
        "state_class": "measurement",
    },
    {
        "entity_id": "sensor.chargesplit_testserial_voltage_l2",
        "unique_id": "TESTSERIAL_voltage_l2",
        "platform": "chargesplit",
        "original_name": "Voltage L2",
        "entity_category": None,
        "disabled_by": None,
        "has_entity_name": True,
        "device_class": "voltage",
        "unit_of_measurement": "V",
        "state_class": "measurement",
    },
    {
        "entity_id": "sensor.chargesplit_testserial_voltage_l3",
        "unique_id": "TESTSERIAL_voltage_l3",
        "platform": "chargesplit",
        "original_name": "Voltage L3",
        "entity_category": None,
        "disabled_by": None,
        "has_entity_name": True,
        "device_class": "voltage",
        "unit_of_measurement": "V",
        "state_class": "measurement",
    },
]

EXPECTED_DEVICES = [
    {
        "identifiers": [("chargesplit", "TESTSERIAL")],
        "manufacturer": "Chargesplit",
        "model": "WB132H",
        "sw_version": "2.34",
        "name": "Chargesplit TESTSERIAL",
    },
]

EXPECTED_STATES = {
    "sensor.chargesplit_testserial_voltage_l1": "0.0",
    "sensor.chargesplit_testserial_voltage_l2": "0.0",
    "sensor.chargesplit_testserial_voltage_l3": "0.0",
    "sensor.chargesplit_testserial_temperature": "21.2",
    "sensor.chargesplit_testserial_wallbox_status": "SCHEDULE",
    "sensor.chargesplit_testserial_model": "WB132H",
    "sensor.chargesplit_testserial_firmware": "2.34",
    "sensor.chargesplit_testserial_serial": "TESTSERIAL",
    "sensor.chargesplit_testserial_total_charged": "0.0",
    "sensor.chargesplit_testserial_pilot_amps": "25",
    "sensor.chargesplit_testserial_actual_amps": "0.0",
    "sensor.chargesplit_testserial_solar_power": "0.52",
    "sensor.chargesplit_testserial_house_consumption": "0.52",
    "sensor.chargesplit_testserial_charging_power": "0.0",
    "sensor.chargesplit_testserial_daily_house_energy": "5450.41",
    "sensor.chargesplit_testserial_daily_solar_energy": "0.0",
    "sensor.chargesplit_testserial_schedule": "1",
    "select.chargesplit_testserial_power_limit": "25",
}
