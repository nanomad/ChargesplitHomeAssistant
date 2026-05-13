"""Integration test for v0.0.9's migration to the new chargesplit integration.

Limitation of the test environment: the new `chargesplit` integration
(hass-chargesplit) isn't on disk here, so when `async_migrate_entry`
calls `async_add(new_chargesplit_entry)` HA can't run its setup —
the entry lands in `not_loaded` state and platforms never call
`async_get_or_create` to adopt the pre-migrated rows. That last step
(row adoption + entity_id preservation under the new entry) only runs
in production where hass-chargesplit is installed.

What we DO verify here, which is everything v0.0.9 itself is responsible for:

- Pre-rewriting entity registry rows: new platform=`chargesplit`,
  new unique_id in the v0.1.0 shape.
- Rewriting device identifiers from ("Chargesplit", serial) to
  ("chargesplit", serial).
- Creating a chargesplit-domain config entry with the same credentials.
- Scheduling removal of the legacy entry.
- A persistent notification announcing the migration.
- Detaching unrecognized rows so they aren't cascade-deleted with the
  legacy entry.
"""

from pathlib import Path
from unittest.mock import patch

import pytest

from homeassistant.components import persistent_notification
from homeassistant.helpers import device_registry as dr, entity_registry as er
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.Chargesplit.api import ChargesplitApi
from custom_components.Chargesplit.migration import (
    LEGACY_DOMAIN,
    NEW_DOMAIN,
    async_migrate_entry,
)

FIXTURE = Path(__file__).parent / "fixtures" / "wallbox_response.json"


@pytest.fixture(autouse=True)
def mock_api():
    """async_migrate_entry's call to async_add may trigger setup attempts
    on the legacy integration's fallback path during background tasks.
    Patch the API to feed the fixture instead of hitting the network."""
    data = FIXTURE.read_bytes()
    with patch.object(ChargesplitApi, "get_data", return_value=data):
        yield


V007_ENTITIES = [
    # (entity_id, unique_id, platform_domain, original_name)
    ("sensor.chargesplit_domus_voltage_l1", "Chargesplit-TESTSERIAL-Voltage L1-TESTSERIAL", "sensor", "Voltage L1"),
    ("sensor.chargesplit_domus_voltage_l2", "Chargesplit-TESTSERIAL-Voltage L2-TESTSERIAL", "sensor", "Voltage L2"),
    ("sensor.chargesplit_domus_voltage_l3", "Chargesplit-TESTSERIAL-Voltage L3-TESTSERIAL", "sensor", "Voltage L3"),
    ("sensor.chargesplit_domus_temperature", "Chargesplit-TESTSERIAL-Temperature-TESTSERIAL", "sensor", "Temperature"),
    ("sensor.chargesplit_domus_wallbox_status", "Chargesplit-TESTSERIAL-Wallbox Status-TESTSERIAL", "sensor", "Wallbox Status"),
    ("sensor.chargesplit_domus_wallbox_model", "Chargesplit-TESTSERIAL-Wallbox Model-TESTSERIAL", "sensor", "Wallbox Model"),
    ("sensor.chargesplit_domus_wallbox_firmware", "Chargesplit-TESTSERIAL-Wallbox firmware-TESTSERIAL", "sensor", "Wallbox firmware"),
    ("sensor.chargesplit_domus_wallbox_serial", "Chargesplit-TESTSERIAL-Wallbox serial-TESTSERIAL", "sensor", "Wallbox serial"),
    ("sensor.chargesplit_domus_charged_kwh", "Chargesplit-TESTSERIAL-Charged kWh-TESTSERIAL", "sensor", "Charged kWh"),
    ("sensor.chargesplit_domus_pilot_amps", "Chargesplit-TESTSERIAL-Pilot Amps-TESTSERIAL", "sensor", "Pilot Amps"),
    ("sensor.chargesplit_domus_actual_amps", "Chargesplit-TESTSERIAL-Actual Amps-TESTSERIAL", "sensor", "Actual Amps"),
    ("sensor.chargesplit_domus_actual_solar_power", "Chargesplit-TESTSERIAL-Actual solar power-TESTSERIAL", "sensor", "Actual solar power"),
    ("sensor.chargesplit_domus_actual_house_consumption", "Chargesplit-TESTSERIAL-Actual House Consumption-TESTSERIAL", "sensor", "Actual House Consumption"),
    ("sensor.chargesplit_domus_car_charging_power", "Chargesplit-TESTSERIAL-Car Charging Power-TESTSERIAL", "sensor", "Car Charging Power"),
    ("sensor.chargesplit_domus_daily_house_wh", "Chargesplit-TESTSERIAL-Daily House Wh-TESTSERIAL", "sensor", "Daily House Wh"),
    ("sensor.chargesplit_domus_daily_solar_wh", "Chargesplit-TESTSERIAL-Daily Solar Wh-TESTSERIAL", "sensor", "Daily Solar Wh"),
    ("sensor.chargesplit_domus_schedule", "Chargesplit-TESTSERIAL-Schedule-TESTSERIAL", "sensor", "Schedule"),
    ("select.chargesplit_domus_send_lock_unlock_command", "TESTSERIAL-lock_mode", "select", "Send Lock/unlock command"),
    ("select.chargesplit_domus_select_chargepoint_power_amps", "TESTSERIAL-operation_mode", "select", "Select Chargepoint Power AMPS"),
    ("select.chargesplit_domus_send_pause_restart_command", "TESTSERIAL-pause_mode", "select", "Send pause/restart command"),
]

