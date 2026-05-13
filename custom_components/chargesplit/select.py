import logging
import requests
from homeassistant.components.select import SelectEntity, SelectEntityDescription
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.entity import DeviceInfo, EntityCategory
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from .const import DOMAIN
from .coordinator import ChargesplitDataUpdateCoordinator

_LOGGER = logging.getLogger(__name__)
_BASE_URL = "https://europe-west1-chargesplithome.cloudfunctions.net/secureEndpoint"

CHARGEPOINT_OPERATION_MODES = [
    "6", "7", "8", "9", "10", "11", "12", "13", "14", "15",
    "16", "17", "18", "19", "20", "21", "22", "23", "24", "25",
    "26", "27", "28", "29", "30", "31", "32",
]

CHARGEPOINT_LOCK_MODES = ["LOCK", "UNLOCK"]
CHARGEPOINT_PAUSE_MODES = ["PAUSE", "RESTART"]

OPERATION_MODE = SelectEntityDescription(
    key="operation_mode",
    name="Power Limit",
    icon="mdi:ev-charger",
    entity_category=EntityCategory.CONFIG,
)

LOCK_MODE = SelectEntityDescription(
    key="lock_mode",
    name="Lock",
    icon="mdi:lock",
    entity_category=EntityCategory.CONFIG,
)

PAUSE_MODE = SelectEntityDescription(
    key="pause_mode",
    name="Pause",
    icon="mdi:pause-circle",
    entity_category=EntityCategory.CONFIG,
)


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    coordinator: ChargesplitDataUpdateCoordinator = hass.data[DOMAIN][config_entry.entry_id]
    code = config_entry.data["code"]
    serial = config_entry.data["serial"]

    async_add_entities([
        ChargepointOperationModeEntity(OPERATION_MODE, serial, code, coordinator),
        ChargepointLockModeEntity(LOCK_MODE, serial, code),
        ChargepointPauseModeEntity(PAUSE_MODE, serial, code),
    ])


class _BaseSelectEntity(SelectEntity):
    _attr_should_poll = False
    _attr_has_entity_name = True

    def __init__(self, description: SelectEntityDescription, serial: str, code: str) -> None:
        self.entity_description = description
        self._attr_unique_id = f"{serial}_{description.key}"
        self._attr_current_option = None
        self.serial = serial
        self.code = code

    @property
    def device_info(self) -> DeviceInfo:
        return DeviceInfo(
            identifiers={(DOMAIN, self.serial)},
            name=f"Chargesplit {self.serial}",
            manufacturer="Chargesplit",
        )


class ChargepointOperationModeEntity(CoordinatorEntity, _BaseSelectEntity):
    def __init__(
        self,
        description: SelectEntityDescription,
        serial: str,
        code: str,
        coordinator: ChargesplitDataUpdateCoordinator,
    ) -> None:
        CoordinatorEntity.__init__(self, coordinator)
        _BaseSelectEntity.__init__(self, description, serial, code)
        self._attr_options = CHARGEPOINT_OPERATION_MODES

    @property
    def current_option(self) -> str | None:
        if not self.coordinator.data:
            return None
        value = self.coordinator.data.get("PILOTLIMIT")
        return str(value) if value is not None else None

    async def async_select_option(self, option: str) -> None:
        data = {"SECRET": self.code, "SERIAL": self.serial, "COMMAND": "PILOTCHANGE", "VALUE": option}
        try:
            response = await self.hass.async_add_executor_job(
                lambda: requests.post(_BASE_URL, data=data)
            )
            response.raise_for_status()
        except Exception as err:
            raise HomeAssistantError(f"Failed to set power to {option}A: {err}") from err
        await self.coordinator.async_request_refresh()


class ChargepointLockModeEntity(_BaseSelectEntity):
    def __init__(self, description: SelectEntityDescription, serial: str, code: str) -> None:
        super().__init__(description, serial, code)
        self._attr_options = CHARGEPOINT_LOCK_MODES

    async def async_select_option(self, option: str) -> None:
        data = {"SECRET": self.code, "SERIAL": self.serial, "COMMAND": "LOCK", "VALUE": option}
        try:
            response = await self.hass.async_add_executor_job(
                lambda: requests.post(_BASE_URL, data=data)
            )
            response.raise_for_status()
        except Exception as err:
            raise HomeAssistantError(f"Failed to set lock to {option}: {err}") from err
        self._attr_current_option = option
        self.async_write_ha_state()


class ChargepointPauseModeEntity(_BaseSelectEntity):
    def __init__(self, description: SelectEntityDescription, serial: str, code: str) -> None:
        super().__init__(description, serial, code)
        self._attr_options = CHARGEPOINT_PAUSE_MODES

    async def async_select_option(self, option: str) -> None:
        data = {"SECRET": self.code, "SERIAL": self.serial, "COMMAND": "PAUSERESTART", "VALUE": option}
        try:
            response = await self.hass.async_add_executor_job(
                lambda: requests.post(_BASE_URL, data=data)
            )
            response.raise_for_status()
        except Exception as err:
            raise HomeAssistantError(f"Failed to set pause/restart to {option}: {err}") from err
        self._attr_current_option = option
        self.async_write_ha_state()
