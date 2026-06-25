from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorStateClass,
)
from homeassistant.const import (
    PERCENTAGE,
    UnitOfApparentPower,
    UnitOfElectricCurrent,
    UnitOfElectricPotential,
    UnitOfFrequency,
    UnitOfPower,
    UnitOfTemperature,
)

from ...utils.const import DOMAIN, CONF_NAME_KEY, ENTITIES_SCAN_INTERVAL
from ...utils.device import get_device_info


UPS_SENSOR_CONFIG = {
    "battery.charge": {
        "name": "Battery Charge",
        "unit": PERCENTAGE,
        "device_class": SensorDeviceClass.BATTERY,
        "state_class": SensorStateClass.MEASUREMENT,
        "icon": "mdi:battery",
    },
    "battery.voltage": {
        "name": "Battery Voltage",
        "unit": UnitOfElectricPotential.VOLT,
        "device_class": SensorDeviceClass.VOLTAGE,
        "state_class": SensorStateClass.MEASUREMENT,
        "icon": "mdi:flash",
    },
    "battery.status": {
        "name": "Battery Status",
        "icon": "mdi:battery-heart-variant",
    },
    "input.voltage": {
        "name": "Input Voltage",
        "unit": UnitOfElectricPotential.VOLT,
        "device_class": SensorDeviceClass.VOLTAGE,
        "state_class": SensorStateClass.MEASUREMENT,
        "icon": "mdi:flash",
    },
    "input.current": {
        "name": "Input Current",
        "unit": UnitOfElectricCurrent.AMPERE,
        "device_class": SensorDeviceClass.CURRENT,
        "state_class": SensorStateClass.MEASUREMENT,
        "icon": "mdi:current-ac",
    },
    "input.frequency": {
        "name": "Input Frequency",
        "unit": UnitOfFrequency.HERTZ,
        "device_class": SensorDeviceClass.FREQUENCY,
        "state_class": SensorStateClass.MEASUREMENT,
        "icon": "mdi:sine-wave",
    },
    "output.voltage": {
        "name": "Output Voltage",
        "unit": UnitOfElectricPotential.VOLT,
        "device_class": SensorDeviceClass.VOLTAGE,
        "state_class": SensorStateClass.MEASUREMENT,
        "icon": "mdi:flash",
    },
    "output.current": {
        "name": "Output Current",
        "unit": UnitOfElectricCurrent.AMPERE,
        "device_class": SensorDeviceClass.CURRENT,
        "state_class": SensorStateClass.MEASUREMENT,
        "icon": "mdi:current-ac",
    },
    "output.power": {
        "name": "Output Power",
        "unit": UnitOfPower.WATT,
        "device_class": SensorDeviceClass.POWER,
        "state_class": SensorStateClass.MEASUREMENT,
        "icon": "mdi:power-plug",
    },
    "output.apower": {
        "name": "Output Apparent Power",
        "unit": UnitOfApparentPower.VOLT_AMPERE,
        "device_class": SensorDeviceClass.APPARENT_POWER,
        "state_class": SensorStateClass.MEASUREMENT,
        "icon": "mdi:power-plug",
    },
    "ups.temperature": {
        "name": "Temperature",
        "unit": UnitOfTemperature.CELSIUS,
        "device_class": SensorDeviceClass.TEMPERATURE,
        "state_class": SensorStateClass.MEASUREMENT,
        "icon": "mdi:thermometer",
    },
    "ups.load": {
        "name": "Load",
        "unit": PERCENTAGE,
        "state_class": SensorStateClass.MEASUREMENT,
        "icon": "mdi:gauge",
    },
    "ups.status": {
        "name": "Status",
        "icon": "mdi:information-outline",
    },
}


def get_ups_sensors(hass, entry, manager, data):
    device_info = get_device_info(entry)
    sensors = []
    for metric_key in UPS_SENSOR_CONFIG:
        if data.get(metric_key) is None:
            continue
        sensors.append(
            RagtechUpsSensor(
                hass,
                entry,
                manager,
                device_info,
                metric_key,
                data,
            )
        )
    return sensors


class RagtechUpsSensor(SensorEntity):
    def __init__(self, hass, entry, manager, device_info, metric_key, data):
        self._hass = hass
        self._entry = entry
        self._manager = manager
        self._device_info = device_info
        self._metric_key = metric_key

        self._data = data

        self._attr_should_poll = True
        self._attr_scan_interval = ENTITIES_SCAN_INTERVAL

    async def async_update(self):
        data = await self._manager.get_status()
        if data:
            self._data = data

    @property
    def state(self):
        return self._data.get(self._metric_key)

    @property
    def unit_of_measurement(self):
        return UPS_SENSOR_CONFIG[self._metric_key].get("unit")

    @property
    def device_class(self):
        return UPS_SENSOR_CONFIG[self._metric_key].get("device_class")

    @property
    def state_class(self):
        return UPS_SENSOR_CONFIG[self._metric_key].get("state_class")

    @property
    def name(self):
        config = UPS_SENSOR_CONFIG[self._metric_key]
        return f"{self._entry.data.get(CONF_NAME_KEY)} {config['name']}"

    @property
    def icon(self):
        return UPS_SENSOR_CONFIG[self._metric_key].get("icon")

    @property
    def unique_id(self):
        key = self._metric_key.replace(".", "_")
        return f"{DOMAIN}_{self._entry.entry_id}_{key}_sensor"

    @property
    def device_info(self):
        return self._device_info