EXPECTED_NEW_UNIQUE_IDS = {
    "Chargesplit-TESTSERIAL-Voltage L1-TESTSERIAL": "TESTSERIAL_voltage_l1",
    "Chargesplit-TESTSERIAL-Voltage L2-TESTSERIAL": "TESTSERIAL_voltage_l2",
    "Chargesplit-TESTSERIAL-Voltage L3-TESTSERIAL": "TESTSERIAL_voltage_l3",
    "Chargesplit-TESTSERIAL-Temperature-TESTSERIAL": "TESTSERIAL_temperature",
    "Chargesplit-TESTSERIAL-Wallbox Status-TESTSERIAL": "TESTSERIAL_status",
    "Chargesplit-TESTSERIAL-Wallbox Model-TESTSERIAL": "TESTSERIAL_model",
    "Chargesplit-TESTSERIAL-Wallbox firmware-TESTSERIAL": "TESTSERIAL_firmware",
    "Chargesplit-TESTSERIAL-Wallbox serial-TESTSERIAL": "TESTSERIAL_serial",
    "Chargesplit-TESTSERIAL-Charged kWh-TESTSERIAL": "TESTSERIAL_total_charged_kwh",
    "Chargesplit-TESTSERIAL-Pilot Amps-TESTSERIAL": "TESTSERIAL_pilot_amps",
    "Chargesplit-TESTSERIAL-Actual Amps-TESTSERIAL": "TESTSERIAL_actual_amps",
    "Chargesplit-TESTSERIAL-Actual solar power-TESTSERIAL": "TESTSERIAL_solar_power",
    "Chargesplit-TESTSERIAL-Actual House Consumption-TESTSERIAL": "TESTSERIAL_house_power",
    "Chargesplit-TESTSERIAL-Car Charging Power-TESTSERIAL": "TESTSERIAL_charging_power",
    "Chargesplit-TESTSERIAL-Daily House Wh-TESTSERIAL": "TESTSERIAL_daily_house_wh",
    "Chargesplit-TESTSERIAL-Daily Solar Wh-TESTSERIAL": "TESTSERIAL_daily_solar_wh",
    "Chargesplit-TESTSERIAL-Schedule-TESTSERIAL": "TESTSERIAL_schedule",
    "TESTSERIAL-lock_mode": "TESTSERIAL_lock_mode",
    "TESTSERIAL-operation_mode": "TESTSERIAL_operation_mode",
    "TESTSERIAL-pause_mode": "TESTSERIAL_pause_mode",
}


def _seed_legacy(hass):
    legacy_entry = MockConfigEntry(
        version=1,
        domain=LEGACY_DOMAIN,
        data={"serial": "TESTSERIAL", "code": "TESTSECRET"},
        title="TESTSERIAL",
    )
    legacy_entry.add_to_hass(hass)

    dev_reg = dr.async_get(hass)
    device = dev_reg.async_get_or_create(
        config_entry_id=legacy_entry.entry_id,
        identifiers={(LEGACY_DOMAIN, "TESTSERIAL")},
        manufacturer="Chargesplit Domus",
        model="WB132H",
        sw_version="2.34",
        name="Chargesplit Domus",
    )

    ent_reg = er.async_get(hass)
    seeded = {}
    for entity_id, unique_id, domain_part, original_name in V007_ENTITIES:
        suggested = entity_id.split(".", 1)[1]
        row = ent_reg.async_get_or_create(
            domain=domain_part,
            platform=LEGACY_DOMAIN,
            unique_id=unique_id,
            suggested_object_id=suggested,
            config_entry=legacy_entry,
            device_id=device.id,
            original_name=original_name,
        )
        assert row.entity_id == entity_id, (
            f"failed to seed {entity_id}; got {row.entity_id}"
        )
        seeded[unique_id] = row
    return legacy_entry, device, seeded


