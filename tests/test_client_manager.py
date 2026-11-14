import asyncio

from custom_components.ragtech.serial.client_manager import RagtechSerialClientManager

DATA = {"ups.status": "OL"}


class ScriptedClient:
    """Stands in for the serial client: one scripted result per poll."""

    def __init__(self, results):
        self._results = iter(results)

    def get_status(self):
        return next(self._results)


def _poll(results):
    """Poll once per scripted result; the manager polls again until it has data."""
    manager = RagtechSerialClientManager(ScriptedClient(results), 10)

    async def run():
        return [await manager.get_status() for _ in results]

    return manager, asyncio.run(run())


def test_two_unanswered_polls_are_not_stale_yet():
    manager, _ = _poll([None, None])
    assert not manager.stale


def test_three_unanswered_polls_are_stale():
    manager, _ = _poll([None, None, None])
    assert manager.stale


def test_an_answer_ends_staleness():
    manager, polled = _poll([None, None, None, DATA])
    assert polled[-1] == DATA
    assert not manager.stale
