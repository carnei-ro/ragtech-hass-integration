from .const import DOMAIN, CONF_NAME_KEY


def get_device_info(entry):
    return {
        "identifiers": {(DOMAIN, entry.entry_id)},
        "name": entry.data.get(CONF_NAME_KEY),
        "manufacturer": "Ragtech",
        "model": "UPS",
    }
