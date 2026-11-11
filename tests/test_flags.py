import pytest

from custom_components.ragtech.serial.flags import (
    FLAGS,
    battery_status,
    decode_flags,
    ups_status,
)
from vendor_frames import FRAMES, PRE_SWAP

# Ragtech's name for each flag its software evaluates -> integration key.
VENDOR_FLAGS = {
    "noBattery": "battery.missing",
    "oldBattery": "battery.aged",
    "opCheckup": "battery.test_running",
    "noVInput": "input.absent",
    "loVInput": "input.voltage_low",
    "hiVInput": "input.voltage_high",
    "opBattery": "ups.on_battery",
    "hiPOutput": "ups.load_high",
    "loBattery": "battery.low",
    "failOvertemp": "fault.over_temperature",
    "failEndBattery": "fault.battery_exhausted",
    "failOverload": "fault.overload",
    "failAbnormalVOutput": "fault.output_voltage",
    "failAbnormalVBattery": "fault.battery_voltage",
    "failInverter": "fault.inverter",
    "failShortcircuit": "fault.output_short",
    "syncInput": "ups.synchronised",
    "moreBattery": "battery.capacity_increased",
    "lessBattery": "battery.capacity_reduced",
    "remoteControlActive": "ups.remote_control",
}


def flags_of(events=0, faults=0, state=0):
    frame = bytearray(31)
    frame[17:20] = events, faults, state
    return decode_flags(bytes(frame))


@pytest.mark.parametrize("vendor", FRAMES, ids=lambda vendor: vendor.frame_hex)
def test_flags_match_the_vendor_decode(vendor):
    flags = decode_flags(vendor.frame)
    assert {name for name, key in VENDOR_FLAGS.items() if flags[key]} == set(
        vendor.flags
    )


def test_pre_swap_frame_reports_aged_battery_and_reduced_capacity():
    flags = decode_flags(PRE_SWAP.frame)
    assert flags["battery.aged"]
    assert flags["battery.capacity_reduced"]
    assert ups_status(flags) == "OL RB"


@pytest.mark.parametrize("key", FLAGS)
def test_each_bit_sets_exactly_one_flag(key):
    byte, bit = FLAGS[key]
    frame = bytearray(31)
    frame[byte] = 1 << bit
    flags = decode_flags(bytes(frame))
    assert [name for name, value in flags.items() if value] == [key]


def test_unassigned_bit_sets_no_flag():
    assert not any(flags_of(state=0x10).values())


def test_mains_low_is_ignored_while_mains_is_absent():
    assert flags_of(events=0x10)["input.voltage_low"]
    assert not flags_of(events=0x18)["input.voltage_low"]


@pytest.mark.parametrize(
    ("events", "faults", "expected"),
    [
        (0x00, 0x00, "OL"),
        (0x80, 0x00, "OL"),
        (0x48, 0x00, "OB"),
        (0x48, 0x01, "OB LB"),
        (0x02, 0x00, "OL RB"),
        (0x01, 0x00, "OL RB"),
        (0x4A, 0x01, "OB LB RB"),
        (0x00, 0x08, "OL OVER ALARM"),
        (0x00, 0x40, "OL ALARM"),
        (0x48, 0x05, "OB LB ALARM"),
    ],
)
def test_ups_status_comes_from_the_flags(events, faults, expected):
    assert ups_status(flags_of(events, faults)) == expected


@pytest.mark.parametrize(
    ("events", "charge", "expected"),
    [
        (0x48, 100, "DISCHARGING"),
        (0x48, 40, "DISCHARGING"),
        (0x00, 99, "CHARGING"),
        (0x00, 100, "FULL"),
    ],
)
def test_battery_status(events, charge, expected):
    assert battery_status(flags_of(events), charge) == expected
