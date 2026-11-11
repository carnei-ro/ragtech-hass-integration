from __future__ import annotations

import asyncio
from datetime import datetime

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .client import RagtechSerialClient

# Polls in a row without a usable frame before the last values count as stale.
STALE_AFTER_FAILED_POLLS = 3


class RagtechSerialClientManager:
    def __init__(self, client: RagtechSerialClient, polling_interval: int):
        self._client = client
        self._polling_interval = polling_interval
        self._data = None
        self._last_update = None
        self._lock = asyncio.Lock()
        self._task = None
        self._failed_polls = 0

    @property
    def stale(self):
        """True while the UPS has left several polls in a row unanswered."""
        return self._failed_polls >= STALE_AFTER_FAILED_POLLS

    def start(self, hass):
        if self._task is None:
            self._task = hass.loop.create_task(self._updater())

    def stop(self):
        if self._task is not None:
            self._task.cancel()
            self._task = None

    async def _fetch_data(self):
        data = await asyncio.to_thread(self._client.get_status)
        if data:
            self._data = data
            self._failed_polls = 0
        else:
            self._failed_polls += 1
        self._last_update = datetime.now()

    async def _updater(self):
        # Setup has just polled: wait one interval before the next poll.
        while True:
            await asyncio.sleep(self._polling_interval)
            async with self._lock:
                await self._fetch_data()

    async def get_status(self):
        async with self._lock:
            if self._data is None:
                await self._fetch_data()
            return self._data
