import logging
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

STATUS, CURRENT, OSCILLATOR = 0x0080, 0x00F3, 0x0202
# The calibration the frame fixtures assume.
REGISTERS = {0x00F3: 69, 0x0202: 100, 0x0203: 72}
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


def test_requests_carry_the_family_in_their_start_byte():
    assert client.read_request(0x0080, 30, 13) == bytes.fromhex("AD0400801E9E")


def test_calibration_is_read_once_at_setup():
    with FakeUps([POST_SWAP.frame], REGISTERS) as ups:
        ragtech = connect(ups)
        for _ in range(3):
            data = ragtech.get_status()
            assert data["output.current"] == POST_SWAP.output_current
            assert data["output.frequency"] == POST_SWAP.output_frequency
        assert ragtech.calibration == Calibration(69, 100, 72)
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
        ups.registers[CURRENT] = 138
        assert ragtech.get_status() is not None
        data = ragtech.get_status()
        assert (ups.reads(CURRENT), ups.reads(OSCILLATOR)) == (2, 2)
        assert ragtech.calibration == Calibration(138, 100, 72)
        # Twice the calibration byte halves the current: 1.62 A became 0.81 A.
        assert data["output.current"] == 0.81


def test_refused_read_leaves_that_calibration_unknown(caplog):
    with FakeUps([POST_SWAP.frame], REGISTERS, replies={CURRENT: REFUSAL}) as ups:
        ragtech = connect(ups)
        data = ragtech.get_status()
        assert ragtech.calibration == Calibration(None, 100, 72)
        assert "read at 0x00F3 refused by the UPS (ca)" in caplog.text
        assert data["output.current"] is None
        assert data["output.apower"] is None
        assert data["output.power"] == 154.0
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
        assert ragtech.calibration == Calibration(69, None, None)
        assert data["output.frequency"] is None
        assert data["output.current"] == POST_SWAP.output_current


def test_unanswered_calibration_leaves_both_unknown(caplog):
    with FakeUps([POST_SWAP.frame]) as ups:
        ups.replies = {CURRENT: b"", OSCILLATOR: b""}
        ragtech = connect(ups)
        data = ragtech.get_status()
        assert ragtech.calibration == Calibration()
        assert "read at 0x0202 got no usable reply (nothing received)" in caplog.text
        assert data["output.current"] is None
        assert data["output.frequency"] is None
        assert data["battery.voltage"] == POST_SWAP.battery_voltage


def test_refused_status_read_is_a_failed_poll(caplog):
    caplog.set_level(logging.DEBUG)
    with FakeUps([POST_SWAP.frame], REGISTERS, replies={STATUS: REFUSAL}) as ups:
        ragtech = connect(ups)
        assert ragtech.get_status() is None
        assert ragtech.last_frame == "ca"
        assert "(family 10) refused the request: ca" in caplog.text
        assert ups.reads(CURRENT) == 0

        del ups.replies[STATUS]
        assert ragtech.get_status() is not None
        assert ups.reads(CURRENT) == 1


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


def hex_requests(ups):
    return [request.hex() for request in ups.requests]


def test_family_13_unit_is_addressed_with_its_own_start_byte():
    with FakeUps([POST_SWAP.frame], REGISTERS, family=13) as ups:
        ragtech = connect(ups)
        # The first request assumes family 10 and is refused with 0xCD.
        assert ragtech.get_status() is None
        assert ragtech.last_frame == "cd"

        data = ragtech.get_status()
        assert ragtech.last_frame.startswith("ad")
        assert data["battery.voltage"] == POST_SWAP.battery_voltage
        assert data["output.current"] == POST_SWAP.output_current
        assert ragtech.get_status() == data
        assert hex_requests(ups) == [
            "aa0400801e9e",
            "ad0400801e9e",
            "ad0400f301f4",
            "ad0402020206",
            "ad0400801e9e",
        ]


def test_probe_follows_a_family_13_refusal():
    with FakeUps([POST_SWAP.frame], family=13) as ups:
        detection = client.probe_ups_model(ups.port, 2560, 0.3)
        assert detection.model == MODEL_ONE_UP_2000_NITRO_TI
        assert hex_requests(ups) == ["aa0400801e9e", "ad0400801e9e"]


def test_stray_refusal_does_not_strand_a_family_10_unit():
    with FakeUps([POST_SWAP.frame], REGISTERS, replies={STATUS: b"\xcd"}) as ups:
        ragtech = connect(ups)
        assert ragtech.get_status() is None

        # The family-13 request that follows is refused by the family-10 unit.
        del ups.replies[STATUS]
        assert ragtech.get_status() is None
        assert ragtech.last_frame == "ca"
        assert ragtech.get_status() is not None
        assert [request[0] for request in ups.requests[:3]] == [0xAA, 0xAD, 0xAA]


def test_silence_falls_back_to_the_default_family():
    with FakeUps([POST_SWAP.frame], REGISTERS, family=13) as ups:
        ragtech = connect(ups)
        ragtech.get_status()
        assert ragtech.get_status() is not None

        ups.silent = True
        assert ragtech.get_status() is None
        ups.silent = False
        assert ragtech.get_status() is None
        assert ragtech.get_status() is not None
        assert [request[0] for request in ups.requests[-5:]] == [
            0xAD,
            0xAA,
            0xAD,
            0xAD,
            0xAD,
        ]
        assert {request[1] for request in ups.requests} == {0x04}
