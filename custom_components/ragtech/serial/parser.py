import logging
from typing import NamedTuple

from .flags import FULL_CHARGE, battery_status, decode_flags, ups_status
from .models import MODEL_EASY_PRO, UPS_MODELS

_LOGGER = logging.getLogger(__name__)

# A status frame is a start-of-frame byte plus a register dump: byte N holds
# register 0x80 + N - 1, so byte 1 is data, not a header.
FRAME_SOF = 0xAA
FRAME_LENGTH = 31
# High nibble of the lone byte the UPS sends to refuse a request.
REFUSAL = 0xC0

# Status frame bytes the parser reads.
NONVOLATILE_FLAGS = 1  # register 0x80
SETTINGS = slice(1, 8)  # registers 0x80-0x86
CAPACITY_REFERENCE = 4  # register 0x83
BATTERY_CHARGE = 8  # register 0x87
BATTERY_VOLTAGE = 11  # register 0x8A
INPUT_VOLTAGE = 12  # register 0x8B
OUTPUT_CURRENT = 13  # register 0x8C
LOAD = 14  # register 0x8D
TEMPERATURE = 15  # register 0x8E
OUTPUT_FREQUENCY = 24  # register 0x97, the inverter oscillator count
MODEL_CODE = 27  # register 0x9A
FIRMWARE = 28  # register 0x9B, in tenths
OUTPUT_VOLTAGE = 30  # register 0x9D

# Scales every model shares.
BATTERY_CHARGE_SCALE = 0.393
INPUT_VOLTAGE_SCALE = 1.06


class Calibration(NamedTuple):
    """Per-unit calibration registers; None where the UPS provided no value."""

    current: int | None = None  # register 0x00F3
    osc53: int | None = None  # register 0x0202
    osc57: int | None = None  # register 0x0203


NO_CALIBRATION = Calibration()


def is_frame(data):
    return len(data) >= FRAME_LENGTH and data[0] == FRAME_SOF


def is_refusal(data):
    return len(data) == 1 and data[0] & 0xF0 == REFUSAL


def detect_model(data):
    """Return the model key for a status frame, or None if unrecognised."""
    if not is_frame(data):
        return None
    for key, model in UPS_MODELS.items():
        if data[MODEL_CODE] == model.code:
            return key
    return None


def _output_current(raw, model, calibration):
    # Without the unit's calibration byte the reading has no scale.
    if not calibration.current:
        return None
    return raw * model.output_current_factor / calibration.current


def _output_frequency(raw, calibration):
    # The oscillator count is interpolated between its 53 Hz and 57 Hz marks.
    osc53, osc57 = calibration.osc53, calibration.osc57
    if osc53 is None or osc57 is None or osc53 == osc57:
        return None
    return (53 + 4 * (raw - osc53) / (osc57 - osc53)) * 0.9806 + 1.46


def decode_frame(data, model, calibration=NO_CALIBRATION):
    """Scale the registers of a status frame the way Ragtech's software does."""
    return {
        "battery_charge": min(data[BATTERY_CHARGE] * BATTERY_CHARGE_SCALE, FULL_CHARGE),
        "battery_voltage": data[BATTERY_VOLTAGE] * model.battery_voltage_scale,
        "input_voltage": data[INPUT_VOLTAGE] * INPUT_VOLTAGE_SCALE,
        "output_voltage": data[OUTPUT_VOLTAGE] * model.output_voltage_scale,
        "output_current": _output_current(data[OUTPUT_CURRENT], model, calibration),
        "output_frequency": _output_frequency(data[OUTPUT_FREQUENCY], calibration),
        "load": data[LOAD],
        "temperature": data[TEMPERATURE],
    }


def _round(value, digits):
    return None if value is None else round(value, digits)


def parse_data(data, model=MODEL_EASY_PRO, calibration=NO_CALIBRATION):
    """
    Parse a raw serial response from a Ragtech UPS.

    `model` is the key of the ``UPS_MODELS`` row to decode with. Output current
    and frequency, and the values derived from them, are None when
    `calibration` lacks the registers they need.
    """
    profile = UPS_MODELS.get(model)
    if profile is None:
        _LOGGER.debug("[parse_data] unknown model: %s", model)
        return None

    if not is_frame(data):
        _LOGGER.debug("[parse_data] unexpected response: %s", data.hex())
        return None

    values = decode_frame(data, profile, calibration)
    battery_charge = round(values["battery_charge"])
    input_voltage = round(values["input_voltage"])
    output_voltage = round(values["output_voltage"])
    output_current = _round(values["output_current"], 2)

    apparent_power = real_power = current_in = None
    if output_current is not None:
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

    flags = decode_flags(data)

    return {
        "battery.charge": battery_charge,
        "battery.voltage": round(values["battery_voltage"], 2),
        "battery.status": battery_status(flags, battery_charge),
        "input.voltage": input_voltage,
        "input.current": current_in,
        "output.voltage": output_voltage,
        "output.frequency": _round(values["output_frequency"], 2),
        "output.current": output_current,
        "output.power": real_power,
        "output.apower": apparent_power,
        "ups.temperature": values["temperature"],
        "ups.load": values["load"],
        "ups.status": ups_status(flags),
        "ups.model_code": data[MODEL_CODE],
        "ups.firmware": f"{data[FIRMWARE] / 10:.1f}",
        "battery.capacity_reference": data[CAPACITY_REFERENCE],
        # Raw registers, published as they are: bits 3 and 5 of 0x80 have no
        # known meaning and must not be interpreted.
        "ups.register_80": f"0x{data[NONVOLATILE_FLAGS]:02X}",
        "ups.settings": data[SETTINGS].hex(" ").upper(),
        **flags,
    }
