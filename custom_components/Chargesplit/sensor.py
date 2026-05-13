import logging

from homeassistant.config_entries import ConfigEntry

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)

from homeassistant.const import (
    EntityCategory,
    UnitOfElectricCurrent,
    UnitOfElectricPotential,
    UnitOfEnergy,
    UnitOfPower,
    UnitOfTemperature,
)

from .const import DOMAIN
from .entity import ChargesplitEntity
from .coordinator import ChargesplitDataUpdateCoordinator

_LOGGER: logging.Logger = logging.getLogger(__package__)


async def async_setup_entry(hass, entry, async_add_devices):
    coordinator = hass.data[DOMAIN][entry.entry_id]
    serial = entry.data["serial"]
    _LOGGER.info("Setting up ChargeSplit with serial " + serial)

    INSTRUMENTS = [
        # (id, description, key, unit, icon, device_class, state_class, serial, entity_category)
        (
            "power_voltagel2",
            "Voltage L2",
            "VOLT2",
            UnitOfElectricPotential.VOLT,
            "mdi:lightning-bolt",
            SensorDeviceClass.VOLTAGE,
            SensorStateClass.MEASUREMENT,
            serial,
            None,
        ),
        (
            "power_voltagel1",
            "Voltage L1",
            "VOLT1",
            UnitOfElectricPotential.VOLT,
            "mdi:lightning-bolt",
            SensorDeviceClass.VOLTAGE,
            SensorStateClass.MEASUREMENT,
            serial,
            None,
        ),
        (
            "power_voltagel3",
            "Voltage L3",
            "VOLT3",
            UnitOfElectricPotential.VOLT,
            "mdi:lightning-bolt",
            SensorDeviceClass.VOLTAGE,
            SensorStateClass.MEASUREMENT,
            serial,
            None,
        ),
        (
            "device_temperature",
            "Temperature",
            "TEMP",
            UnitOfTemperature.CELSIUS,
            "mdi:temperature-celsius",
            SensorDeviceClass.TEMPERATURE,
            SensorStateClass.MEASUREMENT,
            serial,
            None,
        ),
        (
            "state_class",
            "Wallbox Status",
            "STATUS",
            None,
            "mdi:ev-station",
            None,
            None,
            serial,
            None,
        ),
        (
            "device_model",
            "Wallbox Model",
            "MODEL",
            None,
            "mdi:ev-station",
            None,
            None,
            serial,
            EntityCategory.DIAGNOSTIC,
        ),
        (
            "device_firmware",
            "Wallbox firmware",
            "FWVERS",
            None,
            "mdi:ev-station",
            None,
            None,
            serial,
            EntityCategory.DIAGNOSTIC,
        ),
        (
            "device_serial",
            "Wallbox serial",
            "SERIAL",
            None,
            "mdi:ev-station",
            None,
            None,
            serial,
            EntityCategory.DIAGNOSTIC,
        ),
        (
            "power_charged_kWh",
            "Charged kWh",
            "TOTALCHARGED",
            UnitOfEnergy.KILO_WATT_HOUR,
            "mdi:speedometer",
            SensorDeviceClass.ENERGY,
            SensorStateClass.TOTAL_INCREASING,
            serial,
            None,
        ),
        (
            "power_pilotamps",
            "Pilot Amps",
            "PILOTLIMIT",
            UnitOfElectricCurrent.AMPERE,
            "mdi:speedometer",
            SensorDeviceClass.CURRENT,
            SensorStateClass.MEASUREMENT,
            serial,
            None,
        ),
        (
            "power_actual_amps",
            "Actual Amps",
            "AMP",
            UnitOfElectricCurrent.AMPERE,
            "mdi:current-ac",
            SensorDeviceClass.CURRENT,
            SensorStateClass.MEASUREMENT,
            serial,
            None,
        ),
        (
            "power_solar_power",
            "Actual solar power",
            "SOLARPWR",
            UnitOfPower.KILO_WATT,
            "mdi:speedometer",
            SensorDeviceClass.POWER,
            SensorStateClass.MEASUREMENT,
            serial,
            None,
        ),
        (
            "power_house_power",
            "Actual House Consumption",
            "HOUSEPWR",
            UnitOfPower.KILO_WATT,
            "mdi:speedometer",
            SensorDeviceClass.POWER,
            SensorStateClass.MEASUREMENT,
            serial,
            None,
        ),
        (
            "power_car_charging",
            "Car Charging Power",
            "CHARGINGPWR",
            UnitOfPower.KILO_WATT,
            "mdi:speedometer",
            SensorDeviceClass.POWER,
            SensorStateClass.MEASUREMENT,
            serial,
            None,
        ),
        (
            "house_charged_Wh",
            "Daily House Wh",
            "DAYHOUSE",
            UnitOfEnergy.WATT_HOUR,
            "mdi:speedometer",
            SensorDeviceClass.ENERGY,
            SensorStateClass.TOTAL_INCREASING,
            serial,
            None,
        ),
        (
            "solar_charged_Wh",
            "Daily Solar Wh",
            "DAYSOLAR",
            UnitOfEnergy.WATT_HOUR,
            "mdi:speedometer",
            SensorDeviceClass.ENERGY,
            SensorStateClass.TOTAL_INCREASING,
            serial,
            None,
        ),
        (
            "schedule_state",
            "Schedule",
            "SCHEDULE",
            None,
            "mdi:calendar-clock",
            None,
            None,
            serial,
            EntityCategory.DIAGNOSTIC,
        ),
    ]

    sensors = [
        ChargesplitSensor(
            coordinator, entry, id, description, key, unit, icon, device_class, state_class, serial, entity_category
        )
        for id, description, key, unit, icon, device_class, state_class, serial, entity_category in INSTRUMENTS
    ]

    async_add_devices(sensors, True)


class ChargesplitSensor(ChargesplitEntity, SensorEntity):

    def __init__(
        self,
        coordinator: ChargesplitDataUpdateCoordinator,
        entry: ConfigEntry,
        id: str,
        description: str,
        key: str,
        unit: str,
        icon: str,
        device_class: str,
        state_class: str,
        serial,
        entity_category=None,
    ):
        super().__init__(coordinator, entry)
        self._id = f"{serial}-{description}"
        self.description = description
        self.key = key
        self.unit = unit
        self._icon = icon
        self._device_class = device_class
        self._state_class = state_class
        self._attr_entity_category = entity_category

    @property
    def native_value(self):
        if not self.coordinator.data:
            return None
        return self.coordinator.data.get(self.key)

    @property
    def native_unit_of_measurement(self):
        return self.unit

    @property
    def icon(self):
        return self._icon

    @property
    def device_class(self):
        return self._device_class

    @property
    def state_class(self):
        return self._state_class

    @property
    def name(self):
        return f"{self.description}"

    @property
    def id(self):
        return f"{DOMAIN}_{self._id}"

    @property
    def unique_id(self):
        return f"{DOMAIN}-{self._id}-{self.coordinator.api.host}"
