from types import SimpleNamespace

import pytest

from custom_components.ragtech.serial.flags import FLAGS
from custom_components.ragtech.serial.parser import parse_data
from vendor_frames import POST_SWAP

# Entity modules need Home Assistant; the serial layer is tested without it.
binary = pytest.importorskip("custom_components.ragtech.entities.ups.ups_binary_sensor")
sensor = pytest.importorskip("custom_components.ragtech.entities.ups.ups_sensor")

ENTRY = SimpleNamespace(entry_id="abc", data={"name": "Nobreak"}, options={})
# Stand-ins for the client manager: the UPS answers, or has gone silent.
FRESH = SimpleNamespace(stale=False)
STALE = SimpleNamespace(stale=True)
DATA = parse_data(POST_SWAP.frame, "one_up_2000_nitro_ti")


def test_every_sensor_reads_a_parsed_value():
    assert set(sensor.UPS_SENSOR_CONFIG) <= set(DATA)
    assert set(sensor.UPS_SENSOR_CONFIG) | set(FLAGS) == set(DATA)


def test_raw_register_sensors_are_diagnostic():
    sensors = {
        entity.unique_id: entity
        for entity in sensor.get_ups_sensors(None, ENTRY, FRESH, DATA)
    }
    register = sensors["ragtech_abc_ups_register_80_sensor"]
    assert register.native_value == "0x21"
    assert register.name == "Nobreak Register 0x80"
    assert register.entity_category == "diagnostic"
    assert sensors["ragtech_abc_ups_settings_sensor"].entity_category == "diagnostic"
    assert sensors["ragtech_abc_battery_voltage_sensor"].entity_category is None


def test_uncalibrated_sensors_exist_but_are_unavailable():
    sensors = {
        entity.unique_id: entity
        for entity in sensor.get_ups_sensors(None, ENTRY, FRESH, DATA)
    }
    assert len(sensors) == len(sensor.UPS_SENSOR_CONFIG)
    assert DATA["output.current"] is None
    assert not sensors["ragtech_abc_output_current_sensor"].available
    assert sensors["ragtech_abc_output_voltage_sensor"].available


def test_every_flag_has_a_binary_sensor():
    assert set(binary.UPS_BINARY_SENSOR_CONFIG) == set(FLAGS)


def test_binary_sensor_reports_its_flag():
    data = dict.fromkeys(FLAGS, False) | {"battery.aged": True}
    sensors = {
        entity.unique_id: entity
        for entity in binary.get_ups_binary_sensors(ENTRY, FRESH, data)
    }
    replace_battery = sensors["ragtech_abc_battery_aged_binary_sensor"]
    assert replace_battery.is_on
    assert replace_battery.name == "Nobreak Replace Battery"
    assert replace_battery.device_class == "problem"
    assert not sensors["ragtech_abc_battery_low_binary_sensor"].is_on


def test_entities_are_unavailable_while_the_ups_is_silent():
    silent = [
        *sensor.get_ups_sensors(None, ENTRY, STALE, DATA),
        *binary.get_ups_binary_sensors(ENTRY, STALE, DATA),
    ]
    assert not any(entity.available for entity in silent)
    answering = binary.get_ups_binary_sensors(ENTRY, FRESH, DATA)
    assert all(entity.available for entity in answering)
