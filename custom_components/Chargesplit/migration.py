"""One-shot migration to the new `chargesplit` integration in hass-chargesplit.

v0.0.x shipped under DOMAIN="Chargesplit" (mixed case). HA's brands proxy at
brands.home-assistant.io only accepts lowercase domains, so the v0.1.0
release renamed to `"chargesplit"` and moved to a new HACS repo
(github.com/nanomad/hass-chargesplit) — installing v0.1.0 as a sibling
release in this same repo isn't an option because HACS only ships one
folder under `custom_components/` per integration.

This migration takes a legacy config entry from THIS integration and:
1. Rewrites every entity registry row attached to it: new `platform`
   = "chargesplit", new `unique_id` in the v0.1.0 shape (`{serial}_{key}`).
2. Rewrites the device registry row's identifier tuple from
   ("Chargesplit", serial) to ("chargesplit", serial).
3. Creates a new `chargesplit`-domain config entry with the same
   credentials. Because hass-chargesplit's `chargesplit` integration is
   on disk (the caller verified this), HA sets up the new entry
   synchronously, its platforms call `async_get_or_create`, and they
   adopt the pre-migrated rows by `(platform, unique_id)` match. Net:
   entity_ids preserved, statistics history preserved.
4. Schedules removal of the legacy entry as a follow-up task —
   `async_remove` from inside a config entry's own setup_entry would
   deadlock on setup_lock; `async_create_task` defers it past that.

The caller (this integration's `async_setup_entry`) is responsible for
checking that `chargesplit` is on disk before invoking this function.
If it's not, the migration's `async_add(new_entry)` would still succeed
but the new entry would land in `not_loaded` state, and rows would be
left half-migrated. Better to fail the check upstream.
"""

from __future__ import annotations

import logging
from types import MappingProxyType
from typing import Final

from homeassistant.components import persistent_notification
from homeassistant.config_entries import ConfigEntry, SOURCE_IMPORT
from homeassistant.core import HomeAssistant
from homeassistant.helpers import device_registry as dr, entity_registry as er

LEGACY_DOMAIN: Final = "Chargesplit"
NEW_DOMAIN: Final = "chargesplit"

_LOGGER = logging.getLogger(__name__)

# Description text in the legacy sensor unique_id
# `Chargesplit-{serial}-{description}-{serial}` → suffix used in the new
# unique_id `{serial}_{suffix}`. Derived from v0.0.7's
# `custom_components/Chargesplit/sensor.py` INSTRUMENTS list.
_SENSOR_DESCRIPTION_TO_SUFFIX: Final[dict[str, str]] = {
    "Voltage L1": "voltage_l1",
    "Voltage L2": "voltage_l2",
    "Voltage L3": "voltage_l3",
    "Temperature": "temperature",
    "Wallbox Status": "status",
    "Wallbox Model": "model",
    "Wallbox firmware": "firmware",
    "Wallbox serial": "serial",
    "Charged kWh": "total_charged_kwh",
    "Pilot Amps": "pilot_amps",
    "Actual Amps": "actual_amps",
    "Actual solar power": "solar_power",
    "Actual House Consumption": "house_power",
    "Car Charging Power": "charging_power",
    "Daily House Wh": "daily_house_wh",
    "Daily Solar Wh": "daily_solar_wh",
    "Schedule": "schedule",
}

# Legacy select unique_ids are `{serial}-{key}` for these keys.
_SELECT_KEYS: Final = ("operation_mode", "lock_mode", "pause_mode")


def migrate_unique_id(old: str, serial: str) -> str | None:
    """Translate a legacy unique_id to the v0.1.0 shape, or None if unrecognized.

    Anchored on the known serial so that hyphenated serials parse safely.
    """
    if old.startswith(f"{LEGACY_DOMAIN}-{serial}-") and old.endswith(f"-{serial}"):
        description = old[len(f"{LEGACY_DOMAIN}-{serial}-") : -len(f"-{serial}")]
        suffix = _SENSOR_DESCRIPTION_TO_SUFFIX.get(description)
        if suffix is None:
            return None
        return f"{serial}_{suffix}"

    for key in _SELECT_KEYS:
        if old == f"{serial}-{key}":
            return f"{serial}_{key}"

    return None


