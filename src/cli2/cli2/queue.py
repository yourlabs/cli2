"""
asyncio.Queue subclass

While useful, you might want to consider the :py:mod:`cli2.tasks` module
instead.
"""
import asyncio
import os
from .log import log


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

        Number of concurrent workers (default: cpucount * 2)

    .. py:attribute:: results

        List of results from completed tasks, order of results not garanteed
        due to concurrency.
    """

    def __init__(self, *args, num_workers=None, **kwargs):
        """Initialize the queue with worker pool.

        :param num_workers: Number of concurrent workers
                            (default: cpu count * 2)
        :paarm *args: Positional arguments for asyncio.Queue
        :param **kwargs: Keyword arguments for asyncio.Queue
        """
        self.num_workers = num_workers or os.cpu_count() * 2
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
