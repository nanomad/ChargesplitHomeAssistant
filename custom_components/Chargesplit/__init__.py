"""v0.0.9 transition release.

The Chargesplit integration is moving to a new HACS repo with a
lowercase domain — github.com/nanomad/hass-chargesplit. This release
stays on the legacy `Chargesplit/` folder but its setup is rewired:
on each entry setup, we check if the new `chargesplit` integration is
on disk; if it is, we migrate the entry over (entity_ids preserved);
if it isn't, we fire a persistent notification telling the user to
install it, then fall through to the original v0.0.8 setup so their
wallbox keeps working in the meantime.

Once the user installs hass-chargesplit and HA restarts, the
chargesplit dependency check passes on the next setup and the
migration completes. After all legacy entries are migrated, this
integration has no entries to load and is effectively retired.
"""

import logging

from homeassistant import loader
from homeassistant.components import persistent_notification
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
import homeassistant.helpers.config_validation as cv

from .api import ChargesplitApi
from .const import (
    CONF_CODE,
    CHARGEPOINT_SERIAL,
    CONF_SYNC_INTERVAL,
    DEFAULT_SYNC_INTERVAL,
    DOMAIN,
)
from .coordinator import ChargesplitDataUpdateCoordinator
from .migration import NEW_DOMAIN, async_migrate_entry

PLATFORMS = [Platform.SENSOR, Platform.SELECT]

NEW_REPO_URL = "https://github.com/nanomad/hass-chargesplit"
_PROMPT_NOTIFICATION_ID = "chargesplit_migration_install_new_repo"

_LOGGER: logging.Logger = logging.getLogger(__package__)

CONFIG_SCHEMA = cv.config_entry_only_config_schema(DOMAIN)


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry):
    """Migrate to chargesplit if available; otherwise legacy-setup and notify."""
    if await _chargesplit_integration_available(hass):
        await async_migrate_entry(hass, entry)
        # Migration created a chargesplit entry, rehomed registry rows under
        # it, and scheduled removal of this legacy entry. Return True so HA
        # treats this entry as loaded for the brief window before the
        # scheduled async_remove fires.
        return True

    persistent_notification.async_create(
        hass,
        (
            "The Chargesplit integration has moved to a new HACS repository:\n\n"
            f"{NEW_REPO_URL}\n\n"
            "Install it from HACS (Settings → HACS → Integrations → "
            "⋮ → Custom repositories) to migrate your data automatically. "
            "Dashboards, automations, and statistics history will be "
            "preserved. Your wallbox will keep working in the meantime."
        ),
        title="Chargesplit: install the new integration",
        notification_id=_PROMPT_NOTIFICATION_ID,
    )
    return await _legacy_setup_entry(hass, entry)


async def _chargesplit_integration_available(hass: HomeAssistant) -> bool:
    """True iff `custom_components/chargesplit/` is on disk and discoverable."""
    try:
        await loader.async_get_integration(hass, NEW_DOMAIN)
    except loader.IntegrationNotFound:
        return False
    return True


async def _legacy_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Original v0.0.8 setup. Runs only when chargesplit isn't installed yet."""
    hass.data.setdefault(DOMAIN, {})

    code = entry.data["code"]
    serial = entry.data["serial"]
    api = ChargesplitApi(code, serial)
    sync_interval = entry.options.get(CONF_SYNC_INTERVAL, DEFAULT_SYNC_INTERVAL)
    _LOGGER.debug("Setting up Chargesplit for serial: %s", serial)

    coordinator = ChargesplitDataUpdateCoordinator(
        hass, api=api, update_interval=sync_interval, config_entry=entry
    )
    await coordinator.async_config_entry_first_refresh()

    hass.data[DOMAIN][entry.entry_id] = coordinator
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    entry.async_on_unload(entry.add_update_listener(async_reload_entry))
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry):
    """Handle removal of an entry."""
    # If this entry was migrated, it'll be removed shortly and platforms
    # were never forwarded — nothing to unload.
    if DOMAIN not in hass.data or entry.entry_id not in hass.data[DOMAIN]:
        return True
    unloaded = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unloaded:
        _LOGGER.debug("Chargesplit unloaded successfully")
        hass.data[DOMAIN].pop(entry.entry_id, None)
    return unloaded


async def async_reload_entry(hass: HomeAssistant, entry: ConfigEntry) -> None:
    await hass.config_entries.async_reload(entry.entry_id)
