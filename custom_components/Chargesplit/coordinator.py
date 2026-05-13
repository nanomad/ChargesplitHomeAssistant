import json
import logging
from datetime import timedelta

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .api import ChargesplitApi
from .const import DOMAIN

_LOGGER: logging.Logger = logging.getLogger(__package__)

# Wallbox API returns power/current/energy fields as JSON strings in some
# states (e.g. CHARGINGPWR "0.00" at rest, AMP "13.5" while charging). Without
# coercion HA's recorder warns every cycle and Energy dashboard math depends on
# its float() coercion succeeding for every reading. Cast at the data-layer
# boundary so all consumers see uniformly typed values.


def _to_int(value):
    # Goes through float() so stringified floats like "25.0" don't raise.
    return int(float(value))


# Logged in the coerce warning; "int" reads better than the helper name.
_to_int.__name__ = "int"


_NUMERIC_KEYS = {
    "AMP": float,
    "VOLT1": float,
    "VOLT2": float,
    "VOLT3": float,
    "TEMP": float,
    "CHARGINGPWR": float,
    "HOUSEPWR": float,
    "SOLARPWR": float,
    "TOTALCHARGED": float,
    "DAYHOUSE": float,
    "DAYSOLAR": float,
    "PILOTLIMIT": _to_int,
}


def _coerce_numeric(data: dict) -> dict:
    coerced = dict(data)
    for key, caster in _NUMERIC_KEYS.items():
        value = coerced.get(key)
        if value is None:
            continue
        try:
            coerced[key] = caster(value)
        except (TypeError, ValueError):
            _LOGGER.warning(
                "Could not coerce %s=%r to %s, leaving as-is",
                key, value, caster.__name__,
            )
    return coerced


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
            return _coerce_numeric(json.loads(raw))
        except Exception as exception:
            raise UpdateFailed() from exception
