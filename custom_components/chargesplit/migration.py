"""One-shot migration from the legacy capitalized `Chargesplit` domain.

v0.0.x shipped under DOMAIN="Chargesplit" because the brands proxy at
brands.home-assistant.io was case-insensitive at the time. It later started
requiring all-lowercase domains, so v0.1.0 renamed to `chargesplit`. Existing
installs end up with orphaned entries: the old config entry, all entity
registry rows (platform="Chargesplit", verbose unique_ids), and the device
row (identifiers={("Chargesplit", serial)}) are pointed at an integration
that no longer exists on disk.

This module rewrites that state in-place so entity_ids stay stable —
preserving long-term-statistics history (keyed by entity_id), dashboards,
and automations.

The migration runs from `async_setup` on the new `chargesplit` domain. For
that to fire at all when only orphaned `Chargesplit` entries exist, the
sibling `custom_components/Chargesplit/` shim manifest declares
`dependencies: ["chargesplit"]` — HA loads the shim because the orphaned
entry references it, and the dependency forces `chargesplit.async_setup` to
run first.
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


_REENTRY_GUARD_KEY = "_chargesplit_migration_in_progress"


async def async_migrate_legacy_domain(hass: HomeAssistant) -> None:
    """Rewrite orphaned `Chargesplit` config + registry rows to `chargesplit`.

    Idempotent: safe to call repeatedly. If interrupted mid-way and re-run,
    it picks up the partially-migrated state (new chargesplit entry already
    exists for the serial) instead of duplicating.

    Sequencing rationale (all public API):

    1. Rewrite legacy entity rows: change `platform` to `chargesplit` and
       `unique_id` to the v0.1.0 shape, but leave `config_entry_id` pointing
       at the legacy entry. The new entry doesn't exist yet, and that's
       fine — `async_update_entity_platform` accepts a same-value
       `new_config_entry_id` (it's just gating against accidental orphaning
       when the entity is already linked).
    2. Rewrite the device's identifier tuple. Leave config-entry membership
       alone.
    3. `async_add` the new entry. Its platform setup calls
       `async_get_or_create(domain, "chargesplit", new_unique_id)` and
       `async_get_or_create(... identifiers=...)`, which match the rows
       we pre-migrated in steps 1-2 and re-link them to the new entry as
       a side effect of `_async_update_entity` / `_async_update_device`.
    4. Remove the legacy entry. The new entry is already in the device's
       config_entries set; HA cascade-clears the legacy id during removal.

    Re-entry guard: `async_add` in step 3 awaits the new entry's setup. If
    `chargesplit` hasn't been loaded yet (the typical bootstrap order has
    HA load us first via the legacy-domain shim's `dependencies`, but tests
    and edge cases can invert this), HA loads it inline, which calls
    `chargesplit.async_setup` again, which calls *this* function again.
    The inner call would complete the migration first; the outer call would
    then trip over an already-removed legacy entry. The hass.data flag
    below short-circuits the inner call instead.
    """
    if hass.data.get(_REENTRY_GUARD_KEY):
        return

    legacy_entries = list(hass.config_entries.async_entries(LEGACY_DOMAIN))
    if not legacy_entries:
        return

    hass.data[_REENTRY_GUARD_KEY] = True
    try:
        await _do_migrate(hass, legacy_entries)
    finally:
        hass.data.pop(_REENTRY_GUARD_KEY, None)


async def _do_migrate(
    hass: HomeAssistant, legacy_entries: list[ConfigEntry]
) -> None:

    ent_reg = er.async_get(hass)
    dev_reg = dr.async_get(hass)
    migrated_count = 0
    unrecognized: list[str] = []

    for legacy_entry in legacy_entries:
        serial = legacy_entry.data.get("serial")
        if not serial:
            _LOGGER.warning(
                "Legacy Chargesplit entry %s has no serial in data; skipping",
                legacy_entry.entry_id,
            )
            continue

        # Step 1: rewrite entity rows. Keep them pointed at the legacy entry
        # for now; the new entry's platform setup will adopt them via
        # `async_get_or_create` once it runs in step 3.
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

        # Step 2: rewrite device identifiers in place.
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

        # Detach unrecognized rows before removing the legacy entry so they
        # aren't cascade-deleted. The notification at the bottom flags them
        # for manual cleanup.
        for legacy_row in er.async_entries_for_config_entry(
            ent_reg, legacy_entry.entry_id
        ):
            ent_reg.async_update_entity(
                legacy_row.entity_id, config_entry_id=None
            )

        # Step 3: stand up the new entry. If a prior run got partway through
        # and crashed, an entry for this serial already exists — reuse it
        # instead of creating a duplicate.
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
        # Platform setup during async_add called async_get_or_create for
        # each entity and device. Those calls matched the pre-migrated rows
        # by (platform, unique_id) and identifiers respectively, and updated
        # their config_entry_id / config_entries to point at new_entry.

        # Step 4: remove the legacy entry. The device now has both entries
        # in its config_entries set; HA will clean the legacy one out as
        # part of the cascade.
        await hass.config_entries.async_remove(legacy_entry.entry_id)

        migrated_count += 1

    if migrated_count:
        message = (
            f"Migrated {migrated_count} Chargesplit config "
            f"entr{'y' if migrated_count == 1 else 'ies'} from the legacy "
            "`Chargesplit` domain to `chargesplit`. Entity IDs were preserved, "
            "so dashboards, automations, and statistics history continue to work."
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
            notification_id="chargesplit_legacy_migration",
        )


def _find_existing_chargesplit_entry(
    hass: HomeAssistant, serial: str
) -> ConfigEntry | None:
    for entry in hass.config_entries.async_entries(DOMAIN):
        if entry.data.get("serial") == serial:
            return entry
    return None
