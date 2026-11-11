"""
Model table for Ragtech's "Easy" UPS family (family 10).

The UPS reports its model code in status frame byte 27 (register 0x9A). Each
row holds the per-model factors Ragtech's own software applies. Even codes are
"TI" units (115 V output), odd codes "M2" units (220 V output); codes 0-7 run
on a 12 V battery, codes 8-19 on 24 V.

The parser, client and config flow all derive their behaviour from this table.
"""

from typing import NamedTuple


class UpsModel(NamedTuple):
    code: int
    label: str
    # Volts per count of register 0x8A.
    battery_voltage_scale: float
    # Volts per count of register 0x9D.
    output_voltage_scale: float
    # Amps per count of register 0x8C, before dividing by the unit's
    # calibration register 0x00F3.
    output_current_factor: float


_FAMILY_10 = (
    UpsModel(0, "600 VA TI", 0.067, 0.555, 3.2),
    UpsModel(1, "600 VA M2", 0.067, 1.03, 1.7),
    # Ragtech's software applies 4.3; its model list alone would suggest 3.2.
    UpsModel(2, "700 VA TI", 0.067, 0.555, 4.3),
    UpsModel(3, "700 VA M2", 0.067, 1.03, 2.3),
    UpsModel(4, "900 VA TI", 0.067, 0.555, 4.94),
    UpsModel(5, "900 VA M2", 0.067, 1.03, 2.64),
    # 1200 VA TI; the Senoidal Puro 1200 reports this code too.
    UpsModel(6, "Easy Pro", 0.067, 0.555, 6.37),
    UpsModel(7, "1200 VA M2", 0.067, 1.03, 3.41),
    UpsModel(8, "1300 VA TI", 0.134, 0.555, 9.56),
    UpsModel(9, "1300 VA M2", 0.134, 1.03, 5.11),
    UpsModel(10, "1400 VA TI", 0.134, 0.555, 11.15),
    UpsModel(11, "1400 VA M2", 0.134, 1.03, 5.96),
    UpsModel(12, "1600 VA TI", 0.134, 0.555, 12.8),
    UpsModel(13, "1600 VA M2", 0.134, 1.03, 6.8),
    UpsModel(14, "1800 VA TI", 0.134, 0.555, 14.4),
    UpsModel(15, "1800 VA M2", 0.134, 1.03, 7.65),
    # 2000 VA TI; the NitroUp 2000 and Easy 2000 TI report this code too.
    UpsModel(16, "One UP 2000 Nitro TI", 0.134, 0.555, 15.93),
    UpsModel(17, "2000 VA M2", 0.134, 1.03, 8.52),
    UpsModel(18, "2200 VA TI", 0.134, 0.555, 17.52),
    UpsModel(19, "2200 VA M2", 0.134, 1.03, 9.37),
)

MODEL_EASY_PRO = "easy_pro"
MODEL_ONE_UP_2000_NITRO_TI = "one_up_2000_nitro_ti"

# Codes 6 and 16 keep the keys earlier releases stored in config entries.
_STORED_KEYS = {6: MODEL_EASY_PRO, 16: MODEL_ONE_UP_2000_NITRO_TI}

# Model key (the value a config entry stores) -> model.
UPS_MODELS = {
    _STORED_KEYS.get(model.code, f"model_{model.code}"): model for model in _FAMILY_10
}
