import logging
import time

import serial

from .parser import parse_data

_LOGGER = logging.getLogger(__name__)

# Command that asks the UPS for its current status.
REQUEST_COMMAND = bytes.fromhex("AA0400801E9E")
# Number of bytes the UPS sends back in a status response.
RESPONSE_LENGTH = 64
# The UPS needs a short moment to answer after receiving the request.
READ_DELAY = 2


class RagtechSerialClient:
    def __init__(self, port: str, baud_rate: int, timeout: int):
        self.port = port
        self.baud_rate = baud_rate
        self.timeout = timeout
        self.last_data = None

    def get_status(self):
        try:
            with serial.Serial(self.port, self.baud_rate, timeout=self.timeout) as ser:
                _LOGGER.debug(
                    "[get_status] requesting status on %s @ %s baud",
                    self.port,
                    self.baud_rate,
                )
                ser.write(REQUEST_COMMAND)
                time.sleep(READ_DELAY)
                response = ser.read(RESPONSE_LENGTH)

                parsed = parse_data(response)
                if parsed:
                    self.last_data = parsed
                _LOGGER.debug("[get_status] data: %s", parsed)
                return parsed
        except Exception as e:
            _LOGGER.warning("[get_status] error: %s", e)
            return None
