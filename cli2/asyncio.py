import asyncio
import inspect
from . import display
from .log import log


def async_iter(obj):
    """ Check if an object is an async iterable. """
    return inspect.isasyncgen(obj) or hasattr(obj, '__aiter__')


async def async_resolve(result, output=False):
    """
    Recursively resolve awaitables and async iterables.

    :param result: The awaitable or async iterable to resolve
    :param output: If True, print results as they are resolved. If False,
                   collect results.

    :return: The resolved value(s). If output is True, returns None. If output
             is False, returns a list of resolved values from async iterables.
    """
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
    """Run an async coroutine in the current event loop or create a new one.

    If an event loop is already running, creates a task in that loop.
    If no event loop is running, creates a new one and runs the coroutine.

    :param coroutine: The coroutine to run (return value of an async function)
    :return: The result of the coroutine execution
    """
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        return asyncio.run(coroutine)
    else:
        return loop.create_task(coroutine)


class Queue(asyncio.Queue):
    """
    An async queue with worker pool for concurrent task processing.

    Extends asyncio.Queue to manage a pool of worker tasks that process items
    from the queue concurrently.

    .. code-block:: python

        # will run 2 at the time
        queue = cli2.Queue(num_workers=2)
        # call like asyncio.run
        await queue.run(foo(), bar(), other())

    .. py:attribute:: num_workers

        Number of concurrent workers (default: 12)

    .. py:attribute:: results

        List of results from completed tasks, order of results not garanteed
        due to concurrency.
    """

    def __init__(self, *args, num_workers=12, **kwargs):
        """Initialize the queue with worker pool.

        :param num_workers: Number of concurrent workers (default: 12)
        :paarm *args: Positional arguments for asyncio.Queue
        :param **kwargs: Keyword arguments for asyncio.Queue
        """
        self.num_workers = num_workers or 12
        self.results = []
        super().__init__(*args, **kwargs)

    async def run(self, *tasks):
        """
        Run tasks through the worker pool.

        :param tasks: Coroutines
        """
        self.results = []

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
        """Worker task that processes items from the queue.

        Continuously gets tasks from the queue, executes them, and stores
        results.
        Handles exceptions by logging them.
        """
        while True:
            task = await self.get()
            try:
                result = await task
            except:  # noqa
                log.exception()
            else:
                self.results.append(result)
            finally:
                self.task_done()
