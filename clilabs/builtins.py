import inspect
import clilabs


__all__ = ['debug', 'help']


def help(cb=None):
    if not cb:
        cb = 'clilabs:cli'
    cb = clilabs.funcimp(cb)
    print(inspect.getdoc(cb))


def debug(*args, **kwargs):
    try:
        cb = clilabs.funcimp(args[0])
    except ImportError:
        cb = args[0]
        print(f'Could not import: {cb}')
    else:
        print(f'Callable: {cb}')
        print(f'Callable path: {cb.__code__.co_filename}')

    print(f'Args: {args[1:]}')
    print(f'Kwargs: {kwargs}')
    print(f'Context args: {clilabs.context.args}')
    print(f'Context kwagrs: {clilabs.context.kwargs}')
