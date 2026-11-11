from types import SimpleNamespace

import pytest

from custom_components.ragtech.serial.flags import FLAGS

# Entity modules need Home Assistant; the serial layer is tested without it.
binary = pytest.importorskip("custom_components.ragtech.entities.ups.ups_binary_sensor")

ENTRY = SimpleNamespace(entry_id="abc", data={"name": "Nobreak"}, options={})


def test_every_flag_has_a_binary_sensor():
    assert set(binary.UPS_BINARY_SENSOR_CONFIG) == set(FLAGS)


def test_binary_sensor_reports_its_flag():
    data = dict.fromkeys(FLAGS, False) | {"battery.aged": True}
    sensors = {
        sensor.unique_id: sensor
        for sensor in binary.get_ups_binary_sensors(ENTRY, None, data)
    }
    replace_battery = sensors["ragtech_abc_battery_aged_binary_sensor"]
    assert replace_battery.is_on
    assert replace_battery.name == "Nobreak Replace Battery"
    assert replace_battery.device_class == "problem"
    assert not sensors["ragtech_abc_battery_low_binary_sensor"].is_on
