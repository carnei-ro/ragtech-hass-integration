from .utils.const import DOMAIN


async def async_get_config_entry_diagnostics(hass, entry):
    client = hass.data[DOMAIN][entry.entry_id]["client"]
    return {
        "config": {**entry.data, **entry.options},
        "last_frame": client.last_frame,
        "calibration": client.calibration._asdict(),
        "data": client.last_data,
    }
