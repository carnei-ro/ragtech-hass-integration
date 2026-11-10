import pytest

from custom_components.ragtech.serial.models import (
    MODEL_EASY_PRO,
    MODEL_ONE_UP_2000_NITRO_TI as NITRO_TI,
)
from custom_components.ragtech.serial.parser import detect_model, parse_data

# Real One UP 2000 Nitro TI frames (mains OK), captured 2026-11-10.
NITRO_TI_FRAMES = [
    bytes.fromhex(h)
    for h in (
        "aa21000c00000014f300e3c9710e0b30fd00000186c6029a350072100f30c6",
        "aa21000c00000014f300e3c9710d0b30fd00000182c6039a350072100f30c6",
        "aa21000c00000014f500e3cc720f0c2dff0000018286039a350072100f30c8",
        "aa21000c00000014f700e3cb720e0b2dff00000186c6029a350073100f32c8",
    )
]
NITRO_TI_FRAME = NITRO_TI_FRAMES[0]
# Synthetic: no real Easy Pro capture is available.
EASY_PRO_FRAME = NITRO_TI_FRAME.ljust(64, b"\x00")


def with_byte(frame, index, value):
    data = bytearray(frame)
    data[index] = value
    return bytes(data)


@pytest.mark.parametrize("frame", NITRO_TI_FRAMES, ids=["f1", "f2", "f3", "f4"])
def test_nitro_ti_real_frames_parse(frame):
    assert parse_data(frame, NITRO_TI) is not None
    assert detect_model(frame) == NITRO_TI


def test_nitro_ti_decodes_known_values():
    data = parse_data(NITRO_TI_FRAME, NITRO_TI)
    assert data["battery.charge"] == 95
    assert data["battery.voltage"] == 13.49
    assert data["input.voltage"] == 120
    assert data["output.current"] == 1.61
    assert data["ups.load"] == 11
    assert data["ups.temperature"] == 48
    assert data["input.frequency"] == 58.89
    assert data["output.voltage"] == 110


def test_byte_1_is_data_not_header():
    # Pre-battery-swap frames had 0x09 here; values must not depend on it.
    old_style = with_byte(NITRO_TI_FRAME, 1, 0x09)
    assert parse_data(old_style, NITRO_TI) == parse_data(NITRO_TI_FRAME, NITRO_TI)
    assert detect_model(old_style) == NITRO_TI


@pytest.mark.parametrize(
    "frame",
    [
        b"",
        NITRO_TI_FRAME[:30],
        with_byte(NITRO_TI_FRAME, 0, 0xAB),
        b"\x00" + NITRO_TI_FRAME[:30],
    ],
    ids=["empty", "too_short", "bad_sof", "misaligned"],
)
def test_invalid_frames_rejected(frame):
    assert parse_data(frame, NITRO_TI) is None
    assert parse_data(frame, MODEL_EASY_PRO) is None
    assert detect_model(frame) is None


def test_unknown_model_code_not_detected():
    assert detect_model(with_byte(NITRO_TI_FRAME, 27, 0x06)) is None


def test_easy_pro_frame():
    data = parse_data(EASY_PRO_FRAME, MODEL_EASY_PRO)
    assert data["battery.charge"] == 95
    assert data["input.voltage"] == 121
    assert data["output.voltage"] == 110
    assert detect_model(EASY_PRO_FRAME) == MODEL_EASY_PRO
    assert parse_data(with_byte(EASY_PRO_FRAME, 1, 0x09), MODEL_EASY_PRO) == data


def test_easy_pro_still_requires_64_bytes():
    assert parse_data(NITRO_TI_FRAME, MODEL_EASY_PRO) is None
