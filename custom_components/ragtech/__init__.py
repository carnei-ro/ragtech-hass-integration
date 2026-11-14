from __future__ import annotations

from typing import TYPE_CHECKING

from homeassistant.exceptions import ConfigEntryNotReady
from homeassistant.helpers import config_validation as cv, entity_registry as er

from .serial.client import RagtechSerialClient
from .serial.client_manager import RagtechSerialClientManager
from .utils.migration import migrated_unique_id
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
    CONF_MODEL_KEY,
    CONF_MODEL_DEFAULT_VALUE,
)

if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant
    from homeassistant.config_entries import ConfigEntry

PLATFORMS = ["sensor", "binary_sensor"]

# This integration is configured exclusively through config entries (UI).
CONFIG_SCHEMA = cv.config_entry_only_config_schema(DOMAIN)


async def _async_migrate_unique_ids(hass: HomeAssistant, entry: ConfigEntry):
    registry = er.async_get(hass)

    def migrate(entity):
        unique_id = migrated_unique_id(entity.unique_id)
        # Leave the entity alone if its new unique id is already taken.
        if unique_id is None or registry.async_get_entity_id(
            entity.domain, entity.platform, unique_id
        ):
            return None
        return {"new_unique_id": unique_id}

    await er.async_migrate_entries(hass, entry.entry_id, migrate)


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry):
    config = {**entry.data, **entry.options}

    serial_port = config.get(CONF_SERIAL_PORT_KEY, CONF_SERIAL_PORT_DEFAULT_VALUE)
    baud_rate = config.get(CONF_BAUD_RATE_KEY, CONF_BAUD_RATE_DEFAULT_VALUE)
    timeout = config.get(CONF_TIMEOUT_KEY, CONF_TIMEOUT_DEFAULT_VALUE)
    polling_interval = config.get(
        CONF_POLLING_INTERVAL_KEY, CONF_POLLING_INTERVAL_DEFAULT_VALUE
    )
    model = config.get(CONF_MODEL_KEY, CONF_MODEL_DEFAULT_VALUE)

    client = RagtechSerialClient(serial_port, baud_rate, timeout, model=model)
    manager = RagtechSerialClientManager(client, polling_interval)

    # Entities are built from the first status frame: without one, let Home
    # Assistant retry the setup rather than load an entry with no entities.
    if not await manager.get_status():
        msg = f"No status frame from the UPS on {serial_port}"
        raise ConfigEntryNotReady(msg)
    manager.start(hass)

    if DOMAIN not in hass.data:
        hass.data[DOMAIN] = {}
    hass.data[DOMAIN][entry.entry_id] = {
        "client": client,
        "manager": manager,
    }

    await _async_migrate_unique_ids(hass, entry)
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
