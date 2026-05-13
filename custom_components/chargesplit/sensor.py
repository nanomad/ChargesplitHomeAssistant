import logging

from homeassistant.config_entries import ConfigEntry

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
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

# (unique_id_suffix, name, data_key, unit, icon, device_class, state_class, entity_category)
INSTRUMENTS = [
    ("voltage_l1", "Voltage L1", "VOLT1", UnitOfElectricPotential.VOLT, "mdi:lightning-bolt", SensorDeviceClass.VOLTAGE, SensorStateClass.MEASUREMENT, None),
    ("voltage_l2", "Voltage L2", "VOLT2", UnitOfElectricPotential.VOLT, "mdi:lightning-bolt", SensorDeviceClass.VOLTAGE, SensorStateClass.MEASUREMENT, None),
    ("voltage_l3", "Voltage L3", "VOLT3", UnitOfElectricPotential.VOLT, "mdi:lightning-bolt", SensorDeviceClass.VOLTAGE, SensorStateClass.MEASUREMENT, None),
    ("temperature", "Temperature", "TEMP", UnitOfTemperature.CELSIUS, "mdi:thermometer", SensorDeviceClass.TEMPERATURE, SensorStateClass.MEASUREMENT, None),
    ("status", "Wallbox Status", "STATUS", None, "mdi:ev-station", None, None, None),
    ("model", "Model", "MODEL", None, "mdi:information-outline", None, None, EntityCategory.DIAGNOSTIC),
    ("firmware", "Firmware", "FWVERS", None, "mdi:chip", None, None, EntityCategory.DIAGNOSTIC),
    ("serial", "Serial", "SERIAL", None, "mdi:barcode", None, None, EntityCategory.DIAGNOSTIC),
    ("total_charged_kwh", "Total Charged", "TOTALCHARGED", UnitOfEnergy.KILO_WATT_HOUR, "mdi:battery-charging", SensorDeviceClass.ENERGY, SensorStateClass.TOTAL_INCREASING, None),
    ("pilot_amps", "Pilot Amps", "PILOTLIMIT", UnitOfElectricCurrent.AMPERE, "mdi:current-ac", SensorDeviceClass.CURRENT, SensorStateClass.MEASUREMENT, None),
    ("actual_amps", "Actual Amps", "AMP", UnitOfElectricCurrent.AMPERE, "mdi:current-ac", SensorDeviceClass.CURRENT, SensorStateClass.MEASUREMENT, None),
    ("solar_power", "Solar Power", "SOLARPWR", UnitOfPower.KILO_WATT, "mdi:solar-power", SensorDeviceClass.POWER, SensorStateClass.MEASUREMENT, None),
    ("house_power", "House Consumption", "HOUSEPWR", UnitOfPower.KILO_WATT, "mdi:home-lightning-bolt", SensorDeviceClass.POWER, SensorStateClass.MEASUREMENT, None),
    ("charging_power", "Charging Power", "CHARGINGPWR", UnitOfPower.KILO_WATT, "mdi:ev-plug-type2", SensorDeviceClass.POWER, SensorStateClass.MEASUREMENT, None),
    ("daily_house_wh", "Daily House Energy", "DAYHOUSE", UnitOfEnergy.WATT_HOUR, "mdi:home-lightning-bolt", SensorDeviceClass.ENERGY, SensorStateClass.TOTAL_INCREASING, None),
    ("daily_solar_wh", "Daily Solar Energy", "DAYSOLAR", UnitOfEnergy.WATT_HOUR, "mdi:solar-power", SensorDeviceClass.ENERGY, SensorStateClass.TOTAL_INCREASING, None),
    ("schedule", "Schedule", "SCHEDULE", None, "mdi:calendar-clock", None, None, EntityCategory.DIAGNOSTIC),
]


async def async_setup_entry(hass, entry: ConfigEntry, async_add_devices):
    coordinator = hass.data[DOMAIN][entry.entry_id]
    serial = entry.data["serial"]

    async_add_devices([
        ChargesplitSensor(coordinator, entry, serial, *instrument)
        for instrument in INSTRUMENTS
    ], True)


class ChargesplitSensor(ChargesplitEntity, SensorEntity):

    def __init__(
        self,
        coordinator: ChargesplitDataUpdateCoordinator,
        entry: ConfigEntry,
        serial: str,
        uid_suffix: str,
        name: str,
        key: str,
        unit: str,
        icon: str,
        device_class,
        state_class,
        entity_category,
    ):
        super().__init__(coordinator, entry)
        self._attr_unique_id = f"{serial}_{uid_suffix}"
        self._attr_name = name
        self._attr_icon = icon
        self._attr_device_class = device_class
        self._attr_state_class = state_class
        self._attr_native_unit_of_measurement = unit
        self._attr_entity_category = entity_category
        self.key = key

    @property
    def native_value(self):
        if not self.coordinator.data:
            return None
        return self.coordinator.data.get(self.key)
