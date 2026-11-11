import sys

import pytest

from custom_components.ragtech.serial import client
from custom_components.ragtech.serial.models import MODEL_ONE_UP_2000_NITRO_TI
from custom_components.ragtech.serial.parser import Calibration
from fake_ups import FakeUps
from vendor_frames import POST_SWAP

pytestmark = pytest.mark.skipif(
    not sys.platform.startswith("linux"), reason="needs a Linux pseudo-terminal"
)

CURRENT, OSCILLATOR = 0x00F3, 0x0202
# Made-up calibration values: no unit's real ones are known yet.
REGISTERS = {0x00F3: 138, 0x0202: 100, 0x0203: 72}
REFUSAL = b"\xca"


@pytest.fixture(autouse=True)
def no_read_delay(monkeypatch):
    monkeypatch.setattr(client, "READ_DELAY", 0)


def connect(ups):
    return client.RagtechSerialClient(
        ups.port, 2560, 0.3, model=MODEL_ONE_UP_2000_NITRO_TI
    )


@pytest.mark.parametrize(
    ("address", "count", "request_hex"),
    [
        (0x0080, 30, "AA0400801E9E"),
        (0x00F3, 1, "AA0400F301F4"),
        (0x0202, 2, "AA0402020206"),
        (0x0136, 1, "AA0401360138"),
    ],
)
def test_read_requests_match_the_vendor_transport(address, count, request_hex):
    assert client.read_request(address, count) == bytes.fromhex(request_hex)


def test_calibration_is_read_once_at_setup():
    with FakeUps([POST_SWAP.frame], REGISTERS) as ups:
        ragtech = connect(ups)
        for _ in range(3):
            data = ragtech.get_status()
            assert data["output.current"] == POST_SWAP.output_current
            assert data["output.frequency"] == POST_SWAP.output_frequency
        assert ragtech.calibration == Calibration(138, 100, 72)
        assert ups.requests == [
            bytes.fromhex(request)
            for request in (
                "AA0400801E9E",
                "AA0400F301F4",
                "AA0402020206",
                "AA0400801E9E",
                "AA0400801E9E",
            )
        ]


def test_calibration_is_read_again_after_a_failed_poll_streak():
    with FakeUps([POST_SWAP.frame], REGISTERS) as ups:
        ragtech = connect(ups)
        assert ragtech.get_status() is not None

        ups.silent = True
        assert ragtech.get_status() is None
        assert ragtech.get_status() is None
        assert (ups.reads(CURRENT), ups.reads(OSCILLATOR)) == (1, 1)

        ups.silent = False
        ups.registers[CURRENT] = 69
        assert ragtech.get_status() is not None
        data = ragtech.get_status()
        assert (ups.reads(CURRENT), ups.reads(OSCILLATOR)) == (2, 2)
        assert ragtech.calibration == Calibration(69, 100, 72)
        # Half the calibration byte doubles the current: 1.62 A became 3.23 A.
        assert data["output.current"] == 3.23


def test_refused_read_leaves_that_calibration_unknown():
    with FakeUps([POST_SWAP.frame], REGISTERS, replies={CURRENT: REFUSAL}) as ups:
        ragtech = connect(ups)
        data = ragtech.get_status()
        assert ragtech.calibration == Calibration(None, 100, 72)
        assert data["output.current"] is None
        assert data["output.power"] is None
        assert data["output.frequency"] == POST_SWAP.output_frequency
        assert data["output.voltage"] == 110
        # A refusal is not retried until the link has failed.
        assert ragtech.get_status() == data
        assert (ups.reads(CURRENT), ups.reads(OSCILLATOR)) == (1, 1)


def test_short_reply_leaves_that_calibration_unknown():
    with FakeUps(
        [POST_SWAP.frame], REGISTERS, replies={OSCILLATOR: b"\xaa\x64"}
    ) as ups:
        ragtech = connect(ups)
        data = ragtech.get_status()
        assert ragtech.calibration == Calibration(138, None, None)
        assert data["output.frequency"] is None
        assert data["output.current"] == POST_SWAP.output_current


def test_unanswered_calibration_leaves_both_unknown():
    with FakeUps([POST_SWAP.frame]) as ups:
        ups.replies = {CURRENT: b"", OSCILLATOR: b""}
        ragtech = connect(ups)
        data = ragtech.get_status()
        assert ragtech.calibration == Calibration()
        assert data["output.current"] is None
        assert data["output.frequency"] is None
        assert data["battery.voltage"] == POST_SWAP.battery_voltage


def test_only_read_requests_reach_the_ups():
    with FakeUps([POST_SWAP.frame], REGISTERS) as ups:
        ragtech = connect(ups)
        ragtech.get_status()
        ups.silent = True
        ragtech.get_status()
        ups.silent = False
        ragtech.get_status()
        assert client.probe_ups_model(ups.port, 2560, 0.3).model is not None
        assert len(ups.requests) == 8
        assert {request[1] for request in ups.requests} == {0x04}
