import logging
import time
from dataclasses import dataclass

import serial

from .models import MODEL_EASY_PRO
from .parser import detect_model, parse_data

_LOGGER = logging.getLogger(__name__)

# Command that asks the UPS for its current status. All known Ragtech models
# respond to the same request.
REQUEST_COMMAND = bytes.fromhex("AA0400801E9E")
# The answer is a start-of-frame byte plus the 30 registers requested above.
RESPONSE_LENGTH = 31
# The UPS needs a short moment to answer after receiving the request.
READ_DELAY = 2


@dataclass
class Detection:
    model: str | None = None
    error: str | None = None
    raw_hex: str | None = None


def _request_status(ser):
    ser.reset_input_buffer()
    ser.write(REQUEST_COMMAND)
    time.sleep(READ_DELAY)
    return ser.read(RESPONSE_LENGTH)


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

                parsed = parse_data(response, self.model)
                if parsed:
                    self.last_data = parsed
                _LOGGER.debug("[get_status] data: %s", parsed)
                return parsed
        except Exception as e:
            _LOGGER.warning("[get_status] error: %s", e)
            return None
