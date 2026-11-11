from contextlib import nullcontext

import pytest

from custom_components.ragtech.serial import client
from custom_components.ragtech.serial.models import (
    MODEL_EASY_PRO,
    MODEL_ONE_UP_2000_NITRO_TI as NITRO_TI,
    UPS_MODELS,
)
from custom_components.ragtech.serial.parser import detect_model, parse_data
from vendor_frames import FRAMES, POST_SWAP, PRE_SWAP

# Senoidal Puro 1200VA, mains OK (issue #27): byte 1 = 0x09, model code 6.
SENOIDAL_FRAMES = [
    bytes.fromhex(h)
    for h in (
        "aa09000c7b0aa54fff00d3c9bc02013688000001828201a33e00bb060e03d0",
        "aa09000c7b0aa54fff00d3ccbc0302368800000182c201a33e00bc060e00d1",
        "aa09000c7b0aa54fff00d3c8ba0302368800000186c201a33e00ba060e00d0",
    )
]
# One UP 2000 Nitro TI, mains OK: byte 1 = 0x21, model code 16.
NITRO_TI_FRAMES = [
    bytes.fromhex(h)
    for h in (
        "aa21000c00000014f300e3c9710e0b30fd00000186c6029a350072100f30c6",
        "aa21000c00000014f300e3c9710d0b30fd00000182c6039a350072100f30c6",
        "aa21000c00000014f500e3cc720f0c2dff0000018286039a350072100f30c8",
        "aa21000c00000014f700e3cb720e0b2dff00000186c6029a350073100f32c8",
    )
]
REAL_FRAMES = [
    pytest.param(f, MODEL_EASY_PRO, id=f"senoidal-{i}")
    for i, f in enumerate(SENOIDAL_FRAMES)
] + [
    pytest.param(f, NITRO_TI, id=f"nitro_ti-{i}") for i, f in enumerate(NITRO_TI_FRAMES)
]
FRAME = SENOIDAL_FRAMES[0]
DECODED_KEYS = (
    "battery.charge",
    "battery.voltage",
    "input.voltage",
    "output.voltage",
    "output.current",
    "ups.load",
    "ups.temperature",
)


def with_byte(frame, index, value):
    data = bytearray(frame)
    data[index] = value
    return bytes(data)


@pytest.mark.parametrize(("frame", "model"), REAL_FRAMES)
def test_real_frames_decode_whatever_byte_1_holds(frame, model):
    flipped = with_byte(frame, 1, 0x21 if frame[1] == 0x09 else 0x09)
    data = parse_data(frame, model)
    assert data is not None
    assert parse_data(flipped, model) == data
    assert detect_model(frame) == model
    assert detect_model(flipped) == model


@pytest.mark.parametrize(
    ("frame", "model", "expected"),
    [
        (FRAME, MODEL_EASY_PRO, (100, 13.49, 198, 115, 0.24, 1, 54)),
        (FRAME, NITRO_TI, (100, 13.49, 199, 115, 0.23, 1, 54)),
        (NITRO_TI_FRAMES[0], NITRO_TI, (95, 13.49, 120, 110, 1.61, 11, 48)),
    ],
    ids=["senoidal-easy_pro", "senoidal-nitro_ti", "nitro_ti-nitro_ti"],
)
def test_known_values(frame, model, expected):
    data = parse_data(frame, model)
    assert tuple(data[key] for key in DECODED_KEYS) == expected


def test_pre_swap_frame_asks_for_a_battery_replacement():
    data = parse_data(PRE_SWAP.frame, NITRO_TI)
    assert data["battery.aged"]
    assert data["battery.capacity_reduced"]
    assert data["ups.status"] == "OL RB"
    assert data["battery.status"] == "FULL"


def test_post_swap_frame_is_healthy_and_still_charging():
    data = parse_data(POST_SWAP.frame, NITRO_TI)
    assert not data["battery.aged"]
    assert not data["battery.capacity_reduced"]
    assert data["ups.status"] == "OL"
    assert data["battery.status"] == "CHARGING"


def test_on_battery_frame_is_discharging():
    on_battery = FRAMES[11]
    data = parse_data(on_battery.frame, NITRO_TI)
    assert data["ups.on_battery"]
    assert data["input.absent"]
    assert data["ups.status"] == "OB"
    assert data["battery.status"] == "DISCHARGING"


def test_input_above_output_does_not_mean_charging():
    data = parse_data(with_byte(POST_SWAP.frame, 8, 0xFF), NITRO_TI)
    assert data["input.voltage"] > data["output.voltage"]
    assert data["ups.status"] == "OL"
    assert data["battery.status"] == "FULL"


@pytest.mark.parametrize(("code", "model"), [(6, MODEL_EASY_PRO), (16, NITRO_TI)])
def test_detect_model_by_code(code, model):
    assert detect_model(with_byte(FRAME, 27, code)) == model


def test_unknown_model_code_is_left_to_the_user():
    frame = with_byte(FRAME, 27, 99)
    assert detect_model(frame) is None
    # Any profile picked manually still decodes the frame.
    for model in UPS_MODELS:
        assert parse_data(frame, model) is not None


@pytest.mark.parametrize(
    "frame",
    [
        b"",
        FRAME[:30],
        with_byte(FRAME, 0, 0xAB),
        b"\x00" + FRAME[:30],
    ],
    ids=["empty", "too_short", "bad_sof", "misaligned"],
)
def test_invalid_frames_rejected(frame):
    for model in UPS_MODELS:
        assert parse_data(frame, model) is None
    assert detect_model(frame) is None


class FakeSerial:
    def __init__(self, response):
        self.response = response
        self.calls = []

    def reset_input_buffer(self):
        self.calls.append("reset_input_buffer")

    def write(self, data):
        self.calls.append(("write", data))

    def read(self, size):
        self.calls.append(("read", size))
        return self.response[:size]


@pytest.fixture
def fake_serial(monkeypatch):
    monkeypatch.setattr(client, "READ_DELAY", 0)

    def install(response):
        port = FakeSerial(response)
        monkeypatch.setattr(
            client.serial, "Serial", lambda *_a, **_kw: nullcontext(port)
        )
        return port

    return install


EXPECTED_CALLS = [
    "reset_input_buffer",
    ("write", bytes.fromhex("AA0400801E9E")),
    ("read", 31),
]


@pytest.mark.parametrize("model", [MODEL_EASY_PRO, NITRO_TI])
def test_get_status_reads_one_31_byte_frame(fake_serial, model):
    port = fake_serial(FRAME)
    ups = client.RagtechSerialClient("/dev/null", 2560, 5, model=model)
    assert ups.get_status() == parse_data(FRAME, model)
    assert port.calls == EXPECTED_CALLS


@pytest.mark.parametrize(
    ("frame", "model"),
    [(FRAME, MODEL_EASY_PRO), (NITRO_TI_FRAMES[0], NITRO_TI)],
    ids=["senoidal", "nitro_ti"],
)
def test_probe_detects_model(fake_serial, frame, model):
    port = fake_serial(frame)
    detection = client.probe_ups_model("/dev/null", 2560, 5)
    assert detection.model == model
    assert detection.error is None
    assert port.calls == EXPECTED_CALLS


def test_probe_unknown_model_falls_back_to_manual_pick(fake_serial):
    frame = with_byte(FRAME, 27, 99)
    fake_serial(frame)
    detection = client.probe_ups_model("/dev/null", 2560, 5)
    assert detection.model is None
    assert detection.error == f"Unrecognised response (31 bytes): {frame.hex()}"
    assert detection.raw_hex == frame.hex()
