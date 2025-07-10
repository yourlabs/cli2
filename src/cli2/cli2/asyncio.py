import aiofiles
import inspect
from . import display
from .queue import Queue


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


async def files_read(paths, num_workers=None, mode='r', silent=False):
    """
    Read a list of files asynchronously with anyio.

    :param paths: File paths to read.
    :param num_workers: Number of workers, cpucount*2 by default.
    :return: Dict of path=content
    """

    result = dict()

    async def file_read(path):
        try:
            async with aiofiles.open(str(path), mode) as f:
                result[path] = await f.read()
        except:  # noqa
            if not silent:
                raise

    queue = Queue(num_workers=num_workers)
    await queue.run(*[file_read(path) for path in paths])

    return {key: result[key] for key in sorted(result)}
