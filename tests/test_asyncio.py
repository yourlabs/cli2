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
