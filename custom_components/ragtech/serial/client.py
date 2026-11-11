import logging
import time
from dataclasses import dataclass

import serial

from .models import MODEL_EASY_PRO
from .parser import (
    FAMILIES,
    START,
    Calibration,
    detect_model,
    is_frame,
    is_refusal,
    parse_data,
    reply_family,
)

_LOGGER = logging.getLogger(__name__)

# The family addressed until the UPS names its own: 10, the "Easy" family.
DEFAULT_FAMILY = 10
# Read registers: the only opcode this integration ever sends.
READ = 0x04

# (address, register count) of the ranges the integration reads.
STATUS = (0x0080, 30)
CURRENT_CALIBRATION = (0x00F3, 1)
FREQUENCY_CALIBRATION = (0x0202, 2)

# The UPS needs a short moment to answer after receiving the request.
READ_DELAY = 2


@dataclass
class Detection:
    model: str | None = None
    error: str | None = None
    raw_hex: str | None = None


def read_request(address, count, family=DEFAULT_FAMILY):
    """Build a read request; its checksum covers the address and the count."""
    high, low = address >> 8, address & 0xFF
    checksum = (high + low + count) & 0xFF
    return bytes([START | family, READ, high, low, count, checksum])


def _read(ser, family, address, count):
    """Return the raw reply: a start byte plus `count` registers when all is well."""
    ser.reset_input_buffer()
    ser.write(read_request(address, count, family))
    time.sleep(READ_DELAY)
    return ser.read(count + 1)


def _request_status(ser, family=DEFAULT_FAMILY):
    return _read(ser, family, *STATUS)


def _named_family(reply):
    """Return the family a status frame or a refusal names, else the default."""
    if is_frame(reply) or is_refusal(reply):
        family = reply[0] & 0x0F
        if family in FAMILIES:
            return family
    return DEFAULT_FAMILY


def _read_calibration_range(ser, family, address, count):
    reply = _read(ser, family, address, count)
    if len(reply) == count + 1 and reply_family(reply) == family:
        return reply[1:]
    _LOGGER.warning(
        "[calibration] read at 0x%04X %s (%s); values that need it are unavailable",
        address,
        "refused by the UPS" if is_refusal(reply) else "got no usable reply",
        reply.hex() or "nothing received",
    )
    return None


def _read_calibration(ser, family):
    current = _read_calibration_range(ser, family, *CURRENT_CALIBRATION)
    oscillator = _read_calibration_range(ser, family, *FREQUENCY_CALIBRATION)
    return Calibration(*(current or (None,)), *(oscillator or (None, None)))


def probe_ups_model(port: str, baud_rate: int, timeout: int) -> Detection:
    """
    Probe the UPS and match its model code against the model registry.

    Called from the config flow via an executor job.
    """
    try:
        with serial.Serial(port, baud_rate, timeout=timeout) as ser:
            response = _request_status(ser)
            family = _named_family(response)
            if is_refusal(response) and family != DEFAULT_FAMILY:
                # A unit of another family refused: ask again in its terms.
                response = _request_status(ser, family)
    except Exception as exc:
        _LOGGER.debug("[probe_ups_model] serial error: %s", exc)
        return Detection(error=f"Could not open {port}: {exc}")

    if not response:
        return Detection(error=f"No response from UPS on {port}")

    raw_hex = response.hex()
    model = detect_model(response)
    if model is None:
        reason = (
            "UPS refused the request"
            if is_refusal(response)
            else "Unrecognised response"
        )
        return Detection(
            error=f"{reason} ({len(response)} bytes): {raw_hex}",
            raw_hex=raw_hex,
        )
    return Detection(model=model, raw_hex=raw_hex)


class RagtechSerialClient:
    def __init__(
        self, port: str, baud_rate: int, timeout: int, model: str = MODEL_EASY_PRO
    ):
        self.port = port
        self.baud_rate = baud_rate
        self.timeout = timeout
        self.model = model
        self.last_data = None
        # Hex of the latest reply to the status request, valid or not.
        self.last_frame = None
        self.calibration = Calibration()
        # Set at setup and by every failed poll: read the calibration again.
        self._calibration_due = True
        self._family = DEFAULT_FAMILY

    def get_status(self):
        try:
            with serial.Serial(self.port, self.baud_rate, timeout=self.timeout) as ser:
                _LOGGER.debug(
                    "[get_status] requesting status on %s @ %s baud (%s)",
                    self.port,
                    self.baud_rate,
                    self.model,
                )
                response = _request_status(ser, self._family)
                self.last_frame = response.hex()
                _LOGGER.debug("[get_status] frame: %s", self.last_frame)

                # Address the UPS as the family its frame or refusal names.
                self._family = _named_family(response)
                if not is_frame(response):
                    self._calibration_due = True
                elif self._calibration_due:
                    self.calibration = _read_calibration(ser, self._family)
                    self._calibration_due = False
                    _LOGGER.debug("[get_status] %s", self.calibration)

                parsed = parse_data(response, self.model, self.calibration)
                if parsed:
                    self.last_data = parsed
                _LOGGER.debug("[get_status] data: %s", parsed)
                return parsed
        except Exception as e:
            _LOGGER.warning("[get_status] error: %s", e)
            self._calibration_due = True
            self._family = DEFAULT_FAMILY
            return None
