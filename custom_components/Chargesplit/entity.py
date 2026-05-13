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
        data = self.coordinator.data or {}
        return {
            "identifiers": {(DOMAIN, self.coordinator.api.host)},
            "name": NAME,
            "manufacturer": NAME,
            "model": data.get("MODEL"),
            "sw_version": str(data["FWVERS"]) if "FWVERS" in data else None,
        }

    @property
    def available(self) -> bool:
        return self.coordinator.data is not None

    @property
    def should_poll(self) -> bool:
        return False
