import pytest

from custom_components.ragtech.serial.models import (
    MODEL_EASY_PRO,
    MODEL_ONE_UP_2000_NITRO_TI,
    UPS_MODELS,
)
from custom_components.ragtech.serial.parser import (
    Calibration,
    decode_frame,
    detect_model,
    parse_data,
)
from custom_components.ragtech.utils.const import CONF_MODEL_DEFAULT_VALUE
from vendor_frames import CALIBRATION, FRAMES, POST_SWAP

NITRO_TI = UPS_MODELS[MODEL_ONE_UP_2000_NITRO_TI]
# Keys that need the UPS's calibration registers.
CALIBRATED_KEYS = (
    "input.current",
    "input.frequency",
    "output.current",
    "output.power",
    "output.apower",
)

# Output current factors as the research report groups them: model codes -> factors.
CURRENT_FACTORS = {
    (0, 2, 4, 6): (3.2, 4.3, 4.94, 6.37),
    (1, 3, 5, 7): (1.7, 2.3, 2.64, 3.41),
    (8, 10, 12, 14, 16, 18): (9.56, 11.15, 12.8, 14.4, 15.93, 17.52),
    (9, 11, 13, 15, 17, 19): (5.11, 5.96, 6.8, 7.65, 8.52, 9.37),
}


@pytest.mark.parametrize("vendor", FRAMES, ids=lambda vendor: vendor.frame_hex)
def test_frames_decode_like_the_vendor(vendor):
    key = detect_model(vendor.frame)
    model = UPS_MODELS[key]
    assert model.code == vendor.model

    values = decode_frame(vendor.frame, model, Calibration(*CALIBRATION))
    assert values["battery_voltage"] == pytest.approx(vendor.battery_voltage, abs=0.005)
    assert values["battery_charge"] == pytest.approx(
        min(vendor.battery_charge, 100), abs=0.05
    )
    assert values["input_voltage"] == pytest.approx(vendor.input_voltage, abs=0.05)
    assert values["output_voltage"] == pytest.approx(vendor.output_voltage, abs=0.05)
    assert values["load"] == vendor.load
    assert values["temperature"] == vendor.temperature
    assert values["output_current"] == pytest.approx(vendor.output_current, abs=0.005)
    assert values["output_frequency"] == pytest.approx(
        vendor.output_frequency, abs=0.005
    )

    data = parse_data(vendor.frame, key)
    assert data["battery.voltage"] == vendor.battery_voltage
    assert data["ups.model_code"] == vendor.model
    assert data["ups.firmware"] == vendor.firmware


def test_table_holds_the_twenty_family_10_models():
    models = {model.code: model for model in UPS_MODELS.values()}
    assert sorted(models) == list(range(20))
    for code, model in models.items():
        assert model.battery_voltage_scale == (0.067 if code < 8 else 0.134)
        assert model.output_voltage_scale == (1.03 if code % 2 else 0.555)
    for codes, factors in CURRENT_FACTORS.items():
        assert tuple(models[code].output_current_factor for code in codes) == factors


def test_stored_model_keys_still_select_codes_6_and_16():
    assert (MODEL_EASY_PRO, MODEL_ONE_UP_2000_NITRO_TI) == (
        "easy_pro",
        "one_up_2000_nitro_ti",
    )
    assert CONF_MODEL_DEFAULT_VALUE == "easy_pro"
    assert UPS_MODELS["easy_pro"].code == 6
    assert UPS_MODELS["easy_pro"].label == "Easy Pro"
    assert UPS_MODELS["one_up_2000_nitro_ti"].code == 16
    assert UPS_MODELS["one_up_2000_nitro_ti"].label == "One UP 2000 Nitro TI"


def test_stored_nitro_key_now_reports_the_pack_voltage():
    data = parse_data(POST_SWAP.frame, "one_up_2000_nitro_ti")
    assert data["battery.voltage"] == 26.93


def test_manual_model_choice_overrides_the_reported_code():
    assert POST_SWAP.model == 16
    assert parse_data(POST_SWAP.frame, "easy_pro")["battery.voltage"] == 13.47
    assert parse_data(POST_SWAP.frame, "model_17")["output.voltage"] == 204


def test_current_and_frequency_need_the_calibration_registers():
    data = parse_data(POST_SWAP.frame, MODEL_ONE_UP_2000_NITRO_TI)
    assert [data[key] for key in CALIBRATED_KEYS] == [None] * len(CALIBRATED_KEYS)
    assert data["output.voltage"] == 110

    data = parse_data(
        POST_SWAP.frame, MODEL_ONE_UP_2000_NITRO_TI, Calibration(*CALIBRATION)
    )
    assert None not in [data[key] for key in CALIBRATED_KEYS]
    assert data["output.current"] == 1.62
    assert data["input.frequency"] == 60.02


@pytest.mark.parametrize("current", [None, 0])
def test_current_is_unknown_without_a_usable_calibration_byte(current):
    values = decode_frame(POST_SWAP.frame, NITRO_TI, Calibration(current, 100, 72))
    assert values["output_current"] is None
    assert values["output_frequency"] is not None


@pytest.mark.parametrize(
    ("osc53", "osc57"), [(None, None), (100, None), (0, 0), (100, 100)]
)
def test_frequency_is_unknown_without_two_distinct_marks(osc53, osc57):
    values = decode_frame(POST_SWAP.frame, NITRO_TI, Calibration(138, osc53, osc57))
    assert values["output_frequency"] is None
    assert values["output_current"] is not None
