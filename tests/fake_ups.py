"""
Offline Ragtech UPS on a pseudo-terminal, for serial-level tests.

It speaks the wire protocol of the "Easy" families:

  request : start, opcode, addr_hi, addr_lo, value, checksum
            start = 0xA0 | family, checksum = (addr_hi + addr_lo + value) & 0xFF
  04 read : reply start + <value> registers
  refusal : a lone 0xC0 | family byte, sent for a wrong start byte or checksum
            and for every opcode other than read

Simulator assumptions, not firmware facts: unmapped registers read 0x00, and a
real unit may treat a wrong start byte differently.
"""

import os
import select
import threading
import tty

REQUEST_LENGTH = 6
READ = 0x04
STATUS_ADDRESS = 0x0080


class FakeUps:
    def __init__(self, frames, registers=None, family=10, replies=None):
        # Status frames (start byte + 30 registers), served in turn.
        self.frames = list(frames)
        # Registers outside the status range: {address: value}.
        self.registers = dict(registers or {})
        self.family = family
        # Scripted raw replies to reads: {address: bytes}.
        self.replies = dict(replies or {})
        # While set, requests are dropped as if the UPS were unplugged.
        self.silent = False
        # Every request received, in order.
        self.requests = []
        self._status_reads = 0

    def __enter__(self):
        """Open the pseudo-terminal and start answering."""
        self._master, self._slave = os.openpty()
        tty.setraw(self._slave)
        self.port = os.ttyname(self._slave)
        self._stop = threading.Event()
        self._thread = threading.Thread(target=self._serve, daemon=True)
        self._thread.start()
        return self

    def __exit__(self, *_exc: object):
        """Stop answering and close the pseudo-terminal."""
        self._stop.set()
        self._thread.join()
        os.close(self._master)
        os.close(self._slave)

    def reads(self, address):
        """Return how many read requests named this address."""
        return sum(
            request[1] == READ and request[2:4] == address.to_bytes(2, "big")
            for request in self.requests
        )

    def _serve(self):
        buffer = b""
        while not self._stop.is_set():
            readable, _, _ = select.select([self._master], [], [], 0.02)
            if not readable:
                continue
            buffer += os.read(self._master, 64)
            while len(buffer) >= REQUEST_LENGTH:
                request, buffer = buffer[:REQUEST_LENGTH], buffer[REQUEST_LENGTH:]
                self.requests.append(request)
                if not self.silent:
                    os.write(self._master, self._reply(request))

    def _reply(self, request):
        start, opcode, high, low, value, checksum = request
        address = (high << 8) | low
        if (
            start != 0xA0 | self.family
            or checksum != (high + low + value) & 0xFF
            or opcode != READ
        ):
            return bytes([0xC0 | self.family])
        if address in self.replies:
            return self.replies[address]
        memory = dict(self.registers)
        if address == STATUS_ADDRESS:
            frame = self.frames[self._status_reads % len(self.frames)]
            self._status_reads += 1
            memory.update(
                {STATUS_ADDRESS + i: byte for i, byte in enumerate(frame[1:])}
            )
        return bytes(
            [0xA0 | self.family, *(memory.get(address + i, 0) for i in range(value))]
        )
