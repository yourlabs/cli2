import inspect
from . import display


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
