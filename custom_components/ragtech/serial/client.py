import logging
import time
from dataclasses import dataclass

import serial

from .models import MODEL_EASY_PRO
from .parser import Calibration, detect_model, is_frame, is_refusal, parse_data

_LOGGER = logging.getLogger(__name__)

# Every request starts with 0xA0 | family; the "Easy" family is 10.
START = 0xAA
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


def read_request(address, count):
    """Build a read request; its checksum covers the address and the count."""
    high, low = address >> 8, address & 0xFF
    return bytes([START, READ, high, low, count, (high + low + count) & 0xFF])


def _read(ser, address, count):
    """Return the raw reply: a start byte plus `count` registers when all is well."""
    ser.reset_input_buffer()
    ser.write(read_request(address, count))
    time.sleep(READ_DELAY)
    return ser.read(count + 1)


def _request_status(ser):
    return _read(ser, *STATUS)


def _read_calibration_range(ser, address, count):
    reply = _read(ser, address, count)
    if len(reply) == count + 1 and reply[0] == START:
        return reply[1:]
    _LOGGER.debug(
        "[calibration] read at 0x%04X %s: %s",
        address,
        "refused" if is_refusal(reply) else "got no usable reply",
        reply.hex(),
    )
    return None


def _read_calibration(ser):
    (current,) = _read_calibration_range(ser, *CURRENT_CALIBRATION) or (None,)
    osc53, osc57 = _read_calibration_range(ser, *FREQUENCY_CALIBRATION) or (None, None)
    return Calibration(current, osc53, osc57)


def probe_ups_model(port: str, baud_rate: int, timeout: int) -> Detection:
    """
    Probe the UPS and match its model code against the model registry.

    Called from the config flow via an executor job.
    """
    try:
        with serial.Serial(port, baud_rate, timeout=timeout) as ser:
            response = _request_status(ser)
    except Exception as exc:
        _LOGGER.debug("[probe_ups_model] serial error: %s", exc)
        return Detection(error=f"Could not open {port}: {exc}")

    if not response:
        return Detection(error=f"No response from UPS on {port}")

    raw_hex = response.hex()
    model = detect_model(response)
    if model is None:
        return Detection(
            error=f"Unrecognised response ({len(response)} bytes): {raw_hex}",
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

    def get_status(self):
        try:
            with serial.Serial(self.port, self.baud_rate, timeout=self.timeout) as ser:
                _LOGGER.debug(
                    "[get_status] requesting status on %s @ %s baud (%s)",
                    self.port,
                    self.baud_rate,
                    self.model,
                )
                response = _request_status(ser)
                self.last_frame = response.hex()
                _LOGGER.debug("[get_status] frame: %s", self.last_frame)

                if not is_frame(response):
                    self._calibration_due = True
                elif self._calibration_due:
                    self.calibration = _read_calibration(ser)
                    self._calibration_due = False
                    _LOGGER.debug("[get_status] %s", self.calibration)

                parsed = parse_data(response, self.model)
                if parsed:
                    self.last_data = parsed
                _LOGGER.debug("[get_status] data: %s", parsed)
                return parsed
        except Exception as e:
            _LOGGER.warning("[get_status] error: %s", e)
            self._calibration_due = True
            return None
