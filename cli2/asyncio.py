import asyncio
import inspect
from . import display
from .log import log


def async_iter(obj):
    return inspect.isasyncgen(obj) or hasattr(obj, '__aiter__')


async def async_resolve(result, output=False):
    """ Recursively resolve awaitables. """
    while inspect.iscoroutine(result):
        result = await result
    if async_iter(result):
        results = []
        async for _ in result:
            if output:
                if (
                    not inspect.iscoroutine(_)
                    and not inspect.isasyncgen(_)
                ):
                    display.print(_)
                else:
                    await async_resolve(_, output=output)
            else:
                results.append(await async_resolve(_))
        return None if output else results
    return result


def async_run(coroutine):
    """
    Run an async coroutineutine, in running loop or new loop.

    :param coroutine: The return value of an async function call.
    """
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        return asyncio.run(coroutine)
    else:
        return loop.create_task(coroutine)


class Queue(asyncio.Queue):
    def __init__(self, *args, num_workers=12, **kwargs):
        self.num_workers = num_workers or 12
        self.results = []
        super().__init__(*args, **kwargs)

    async def run(self, *tasks):
        for task in tasks:
            await self.put(task)

        workers = [
            asyncio.create_task(self.worker())
            for i in range(self.num_workers)
        ]

        await self.join()
        for worker in workers:
            worker.cancel()

    async def worker(self):
        while True:
            task = await self.get()
            try:
                result = await task
            except Exception as exc:
                log.exception()
            else:
                self.results.append(result)
            self.task_done()
