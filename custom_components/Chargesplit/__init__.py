"""Legacy `Chargesplit` (capitalized) domain shim.

v0.0.x used DOMAIN="Chargesplit". v0.1.0 renamed to lowercase. Existing
installs have orphaned config entries under the old capitalized domain;
this shim exists only so HA can resolve those entries to *something* on
disk, which in turn forces `chargesplit` (our real integration, declared
as a dependency in this shim's manifest) to load. `chargesplit.async_setup`
then runs the migration that rehomes the entry under the lowercase domain.

Once an install has been migrated, no `Chargesplit` config entries remain
and this shim is never loaded again. It can be deleted from the release
once we're confident nobody is upgrading from <0.1.0.
"""

from __future__ import annotations

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant


async def async_setup(hass: HomeAssistant, config: dict) -> bool:
    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    # An entry only reaches us if migration didn't remove it during
    # `chargesplit.async_setup`. The most likely cause is an unrecognized
    # entity unique_id; the migration logs and notifies in that case.
    # We return True so HA marks the entry LOADED rather than erroring —
    # without this the entry stays in setup_error and confuses the UI.
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    return True
