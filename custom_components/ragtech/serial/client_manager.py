import asyncio
from datetime import datetime

from .client import RagtechSerialClient


class RagtechSerialClientManager:
    def __init__(self, client: RagtechSerialClient, polling_interval: int):
        self._client = client
        self._polling_interval = polling_interval
        self._data = None
        self._last_update = None
        self._lock = asyncio.Lock()
        self._task = None

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
        self._last_update = datetime.now()

    async def _updater(self):
        while True:
            async with self._lock:
                await self._fetch_data()
            await asyncio.sleep(self._polling_interval)

    async def get_status(self):
        async with self._lock:
            if self._data is None:
                await self._fetch_data()
            return self._data
