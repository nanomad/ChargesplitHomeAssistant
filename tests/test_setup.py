from pathlib import Path
from unittest.mock import patch

from homeassistant.helpers import entity_registry as er
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.Chargesplit.api import ChargesplitApi

FIXTURE = Path(__file__).parent / "fixtures" / "wallbox_response.json"


async def test_setup_produces_correct_entities(hass):
    data = FIXTURE.read_bytes()

    entry = MockConfigEntry(
        domain="Chargesplit",
        data={"serial": "TESTSERIAL", "code": "TESTSECRET"},
        title="TESTSERIAL",
    )
    entry.add_to_hass(hass)

    with patch.object(ChargesplitApi, "get_data", return_value=data):
        assert await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()

    registry = er.async_get(hass)
    entries = [
        {
            "entity_id": e.entity_id,
            "unique_id": e.unique_id,
            "platform": e.platform,
            "original_name": e.original_name,
        }
        for e in registry.entities.values()
        if e.config_entry_id == entry.entry_id
    ]

    by_unique_id = lambda e: e["unique_id"]
    assert sorted(entries, key=by_unique_id) == sorted(EXPECTED_V007, key=by_unique_id)


EXPECTED_V007 = [
    {
        "entity_id": "sensor.chargesplit_domus_actual_amps",
        "unique_id": "Chargesplit-TESTSERIAL-Actual Amps-TESTSERIAL",
        "platform": "Chargesplit",
        "original_name": "Actual Amps",
    },
    {
        "entity_id": "sensor.chargesplit_domus_actual_house_consumption",
        "unique_id": "Chargesplit-TESTSERIAL-Actual House Consumption-TESTSERIAL",
        "platform": "Chargesplit",
        "original_name": "Actual House Consumption",
    },
    {
        "entity_id": "sensor.chargesplit_domus_actual_solar_power",
        "unique_id": "Chargesplit-TESTSERIAL-Actual solar power-TESTSERIAL",
        "platform": "Chargesplit",
        "original_name": "Actual solar power",
    },
    {
        "entity_id": "sensor.chargesplit_domus_car_charging_power",
        "unique_id": "Chargesplit-TESTSERIAL-Car Charging Power-TESTSERIAL",
        "platform": "Chargesplit",
        "original_name": "Car Charging Power",
    },
    {
        "entity_id": "sensor.chargesplit_domus_charged_kwh",
        "unique_id": "Chargesplit-TESTSERIAL-Charged kWh-TESTSERIAL",
        "platform": "Chargesplit",
        "original_name": "Charged kWh",
    },
    {
        "entity_id": "sensor.chargesplit_domus_daily_house_wh",
        "unique_id": "Chargesplit-TESTSERIAL-Daily House Wh-TESTSERIAL",
        "platform": "Chargesplit",
        "original_name": "Daily House Wh",
    },
    {
        "entity_id": "sensor.chargesplit_domus_daily_solar_wh",
        "unique_id": "Chargesplit-TESTSERIAL-Daily Solar Wh-TESTSERIAL",
        "platform": "Chargesplit",
        "original_name": "Daily Solar Wh",
    },
    {
        "entity_id": "sensor.chargesplit_domus_pilot_amps",
        "unique_id": "Chargesplit-TESTSERIAL-Pilot Amps-TESTSERIAL",
        "platform": "Chargesplit",
        "original_name": "Pilot Amps",
    },
    {
        "entity_id": "sensor.chargesplit_domus_schedule",
        "unique_id": "Chargesplit-TESTSERIAL-Schedule-TESTSERIAL",
        "platform": "Chargesplit",
        "original_name": "Schedule",
    },
    {
        "entity_id": "sensor.chargesplit_domus_temperature",
        "unique_id": "Chargesplit-TESTSERIAL-Temperature-TESTSERIAL",
        "platform": "Chargesplit",
        "original_name": "Temperature",
    },
    {
        "entity_id": "sensor.chargesplit_domus_voltage_l1",
        "unique_id": "Chargesplit-TESTSERIAL-Voltage L1-TESTSERIAL",
        "platform": "Chargesplit",
        "original_name": "Voltage L1",
    },
    {
        "entity_id": "sensor.chargesplit_domus_voltage_l2",
        "unique_id": "Chargesplit-TESTSERIAL-Voltage L2-TESTSERIAL",
        "platform": "Chargesplit",
        "original_name": "Voltage L2",
    },
    {
        "entity_id": "sensor.chargesplit_domus_voltage_l3",
        "unique_id": "Chargesplit-TESTSERIAL-Voltage L3-TESTSERIAL",
        "platform": "Chargesplit",
        "original_name": "Voltage L3",
    },
    {
        "entity_id": "sensor.chargesplit_domus_wallbox_model",
        "unique_id": "Chargesplit-TESTSERIAL-Wallbox Model-TESTSERIAL",
        "platform": "Chargesplit",
        "original_name": "Wallbox Model",
    },
    {
        "entity_id": "sensor.chargesplit_domus_wallbox_status",
        "unique_id": "Chargesplit-TESTSERIAL-Wallbox Status-TESTSERIAL",
        "platform": "Chargesplit",
        "original_name": "Wallbox Status",
    },
    {
        "entity_id": "sensor.chargesplit_domus_wallbox_firmware",
        "unique_id": "Chargesplit-TESTSERIAL-Wallbox firmware-TESTSERIAL",
        "platform": "Chargesplit",
        "original_name": "Wallbox firmware",
    },
    {
        "entity_id": "sensor.chargesplit_domus_wallbox_serial",
        "unique_id": "Chargesplit-TESTSERIAL-Wallbox serial-TESTSERIAL",
        "platform": "Chargesplit",
        "original_name": "Wallbox serial",
    },
    {
        "entity_id": "select.chargesplit_domus_send_lock_unlock_command",
        "unique_id": "TESTSERIAL-lock_mode",
        "platform": "Chargesplit",
        "original_name": "Send Lock/unlock command",
    },
    {
        "entity_id": "select.chargesplit_domus_select_chargepoint_power_amps",
        "unique_id": "TESTSERIAL-operation_mode",
        "platform": "Chargesplit",
        "original_name": "Select Chargepoint Power AMPS",
    },
    {
        "entity_id": "select.chargesplit_domus_send_pause_restart_command",
        "unique_id": "TESTSERIAL-pause_mode",
        "platform": "Chargesplit",
        "original_name": "Send pause/restart command",
    },
]
