"""
State flags a Ragtech UPS reports in registers 0x90-0x92.

Bit positions and meanings follow Ragtech's own register map. In a status
frame these registers are bytes 17-19, because byte N holds register
0x80 + N - 1.
"""

# flag key -> (status frame byte, bit)
FLAGS = {
    # Register 0x90: events.
    "battery.missing": (17, 0),
    "battery.aged": (17, 1),
    "battery.test_running": (17, 2),
    "input.absent": (17, 3),
    "input.voltage_low": (17, 4),
    "input.voltage_high": (17, 5),
    "ups.on_battery": (17, 6),
    "ups.load_high": (17, 7),
    # Register 0x91: battery low warning and faults.
    "battery.low": (18, 0),
    "fault.over_temperature": (18, 1),
    "fault.battery_exhausted": (18, 2),
    "fault.overload": (18, 3),
    "fault.output_voltage": (18, 4),
    "fault.battery_voltage": (18, 5),
    "fault.inverter": (18, 6),
    "fault.output_short": (18, 7),
    # Register 0x92: operating state. Bit 4 has no known meaning.
    "ups.synchronised": (19, 0),
    "ups.software_attached": (19, 1),
    "battery.capacity_increased": (19, 2),
    "battery.capacity_reduced": (19, 3),
    "ups.remote_control": (19, 5),
    "ups.powerlook": (19, 6),
    "ups.timer_armed": (19, 7),
}

FAULTS = tuple(key for key in FLAGS if key.startswith("fault."))

FULL_CHARGE = 100


def decode_flags(frame):
    """Return every known flag of a status frame as a bool."""
    flags = {key: bool((frame[byte] >> bit) & 1) for key, (byte, bit) in FLAGS.items()}
    # Ragtech's software ignores "mains low" while mains is absent.
    if flags["input.absent"]:
        flags["input.voltage_low"] = False
    return flags


def ups_status(flags):
    """Return a NUT-style status built from the flags alone."""
    status = ["OB" if flags["ups.on_battery"] else "OL"]
    if flags["battery.low"]:
        status.append("LB")
    if flags["battery.aged"] or flags["battery.missing"]:
        status.append("RB")
    if flags["fault.overload"]:
        status.append("OVER")
    if any(flags[key] for key in FAULTS):
        status.append("ALARM")
    return " ".join(status)


def battery_status(flags, charge):
    """Return the battery state; charging is inferred, the UPS has no flag for it."""
    if flags["ups.on_battery"]:
        return "DISCHARGING"
    return "CHARGING" if charge < FULL_CHARGE else "FULL"
