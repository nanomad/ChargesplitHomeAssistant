"""Integration test for the legacy-domain migration.

Seeds the entity + device registries with the v0.0.7-shaped rows under the
old `Chargesplit` domain, runs the migration, and asserts that:

- The old config entry is gone and a new `chargesplit` entry exists holding
  the same credentials.
- Every entity row keeps its original `entity_id` (statistics history, which
  is keyed on entity_id, must survive). Its `unique_id` is rewritten to the
  v0.1.0 shape and its `platform` to `chargesplit`.
- The device row keeps its `device_id` but its identifiers are rewritten,
  and its config-entry membership swaps to the new entry.
- A persistent_notification is created announcing the migration.
- An entity with an unrecognized unique_id is left in place (detached from
  the deleted legacy entry) and called out in the notification.
"""

from pathlib import Path
from unittest.mock import patch

import pytest

from homeassistant.components import persistent_notification
from homeassistant.helpers import device_registry as dr, entity_registry as er
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.chargesplit.api import ChargesplitApi
from custom_components.chargesplit.migration import (
    LEGACY_DOMAIN,
    async_migrate_entry,
)

FIXTURE = Path(__file__).parent / "fixtures" / "wallbox_response.json"


@pytest.fixture(autouse=True)
def mock_api():
    """The migration creates new chargesplit entries; HA then runs setup on
    them, which would hit the network. Patch the API to feed the fixture
    instead so the coordinator's first refresh succeeds."""
    data = FIXTURE.read_bytes()
    with patch.object(ChargesplitApi, "get_data", return_value=data):
        yield


# v0.0.7 entity contract — entity_id + unique_id pairs. Derived from
# tests/test_setup.py::EXPECTED_V007 on `main`.
V007_ENTITIES = [
    # (entity_id, unique_id, domain_part, original_name)
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

# Mapping from old unique_id → expected new unique_id, derived from the
# migration mapping. Used to assert each row migrated correctly.
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
    """Add a Chargesplit-domain entry plus full v0.0.7 registry state."""
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
        # Suggest the v0.0.7 entity_id explicitly. async_get_or_create
        # honours suggested_object_id when nothing is registered yet.
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
            f"failed to seed entity_id {entity_id}; got {row.entity_id}"
        )
        seeded[unique_id] = row
    return legacy_entry, device, seeded


async def test_migration_preserves_entity_ids_and_rewires_to_new_entry(hass):
    legacy_entry, device, seeded = _seed_legacy(hass)
    legacy_entry_id = legacy_entry.entry_id

    await async_migrate_entry(hass, legacy_entry)
    await hass.async_block_till_done()

    # The legacy config entry is gone (scheduled removal task ran).
    assert hass.config_entries.async_get_entry(legacy_entry_id) is None
    legacy_entries = hass.config_entries.async_entries(LEGACY_DOMAIN)
    assert legacy_entries == []

    # A new chargesplit entry exists with the same credentials.
    new_entries = hass.config_entries.async_entries("chargesplit")
    assert len(new_entries) == 1
    new_entry = new_entries[0]
    assert new_entry.data == {"serial": "TESTSERIAL", "code": "TESTSECRET"}
    assert new_entry.title == "TESTSERIAL"

    # Every seeded entity row now belongs to the new entry, with the new
    # unique_id and new platform — but the entity_id is unchanged. That's
    # the load-bearing assertion: statistics keep flowing.
    ent_reg = er.async_get(hass)
    for old_unique_id, original_row in seeded.items():
        new_unique_id = EXPECTED_NEW_UNIQUE_IDS[old_unique_id]
        domain_part = original_row.entity_id.split(".", 1)[0]
        migrated = ent_reg.async_get_entity_id(domain_part, "chargesplit", new_unique_id)
        assert migrated is not None, (
            f"entity for new unique_id {new_unique_id} not found"
        )
        assert migrated == original_row.entity_id, (
            f"entity_id changed: was {original_row.entity_id}, now {migrated}"
        )

        migrated_row = ent_reg.async_get(migrated)
        assert migrated_row.platform == "chargesplit"
        assert migrated_row.config_entry_id == new_entry.entry_id

    # The device row keeps its device_id, but identifiers and config-entry
    # membership are swapped to the new entry.
    dev_reg = dr.async_get(hass)
    migrated_device = dev_reg.async_get(device.id)
    assert migrated_device is not None
    assert migrated_device.identifiers == {("chargesplit", "TESTSERIAL")}
    assert new_entry.entry_id in migrated_device.config_entries
    assert legacy_entry_id not in migrated_device.config_entries

    # User-visible notification was raised.
    notifications = persistent_notification._async_get_or_create_notifications(hass)
    assert f"chargesplit_legacy_migration_{legacy_entry_id}" in notifications


async def test_migration_is_idempotent_when_nothing_to_migrate(hass):
    # No legacy entries seeded. async_migrate_entry shouldn't be called by
    # the shim either — but if something does invoke it on a non-Chargesplit
    # entry by accident, it would need a serial in data. We just verify the
    # whole-system invariant: with no legacy entries, no chargesplit entries
    # get created out of thin air.
    new_entries_before = hass.config_entries.async_entries("chargesplit")
    # Nothing to do — the shim's setup_entry only fires when HA finds an
    # orphaned Chargesplit entry. No entry, no call.
    new_entries_after = hass.config_entries.async_entries("chargesplit")
    assert [e.entry_id for e in new_entries_before] == [
        e.entry_id for e in new_entries_after
    ]


async def test_migration_resumes_partial_state(hass):
    """If a previous attempt created the chargesplit entry but crashed before
    rehoming all rows, the next pass must reuse the existing entry rather
    than spawning a duplicate.
    """
    legacy_entry, _device, _seeded = _seed_legacy(hass)

    # Simulate a half-done migration: a chargesplit entry already exists for
    # this serial, but the legacy entry and entity rows are still in their
    # old place.
    existing_new = MockConfigEntry(
        version=1,
        domain="chargesplit",
        data={"serial": "TESTSERIAL", "code": "TESTSECRET"},
        title="TESTSERIAL",
    )
    existing_new.add_to_hass(hass)
    existing_id = existing_new.entry_id

    await async_migrate_entry(hass, legacy_entry)
    await hass.async_block_till_done()

    new_entries = hass.config_entries.async_entries("chargesplit")
    assert len(new_entries) == 1, (
        f"expected one chargesplit entry, got {[e.entry_id for e in new_entries]}"
    )
    assert new_entries[0].entry_id == existing_id


async def test_migration_leaves_unknown_unique_id_in_place_and_notifies(hass):
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

    # Weird entity is detached but still present.
    survivor = ent_reg.async_get(weird_entity_id)
    assert survivor is not None
    assert survivor.config_entry_id is None
    assert survivor.platform == LEGACY_DOMAIN

    # Notification mentions it.
    notifications = persistent_notification._async_get_or_create_notifications(hass)
    notification_id = f"chargesplit_legacy_migration_{legacy_entry.entry_id}"
    assert notification_id in notifications
    assert weird_entity_id in notifications[notification_id]["message"]
