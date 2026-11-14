from ..serial.models import UPS_MODELS
from .const import DOMAIN, CONF_NAME_KEY, CONF_MODEL_KEY, CONF_MODEL_DEFAULT_VALUE


def get_device_info(entry):
    merged = {**entry.data, **(entry.options or {})}
    model = UPS_MODELS.get(merged.get(CONF_MODEL_KEY, CONF_MODEL_DEFAULT_VALUE))
    return {
        "identifiers": {(DOMAIN, entry.entry_id)},
        "name": entry.data.get(CONF_NAME_KEY),
        "manufacturer": "Ragtech",
        "model": model.label if model else "UPS",
    }
