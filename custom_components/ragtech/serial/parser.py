import logging

from .models import MODEL_EASY_PRO, UPS_MODELS

_LOGGER = logging.getLogger(__name__)

# Below this input voltage the UPS is considered running on battery (mains down).
ONLINE_INPUT_VOLTAGE = 100
# Battery charge thresholds used to derive the NUT-style status.
LOW_BATTERY_CHARGE = 30
REPLACE_BATTERY_CHARGE = 5
# Relative input/output voltage delta above which the battery is discharging.
DISCHARGE_VOLTAGE_DELTA = 0.10

# Fields whose raw values are (byte_offset, multiplier, additive_offset)
# lookups inside a model profile.
_METRIC_FIELDS = (
    "battery_charge",
    "battery_voltage",
    "input_voltage",
    "output_current",
    "load",
    "temperature",
    "frequency",
    "output_voltage",
)


def _read(hex_str, spec):
    offset, multiplier, additive = spec
    raw = int(hex_str[offset * 2 : offset * 2 + 2], 16)
    return raw * multiplier + additive


def parse_data(data, model=MODEL_EASY_PRO):
    """Parse a raw serial response from a Ragtech UPS.

    `model` selects which calibration profile in ``UPS_MODELS`` to use.
    """
    profile = UPS_MODELS.get(model)
    if profile is None:
        _LOGGER.debug("[parse_data] unknown model: %s", model)
        return None

    hex_str = "".join(f"{byte:02x}" for byte in data)
    expected_hex_len = profile["response_length"] * 2

    if not (hex_str.startswith(profile["header"]) and len(hex_str) >= expected_hex_len):
        _LOGGER.debug("[parse_data] unexpected response: %s", hex_str)
        return None

    values = {field: _read(hex_str, profile[field]) for field in _METRIC_FIELDS}

    battery_charge = round(values["battery_charge"])
    battery_voltage = round(values["battery_voltage"], 2)
    input_voltage = round(values["input_voltage"])
    output_current = round(values["output_current"], 2)
    load = round(values["load"])
    temperature = round(values["temperature"])
    frequency = round(values["frequency"], 2)
    output_voltage = round(values["output_voltage"])

    battery_status = "FULL"

    apparent_power = round(output_voltage * output_current, 1)
    # Power factor of 0.7 -> 1.3 multiplier is used for the real power estimate.
    power_factor = 1.3
    real_power = round(apparent_power * power_factor, 1)
    # Efficiency factor derived from multimeter readings and the official app.
    efficiency = 0.60
    current_in = 0.0
    if input_voltage > 0:
        current_in = round(
            (output_voltage * output_current) / (input_voltage * efficiency), 2
        )

    if input_voltage < ONLINE_INPUT_VOLTAGE:
        ups_status = "LB" if battery_charge < LOW_BATTERY_CHARGE else "OB"
    else:
        ups_status = "OL"

    if battery_charge < REPLACE_BATTERY_CHARGE:
        ups_status = "RB"

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
        "battery.voltage": battery_voltage,
        "battery.status": battery_status,
        "input.voltage": input_voltage,
        "input.current": current_in,
        "input.frequency": frequency,
        "output.voltage": output_voltage,
        "output.current": output_current,
        "output.power": apparent_power,
        "output.apower": real_power,
        "ups.temperature": temperature,
        "ups.load": load,
        "ups.status": ups_status,
    }
