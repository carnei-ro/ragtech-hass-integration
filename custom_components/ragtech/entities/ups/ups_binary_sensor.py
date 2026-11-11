from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
)
from homeassistant.const import EntityCategory

from ...utils.const import DOMAIN, CONF_NAME_KEY
from ...utils.device import get_device_info

PROBLEM = {"device_class": BinarySensorDeviceClass.PROBLEM}
DIAGNOSTIC = {"entity_category": EntityCategory.DIAGNOSTIC}

# Flag key (see serial/flags.py) -> entity description.
UPS_BINARY_SENSOR_CONFIG = {
    "battery.aged": {"name": "Replace Battery", **PROBLEM},
    "battery.capacity_reduced": {"name": "Battery Capacity Reduced", **PROBLEM},
    "battery.missing": {"name": "Battery Missing", **PROBLEM},
    "battery.low": {
        "name": "Battery Low",
        "device_class": BinarySensorDeviceClass.BATTERY,
    },
    "ups.on_battery": {"name": "On Battery"},
    "input.absent": {"name": "Mains Absent", **PROBLEM},
    "input.voltage_low": {"name": "Mains Voltage Low", **PROBLEM},
    "input.voltage_high": {"name": "Mains Voltage High", **PROBLEM},
    "ups.load_high": {"name": "Overload Warning", **PROBLEM},
    "fault.over_temperature": {"name": "Over Temperature Fault", **PROBLEM},
    "fault.battery_exhausted": {"name": "Battery Exhausted Fault", **PROBLEM},
    "fault.overload": {"name": "Overload Fault", **PROBLEM},
    "fault.output_voltage": {"name": "Output Voltage Fault", **PROBLEM},
    "fault.battery_voltage": {"name": "Battery Voltage Fault", **PROBLEM},
    "fault.inverter": {"name": "Inverter Fault", **PROBLEM},
    "fault.output_short": {"name": "Output Short Circuit Fault", **PROBLEM},
    "battery.test_running": {
        "name": "Battery Discharge Test",
        "device_class": BinarySensorDeviceClass.RUNNING,
        **DIAGNOSTIC,
    },
    "battery.capacity_increased": {
        "name": "Battery Capacity Increased",
        **DIAGNOSTIC,
    },
    "ups.synchronised": {"name": "Synchronised to Mains", **DIAGNOSTIC},
    "ups.software_attached": {"name": "Vendor Software Attached", **DIAGNOSTIC},
    "ups.remote_control": {"name": "Remote Control", **DIAGNOSTIC},
    "ups.powerlook": {"name": "Powerlook", **DIAGNOSTIC},
    "ups.timer_armed": {"name": "Timer Armed", **DIAGNOSTIC},
}


def get_ups_binary_sensors(entry, manager, data):
    device_info = get_device_info(entry)
    return [
        RagtechUpsBinarySensor(entry, manager, device_info, flag_key, data)
        for flag_key in UPS_BINARY_SENSOR_CONFIG
    ]


class RagtechUpsBinarySensor(BinarySensorEntity):
    def __init__(self, entry, manager, device_info, flag_key, data):
        config = UPS_BINARY_SENSOR_CONFIG[flag_key]
        self._manager = manager
        self._flag_key = flag_key
        self._data = data

        key = flag_key.replace(".", "_")
        self._attr_unique_id = f"{DOMAIN}_{entry.entry_id}_{key}_binary_sensor"
        self._attr_name = f"{entry.data.get(CONF_NAME_KEY)} {config['name']}"
        self._attr_device_class = config.get("device_class")
        self._attr_entity_category = config.get("entity_category")
        self._attr_device_info = device_info

    async def async_update(self):
        data = await self._manager.get_status()
        if data:
            self._data = data

    @property
    def is_on(self):
        return self._data.get(self._flag_key)
