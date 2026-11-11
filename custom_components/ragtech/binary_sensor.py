from .entities.ups.ups_binary_sensor import get_ups_binary_sensors
from .utils.const import DOMAIN


async def async_setup_entry(hass, entry, async_add_entities):
    manager = hass.data[DOMAIN][entry.entry_id]["manager"]
    data = await manager.get_status()
    if not data:
        return

    async_add_entities(
        get_ups_binary_sensors(entry, manager, data), update_before_add=True
    )
