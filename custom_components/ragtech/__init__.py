from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from .serial.client import RagtechSerialClient
from .serial.client_manager import RagtechSerialClientManager
from .utils.const import (
    DOMAIN,
    CONF_SERIAL_PORT_KEY,
    CONF_SERIAL_PORT_DEFAULT_VALUE,
    CONF_BAUD_RATE_KEY,
    CONF_BAUD_RATE_DEFAULT_VALUE,
    CONF_TIMEOUT_KEY,
    CONF_TIMEOUT_DEFAULT_VALUE,
    CONF_POLLING_INTERVAL_KEY,
    CONF_POLLING_INTERVAL_DEFAULT_VALUE,
)

PLATFORMS = ["sensor"]


async def async_setup(_hass, _config):
    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry):
    config = {**entry.data, **entry.options}

    serial_port = config.get(CONF_SERIAL_PORT_KEY, CONF_SERIAL_PORT_DEFAULT_VALUE)
    baud_rate = config.get(CONF_BAUD_RATE_KEY, CONF_BAUD_RATE_DEFAULT_VALUE)
    timeout = config.get(CONF_TIMEOUT_KEY, CONF_TIMEOUT_DEFAULT_VALUE)
    polling_interval = config.get(
        CONF_POLLING_INTERVAL_KEY, CONF_POLLING_INTERVAL_DEFAULT_VALUE
    )

    client = RagtechSerialClient(serial_port, baud_rate, timeout)
    manager = RagtechSerialClientManager(client, polling_interval)
    manager.start(hass)

    if DOMAIN not in hass.data:
        hass.data[DOMAIN] = {}
    hass.data[DOMAIN][entry.entry_id] = {
        "client": client,
        "manager": manager,
    }

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    entry.async_on_unload(entry.add_update_listener(async_reload_entry))

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry):
    unloaded = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unloaded:
        data = hass.data[DOMAIN].pop(entry.entry_id, None)
        if data and data.get("manager"):
            data["manager"].stop()
    return unloaded


async def async_reload_entry(hass: HomeAssistant, entry: ConfigEntry):
    await hass.config_entries.async_reload(entry.entry_id)