async def async_migrate_entry(
    hass: HomeAssistant, legacy_entry: ConfigEntry
) -> None:
    """Migrate one legacy config entry over to the chargesplit integration.

    Caller has already verified the chargesplit integration is on disk.
    """
    serial = legacy_entry.data.get("serial")
    if not serial:
        _LOGGER.warning(
            "Legacy Chargesplit entry %s has no serial; skipping migration",
            legacy_entry.entry_id,
        )
        return

    ent_reg = er.async_get(hass)
    dev_reg = dr.async_get(hass)
    unrecognized: list[str] = []

    # Step 1: rewrite entity rows in place. Keep them pointed at the legacy
    # entry — the new entry's platform setup will adopt them via
    # async_get_or_create matching on (platform, unique_id) once it runs
    # in step 3.
    for legacy_row in er.async_entries_for_config_entry(
        ent_reg, legacy_entry.entry_id
    ):
        new_unique_id = migrate_unique_id(legacy_row.unique_id, serial)
        if new_unique_id is None:
            _LOGGER.warning(
                "Could not migrate entity %s (unique_id=%s); leaving under legacy domain",
                legacy_row.entity_id,
                legacy_row.unique_id,
            )
            unrecognized.append(legacy_row.entity_id)
            continue
        ent_reg.async_update_entity_platform(
            legacy_row.entity_id,
            NEW_DOMAIN,
            new_config_entry_id=legacy_entry.entry_id,
            new_unique_id=new_unique_id,
        )

    # Step 2: rewrite device identifiers.
    for legacy_device in dr.async_entries_for_config_entry(
        dev_reg, legacy_entry.entry_id
    ):
        new_identifiers = {
            (NEW_DOMAIN if d == LEGACY_DOMAIN else d, v)
            for (d, v) in legacy_device.identifiers
        }
        dev_reg.async_update_device(
            legacy_device.id, new_identifiers=new_identifiers
        )

    # Detach unrecognized rows before legacy-entry removal so they aren't
    # cascade-deleted. The notification below flags them for manual cleanup.
    for legacy_row in er.async_entries_for_config_entry(
        ent_reg, legacy_entry.entry_id
    ):
        ent_reg.async_update_entity(legacy_row.entity_id, config_entry_id=None)

    # Step 3: create (or adopt, on retry) the chargesplit entry.
    new_entry = _find_existing_chargesplit_entry(hass, serial)
    if new_entry is None:
        new_entry = ConfigEntry(
            version=legacy_entry.version,
            minor_version=legacy_entry.minor_version,
            domain=NEW_DOMAIN,
            title=legacy_entry.title,
            data=dict(legacy_entry.data),
            options=dict(legacy_entry.options),
            source=SOURCE_IMPORT,
            unique_id=legacy_entry.unique_id,
            discovery_keys=MappingProxyType({}),
            subentries_data=None,
        )
        await hass.config_entries.async_add(new_entry)

    # Step 3.5: attach the device to the new entry explicitly. The new
    # entry's platforms would normally do this via `device_info` during
    # their own setup, but if that setup fails or hasn't run yet, the
    # legacy-entry removal below would cascade-delete the device. Adding
    # the new entry to the device's config_entries here guarantees the
    # device survives the removal.
    for legacy_device in dr.async_entries_for_config_entry(
        dev_reg, legacy_entry.entry_id
    ):
        dev_reg.async_update_device(
            legacy_device.id, add_config_entry_id=new_entry.entry_id
        )

    # Step 4: schedule legacy entry removal once we're out of setup_lock.
    hass.async_create_task(
        hass.config_entries.async_remove(legacy_entry.entry_id),
        f"chargesplit-migration-remove-{legacy_entry.entry_id}",
    )

    message = (
        "Migrated a Chargesplit config entry from the legacy `Chargesplit` "
        "domain to `chargesplit`. Entity IDs were preserved, so dashboards, "
        "automations, and statistics history continue to work."
    )
    if unrecognized:
        message += (
            "\n\nThese entities had an unrecognized unique_id format and "
            "were left untouched — you may need to delete them manually:\n"
            + "\n".join(f"- {eid}" for eid in unrecognized)
        )
    persistent_notification.async_create(
        hass,
        message,
        title="Chargesplit migration",
        notification_id=f"chargesplit_legacy_migration_{legacy_entry.entry_id}",
    )


def _find_existing_chargesplit_entry(
    hass: HomeAssistant, serial: str
) -> ConfigEntry | None:
    for entry in hass.config_entries.async_entries(NEW_DOMAIN):
        if entry.data.get("serial") == serial:
            return entry
    return None
