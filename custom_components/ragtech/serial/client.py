import logging
import time
from dataclasses import dataclass

import serial

from .models import MODEL_EASY_PRO, UPS_MODELS
from .parser import parse_data

_LOGGER = logging.getLogger(__name__)

# Command that asks the UPS for its current status. All known Ragtech models
# respond to the same request.
REQUEST_COMMAND = bytes.fromhex("AA0400801E9E")
# The UPS needs a short moment to answer after receiving the request.
READ_DELAY = 2

_HEADER_TO_MODEL = {profile["header"]: key for key, profile in UPS_MODELS.items()}
_PROBE_READ_LEN = max(profile["response_length"] for profile in UPS_MODELS.values())


@dataclass
class Detection:
    model: str | None = None
    error: str | None = None
    raw_hex: str | None = None


def probe_ups_model(port: str, baud_rate: int, timeout: int) -> Detection:
    """Open the port, ask the UPS to talk, and match its header against
    the model registry. Called from the config flow via an executor job.
    """
    try:
        with serial.Serial(port, baud_rate, timeout=timeout) as ser:
            ser.write(REQUEST_COMMAND)
            time.sleep(READ_DELAY)
            response = ser.read(_PROBE_READ_LEN)
    except Exception as exc:
        _LOGGER.debug("[probe_ups_model] serial error: %s", exc)
        return Detection(error=f"Could not open {port}: {exc}")

    if not response:
        return Detection(error=f"No response from UPS on {port}")

    raw_hex = response.hex()
    header = raw_hex[:4]
    model = _HEADER_TO_MODEL.get(header)
    if model is None:
        return Detection(
            error=f"Unknown response header '{header}' (full response: {raw_hex})",
            raw_hex=raw_hex,
        )
    return Detection(model=model, raw_hex=raw_hex)


class RagtechSerialClient:
    def __init__(self, port: str, baud_rate: int, timeout: int, model: str = MODEL_EASY_PRO):
        self.port = port
        self.baud_rate = baud_rate
        self.timeout = timeout
        self.model = model
        profile = UPS_MODELS.get(model, UPS_MODELS[MODEL_EASY_PRO])
        self._response_length = profile["response_length"]
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
                ser.write(REQUEST_COMMAND)
                time.sleep(READ_DELAY)
                response = ser.read(self._response_length)

                parsed = parse_data(response, self.model)
                if parsed:
                    self.last_data = parsed
                _LOGGER.debug("[get_status] data: %s", parsed)
                return parsed
        except Exception as e:
            _LOGGER.warning("[get_status] error: %s", e)
            return None
