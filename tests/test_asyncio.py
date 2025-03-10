import asyncio
import cli2
import pytest


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
    results = []

    async def worker(i):
        results.append(i)
        await asyncio.sleep(0.01)

    queue = cli2.Queue()
    await queue.run(worker(1), worker(2), worker(3))
    
    assert sorted(results) == [1, 2, 3]


@pytest.mark.asyncio
async def test_queue_concurrency():
    results = []
    start = asyncio.get_event_loop().time()

    async def worker(i):
        results.append(i)
        await asyncio.sleep(0.1)

    queue = cli2.Queue(num_workers=3)
    await queue.run(worker(1), worker(2), worker(3))
    
    duration = asyncio.get_event_loop().time() - start
    assert duration < 0.15  # Should run in parallel
    assert sorted(results) == [1, 2, 3]


@pytest.mark.asyncio
async def test_queue_error_handling():
    results = []

    async def worker(i):
        if i == 2:
            raise ValueError('test error')
        results.append(i)
        await asyncio.sleep(0.01)

    queue = cli2.Queue()
    await queue.run(worker(1), worker(2), worker(3))
    
    assert results == [1, 3]  # Error should not stop other tasks


@pytest.mark.asyncio
async def test_queue_many_tasks():
    results = []

    async def worker(i):
        results.append(i)
        await asyncio.sleep(0.01)

    queue = cli2.Queue(num_workers=2)
    tasks = [worker(i) for i in range(10)]
    await queue.run(*tasks)
    
    assert sorted(results) == list(range(10))
