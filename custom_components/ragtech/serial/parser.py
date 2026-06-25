import logging

_LOGGER = logging.getLogger(__name__)

# A valid status response starts with this marker ...
RESPONSE_HEADER = "aa21"
# ... and is at least this many hex chars long (the fields we read end at 62).
MIN_RESPONSE_HEX_LEN = 62

# Below this input voltage the UPS is considered running on battery (mains down).
ONLINE_INPUT_VOLTAGE = 100
# Battery charge thresholds used to derive the NUT-style status.
LOW_BATTERY_CHARGE = 30
REPLACE_BATTERY_CHARGE = 5
# Relative input/output voltage delta above which the battery is discharging.
DISCHARGE_VOLTAGE_DELTA = 0.10


def parse_data(data):
    """
    Parse the raw 64-byte serial response from a Ragtech UPS.

    The decoding constants below are taken from reverse engineering the
    Ragtech serial protocol (see the original ``ragtech.sh`` script) and
    were calibrated against a multimeter and the official Ragtech app.
    """
    hex_str = "".join(f"{byte:02x}" for byte in data)

    if not (
        hex_str.startswith(RESPONSE_HEADER) and len(hex_str) >= MIN_RESPONSE_HEX_LEN
    ):
        _LOGGER.debug("[parse_data] unexpected response: %s", hex_str)
        return None

    battery_charge = round(int(hex_str[16:18], 16) * 0.393)
    input_voltage = round(int(hex_str[52:54], 16) * 1.06)
    output_voltage = round(int(hex_str[60:62], 16) * 0.555)
    temperature = int(hex_str[30:32], 16)
    load = int(hex_str[28:30], 16)
    battery_voltage = round(int(hex_str[22:24], 16) * 0.1342, 2)
    frequency = round(int(hex_str[48:50], 16) * -0.1152 + 65, 2)
    current_out = round(int(hex_str[26:28], 16) * 0.120, 2)
    battery_status = "FULL"

    apparent_power = round(output_voltage * current_out, 1)
    # Power factor of 0.7 -> 1.3 multiplier is used for the real power estimate.
    power_factor = 1.3
    real_power = round(apparent_power * power_factor, 1)
    # Efficiency factor derived from multimeter readings and the official app.
    efficiency = 0.60
    current_in = 0.0
    if input_voltage > 0:
        current_in = round(
            (output_voltage * current_out) / (input_voltage * efficiency), 2
        )

    # Enhanced status logic
    if input_voltage < ONLINE_INPUT_VOLTAGE:
        # LB = Low Battery, OB = On Battery
        ups_status = "LB" if battery_charge < LOW_BATTERY_CHARGE else "OB"
    else:
        ups_status = "OL"  # On Line

    # Battery replacement detection
    if battery_charge < REPLACE_BATTERY_CHARGE:
        ups_status = "RB"

    # Charging / Discharging logic
    if input_voltage > output_voltage:
        ups_status += " CHRG"
        battery_status = "CHARGING"
    elif (
        input_voltage != 0
        and abs(input_voltage - output_voltage) / input_voltage
        > DISCHARGE_VOLTAGE_DELTA
    ):
        ups_status += " DISCHRG"
        battery_status = "DISCHARGING"

    return {
        "battery.charge": battery_charge,
        "battery.voltage": battery_voltage / 2,
        "battery.status": battery_status,
        "input.voltage": input_voltage,
        "input.current": current_in,
        "input.frequency": frequency,
        "output.voltage": output_voltage,
        "output.current": current_out,
        "output.power": apparent_power,
        "output.apower": real_power,
        "ups.temperature": temperature,
        "ups.load": load,
        "ups.status": ups_status,
    }
