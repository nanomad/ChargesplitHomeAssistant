import json
import logging
from datetime import timedelta

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .api import ChargesplitApi
from .const import DOMAIN

_LOGGER: logging.Logger = logging.getLogger(__package__)


class ChargesplitDataUpdateCoordinator(DataUpdateCoordinator):
    def __init__(
        self,
        hass: HomeAssistant,
        api: ChargesplitApi,
        update_interval: int,
        config_entry: ConfigEntry,
    ) -> None:
        self.api = api
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=timedelta(seconds=update_interval),
            config_entry=config_entry,
        )

    async def _async_update_data(self) -> dict:
        try:
            raw = await self.hass.async_add_executor_job(self.api.get_data)
            return json.loads(raw)
        except Exception as exception:
            raise UpdateFailed() from exception
