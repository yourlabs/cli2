import asyncio
import cli2
import pytest
from unittest import mock


def test_async_run_noloop():
    async def task():
        await asyncio.sleep(.01)

    cli2.async_run(task())


@pytest.mark.asyncio
async def test_async_run_loop():
    async def task():
        await asyncio.sleep(.01)

    cli2.async_run(task())


@pytest.mark.asyncio
async def test_queue_basic():
    async def task(i):
        return i

    queue = cli2.Queue()
    await queue.run(task(1), task(2), task(3))

    assert sorted(queue.results) == [1, 2, 3]


@pytest.mark.asyncio
async def test_queue_concurrency():
    start = asyncio.get_event_loop().time()

    async def worker(i):
        await asyncio.sleep(0.1)
        return i

    queue = cli2.Queue(num_workers=3)
    await queue.run(worker(1), worker(2), worker(3))

    duration = asyncio.get_event_loop().time() - start
    assert duration < 0.15, 'Should run in parallel'
    assert sorted(queue.results) == [1, 2, 3]


@pytest.mark.asyncio
async def test_queue_error_handling(monkeypatch):
    import cli2.asyncio
    logger = mock.Mock()
    monkeypatch.setattr(cli2.asyncio, 'log', logger)

    async def worker(i):
        if i == 2:
            raise ValueError('test error')
        await asyncio.sleep(0.01)
        return i

    queue = cli2.Queue()
    await queue.run(worker(1), worker(2), worker(3))

    # Error should not stop other tasks
    assert queue.results == [1, 3]

    # Exceptions should be printed though, not swallowed
    logger.exception.assert_called_once()