async def test_migration_rewrites_registry_and_creates_new_entry(hass):
    legacy_entry, device, seeded = _seed_legacy(hass)
    legacy_entry_id = legacy_entry.entry_id

    await async_migrate_entry(hass, legacy_entry)
    await hass.async_block_till_done()

    # Legacy entry was removed by the scheduled task.
    assert hass.config_entries.async_get_entry(legacy_entry_id) is None
    assert hass.config_entries.async_entries(LEGACY_DOMAIN) == []

    # A chargesplit-domain entry exists with the same credentials.
    new_entries = hass.config_entries.async_entries(NEW_DOMAIN)
    assert len(new_entries) == 1
    new_entry = new_entries[0]
    assert new_entry.data == {"serial": "TESTSERIAL", "code": "TESTSECRET"}
    assert new_entry.title == "TESTSERIAL"

    # Every seeded row was rewritten with the new platform + unique_id.
    # In production hass-chargesplit's platforms would adopt these via
    # async_get_or_create and set config_entry_id back to new_entry; here
    # they stay detached because the integration isn't on disk.
    ent_reg = er.async_get(hass)
    for old_unique_id, original_row in seeded.items():
        new_unique_id = EXPECTED_NEW_UNIQUE_IDS[old_unique_id]
        domain_part = original_row.entity_id.split(".", 1)[0]
        rewritten_id = ent_reg.async_get_entity_id(
            domain_part, NEW_DOMAIN, new_unique_id
        )
        assert rewritten_id is not None, (
            f"row for new unique_id {new_unique_id} not found in registry"
        )
        assert rewritten_id == original_row.entity_id, (
            f"entity_id changed from {original_row.entity_id} to {rewritten_id}"
        )

    # Device identifiers were rewritten.
    dev_reg = dr.async_get(hass)
    migrated_device = dev_reg.async_get(device.id)
    assert migrated_device is not None
    assert migrated_device.identifiers == {(NEW_DOMAIN, "TESTSERIAL")}

    # Notification was raised.
    notifications = persistent_notification._async_get_or_create_notifications(hass)
    notification_id = f"chargesplit_legacy_migration_{legacy_entry_id}"
    assert notification_id in notifications


async def test_migration_resumes_when_chargesplit_entry_already_exists(hass):
    """If a previous attempt created the chargesplit entry but crashed
    before scheduling legacy removal, the next pass reuses the existing
    entry rather than spawning a duplicate."""
    legacy_entry, _device, _seeded = _seed_legacy(hass)

    existing_new = MockConfigEntry(
        version=1,
        domain=NEW_DOMAIN,
        data={"serial": "TESTSERIAL", "code": "TESTSECRET"},
        title="TESTSERIAL",
    )
    existing_new.add_to_hass(hass)
    existing_id = existing_new.entry_id

    await async_migrate_entry(hass, legacy_entry)
    await hass.async_block_till_done()

    new_entries = hass.config_entries.async_entries(NEW_DOMAIN)
    assert len(new_entries) == 1
    assert new_entries[0].entry_id == existing_id


async def test_migration_detaches_unknown_unique_id_and_flags_it(hass):
    legacy_entry, _device, _seeded = _seed_legacy(hass)

    ent_reg = er.async_get(hass)
    weird = ent_reg.async_get_or_create(
        domain="sensor",
        platform=LEGACY_DOMAIN,
        unique_id="Chargesplit-TESTSERIAL-Cosmic Rays-TESTSERIAL",
        suggested_object_id="chargesplit_domus_cosmic_rays",
        config_entry=legacy_entry,
        original_name="Cosmic Rays",
    )
    weird_entity_id = weird.entity_id

    await async_migrate_entry(hass, legacy_entry)
    await hass.async_block_till_done()

    # Survivor is still in the registry but detached from any entry.
    survivor = ent_reg.async_get(weird_entity_id)
    assert survivor is not None
    assert survivor.config_entry_id is None
    assert survivor.platform == LEGACY_DOMAIN

    notifications = persistent_notification._async_get_or_create_notifications(hass)
    notification_id = f"chargesplit_legacy_migration_{legacy_entry.entry_id}"
    assert notification_id in notifications
    assert weird_entity_id in notifications[notification_id]["message"]


async def test_migration_skips_entry_with_no_serial(hass, caplog):
    """If somehow a legacy entry has no serial (corrupt data, manual edit),
    skip it with a warning rather than crash."""
    legacy_entry = MockConfigEntry(
        version=1,
        domain=LEGACY_DOMAIN,
        data={"code": "TESTSECRET"},  # no serial
        title="TESTSERIAL",
    )
    legacy_entry.add_to_hass(hass)

    await async_migrate_entry(hass, legacy_entry)

    # Entry still there, no chargesplit entry created.
    assert hass.config_entries.async_get_entry(legacy_entry.entry_id) is not None
    assert hass.config_entries.async_entries(NEW_DOMAIN) == []
    assert "no serial" in caplog.text
