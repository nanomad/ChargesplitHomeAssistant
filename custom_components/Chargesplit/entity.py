import json
import logging

from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN, NAME
from .coordinator import ChargesplitDataUpdateCoordinator

_LOGGER: logging.Logger = logging.getLogger(__package__)


class ChargesplitEntity(CoordinatorEntity):
    def __init__(self, coordinator: ChargesplitDataUpdateCoordinator, entry):
        super().__init__(coordinator)
        self.entry = entry

    @property
    def device_info(self):
        data = json.loads(self.coordinator.data) if self.coordinator.data else {}
        return {
            "identifiers": {(DOMAIN, self.coordinator.api.host)},
            "name": NAME,
            "manufacturer": NAME,
            "model": data.get("MODEL"),
            "sw_version": str(data.get("FWVERS")) if data.get("FWVERS") is not None else None,
        }

    @property
    def available(self) -> bool:
        return not not self.coordinator.data

    @property
    def should_poll(self) -> bool:
        return False
