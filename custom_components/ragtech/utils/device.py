from ..serial.models import UPS_MODELS
from .const import DOMAIN, CONF_NAME_KEY, CONF_MODEL_KEY, CONF_MODEL_DEFAULT_VALUE


def get_device_info(entry):
    merged = {**entry.data, **(entry.options or {})}
    model_key = merged.get(CONF_MODEL_KEY, CONF_MODEL_DEFAULT_VALUE)
    model_label = UPS_MODELS.get(model_key, {}).get("label", "UPS")
    return {
        "identifiers": {(DOMAIN, entry.entry_id)},
        "name": entry.data.get(CONF_NAME_KEY),
        "manufacturer": "Ragtech",
        "model": model_label,
    }
