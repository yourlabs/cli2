import importlib
import inspect
import traceback

import clilabs


__all__ = ['debug', 'help']


def _modhelp(modname):
    filename = importlib.find_loader(modname).get_filename()
    moddoc = filedoc(filename)

    if moddoc:
        print('Module docstring:', moddoc)

    try:
        mod = importlib.import_module(modname)
    except ImportError:
        traceback.print_exc()
        print(f'Could not import module: {modname}')
    else:
        callables = clilabs.callables(mod)
        if callables:
            print(f'Callables found in: {filename}')
            print("\n".join(callables))
        else:
            print(f'No callable found in {filename}')

    if not moddoc and not callables:
        print('No help found')


def filedoc(filepath):
    co = compile(open(filepath).read(), filepath, 'exec')
    if co.co_consts and isinstance(co.co_consts[0], str):
        docstring = co.co_consts[0]
    else:
        docstring = None
    return docstring


def help(cb=None):
    """
    Get help for a callable, or list callables for a module.

    Examples:

    # Print module docstring and list of callables:
    clilabs help clilabs.mod
    clilabs help mod (same as above)
    clilabs help ~your.mod

    # Print callable docstring
    clilabs help clilabs.mod:func
    clilabs help mod:func (same as above)
    clilabs help ~external.mod:func
    """
    if not cb:
        cb = 'clilabs:cli'

    modname, funcname = clilabs.funcexpand(cb)

    try:
        cb = clilabs.modfuncimp(modname, funcname)
    except ImportError:
        if ':' not in cb:
            _modhelp(modname)
    else:
        funcdoc = inspect.getdoc(cb)
        if funcdoc:
            print(funcdoc)
        else:
            print(f'No docstring found for {modname}:{funcname}')
            _modhelp(modname)


def debug(*args, **kwargs):
    """Print debug output for a command line.

    The debug function is made to dump the result of the clilabs parser.
    It will show what callable and arguments it will use.
    You will see that the following are not the same, as stated in the
    tutorial.

    clilabs debug your:func -x 12
    clilabs debug your:func -x=12
    """
    if not args:
        return print('func:arg argument required ie. clilabs debug your:func')

    try:
        cb = clilabs.funcimp(args[0])
    except ImportError:
        cb = args[0]
        print(f'Could not import {cb}')
    else:
        print(f'Callable: {cb}')
        print(f'Callable path: {cb.__code__.co_filename}')

    print(f'Args: {args[1:]}')
    print(f'Kwargs: {kwargs}')
    print(f'Context args: {clilabs.context.args}')
    print(f'Context kwargs: {clilabs.context.kwargs}')
