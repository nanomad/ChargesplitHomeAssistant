"""One-shot migration from the legacy capitalized `Chargesplit` domain.

v0.0.x shipped under DOMAIN="Chargesplit" because the brands proxy at
brands.home-assistant.io was case-insensitive at the time. It later started
requiring all-lowercase domains, so v0.1.0 renamed to `chargesplit`. Existing
installs end up with orphaned entries: the old config entry, all entity
registry rows (platform="Chargesplit", verbose unique_ids), and the device
row (identifiers={("Chargesplit", serial)}) all point at an integration that
no longer exists on disk.

This module rewrites that state in-place so entity_ids stay stable —
preserving long-term-statistics history (keyed by entity_id), dashboards,
and automations.

Trigger. The sibling `custom_components/Chargesplit/` shim declares
`dependencies: ["chargesplit"]`. HA loads the shim because legacy entries
reference it, and the dependency makes it load `chargesplit` first. The
shim's `async_setup_entry` then calls `async_migrate_entry` for each
legacy entry; that function is the only entry point in this module.
"""

from __future__ import annotations

import logging
from types import MappingProxyType
from typing import Final

from homeassistant.components import persistent_notification
from homeassistant.config_entries import ConfigEntry, SOURCE_IMPORT
from homeassistant.core import HomeAssistant
from homeassistant.helpers import device_registry as dr, entity_registry as er

from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)

LEGACY_DOMAIN: Final = "Chargesplit"

# Description text in the old (v0.0.x) sensor unique_id `Chargesplit-{serial}-{description}-{serial}`
# → suffix used in the v0.1.0 unique_id `{serial}_{suffix}`.
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

# v0.0.x select unique_ids are `{serial}-{key}` for these keys.
_SELECT_KEYS: Final = ("operation_mode", "lock_mode", "pause_mode")


def migrate_unique_id(old: str, serial: str) -> str | None:
    """Translate a v0.0.x unique_id to the v0.1.0 shape, or None if unrecognized.

    Anchored on the known serial so that serials containing dashes parse safely.
    """
    if old.startswith(f"{LEGACY_DOMAIN}-{serial}-") and old.endswith(f"-{serial}"):
        # Sensor: Chargesplit-{serial}-{description}-{serial}
        description = old[len(f"{LEGACY_DOMAIN}-{serial}-") : -len(f"-{serial}")]
        suffix = _SENSOR_DESCRIPTION_TO_SUFFIX.get(description)
        if suffix is None:
            return None
        return f"{serial}_{suffix}"

    for key in _SELECT_KEYS:
        if old == f"{serial}-{key}":
            return f"{serial}_{key}"

    return None


async def async_migrate_entry(hass: HomeAssistant, legacy_entry: ConfigEntry) -> None:
    """Migrate one orphaned `Chargesplit` config entry to `chargesplit`.

    Sequencing (all public API):

    1. Rewrite the legacy entity rows in place: new `platform=chargesplit`
       and new `unique_id`, but `new_config_entry_id=legacy_entry.entry_id`
       (the gating value, not a real change — `async_update_entity_platform`
       refuses UNDEFINED when a row is already linked).
    2. Rewrite the device's identifier tuple, leaving config-entry
       membership alone.
    3. `async_add` the new entry. Its platform setup calls
       `async_get_or_create(... platform, unique_id)` and
       `async_get_or_create(... identifiers=...)`, which match the
       pre-migrated rows and adopt them — `_async_update_entity` /
       `_async_update_device` set `config_entry_id` to the new entry as
       a side effect.
    4. Schedule the legacy entry's removal as a follow-up task. We can't
       `await async_remove(legacy_entry.entry_id)` synchronously: this
       function runs inside the shim's `async_setup_entry`, which holds
       the legacy entry's setup_lock; `async_remove` would try to acquire
       the same lock and deadlock. `hass.async_create_task` defers it
       past the current setup, where the lock is no longer held.

    Idempotent: if a previous attempt crashed after step 3 but before
    step 4, the next pass re-runs steps 1-2 as no-ops on the already-
    migrated rows, finds the existing chargesplit entry in step 3 and
    reuses it, and re-schedules removal in step 4.
    """
    serial = legacy_entry.data.get("serial")
    if not serial:
        _LOGGER.warning(
            "Legacy Chargesplit entry %s has no serial in data; skipping",
            legacy_entry.entry_id,
        )
        return

    ent_reg = er.async_get(hass)
    dev_reg = dr.async_get(hass)
    unrecognized: list[str] = []

    # Step 1: rewrite entity rows in place.
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
            DOMAIN,
            new_config_entry_id=legacy_entry.entry_id,
            new_unique_id=new_unique_id,
        )

    # Step 2: rewrite device identifiers.
    for legacy_device in dr.async_entries_for_config_entry(
        dev_reg, legacy_entry.entry_id
    ):
        new_identifiers = {
            (DOMAIN if ident_domain == LEGACY_DOMAIN else ident_domain, ident_value)
            for (ident_domain, ident_value) in legacy_device.identifiers
        }
        dev_reg.async_update_device(
            legacy_device.id, new_identifiers=new_identifiers
        )

    # Detach unrecognized rows so the upcoming legacy-entry removal doesn't
    # cascade-delete them. The notification below flags them for the user.
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
            domain=DOMAIN,
            title=legacy_entry.title,
            data=dict(legacy_entry.data),
            options=dict(legacy_entry.options),
            source=SOURCE_IMPORT,
            unique_id=legacy_entry.unique_id,
            discovery_keys=MappingProxyType({}),
            subentries_data=None,
        )
        await hass.config_entries.async_add(new_entry)

    # Step 4: schedule legacy removal after our caller's setup_lock releases.
    hass.async_create_task(
        hass.config_entries.async_remove(legacy_entry.entry_id),
        f"chargesplit-migration-remove-{legacy_entry.entry_id}",
    )

    message = (
        "Migrated one Chargesplit config entry from the legacy `Chargesplit` "
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
    for entry in hass.config_entries.async_entries(DOMAIN):
        if entry.data.get("serial") == serial:
            return entry
    return None
