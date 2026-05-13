"""Legacy `Chargesplit` (capitalized) domain shim.

v0.0.x used DOMAIN="Chargesplit". v0.1.0 renamed to lowercase. Existing
installs have orphaned config entries under the old capitalized domain;
this shim exists so HA can resolve those entries on disk, and so each
one triggers the per-entry migration in `chargesplit.migration`.

The folder name `chargesplit_legacy_shim` is decoupled from the domain
("Chargesplit") declared in `manifest.json` — HA looks up integrations
by manifest domain, not folder name. The folder is named this way so
that HACS, which scans `custom_components/*/` alphabetically and treats
the first hit as "the" integration, picks `chargesplit/` (and its brand
assets) rather than this shim.

Once an install has been migrated, no `Chargesplit` config entries
remain and this shim is never loaded again. It can be deleted from
the release once we're confident nobody is upgrading from <0.1.0.
"""

from __future__ import annotations

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from custom_components.chargesplit.migration import async_migrate_entry


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    await async_migrate_entry(hass, entry)
    # `async_migrate_entry` has scheduled `async_remove(entry.entry_id)` as
    # a follow-up task — we can't await it here because we hold this
    # entry's setup_lock. Return True so HA marks the entry LOADED for
    # the brief window before that task fires.
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    return True
