import inspect
import importlib
import traceback
import sys


class Context:
    """Args/kwargs starting with dash go in context."""

    def __init__(self, *args, **kwargs):
        self.args = list(args)
        self.kwargs = kwargs
        self.argv = []

    @classmethod
    def factory(cls, argvs):
        context = cls()

        for argv in argvs:
            if not argv.startswith('-'):
                continue

            if argv == '--':
                context.args.append(sys.stdin.read().strip())
                continue

            context.argv.append(argv)
            argv = argv.lstrip('-')

            if '=' in argv:
                key, value = argv.split('=', 1)
                if value == '-':
                    value = sys.stdin.read().strip()
                context.kwargs[key] = value

            else:
                context.args.append(argv)

        return context
context = Context.factory(sys.argv)


def expand(*argv):
    """Extract args/kwargs not starting with dash."""
    args, kwargs = list(), dict()

    for arg in argv:
        if arg == '-':
            args.append(sys.stdin.read().strip())
            continue

        if arg.startswith('-'):
            continue

        if '=' in arg:
            name, value = arg.split('=', 1)
            if value == '-':
                value = sys.stdin.read().strip()
            kwargs[name] = value
        else:
            args.append(arg)

    return args, kwargs


def callables(mod):
    """Return the callables of a module."""
    return [
        i[0]
        for i in inspect.getmembers(mod)
        if callable(getattr(mod, i[0]))
        and not i[0].startswith('_')
    ]


def funcexpand(callback, builtin_module_name=None):
    """Separate module name from callable name."""
    builtin_module_name = builtin_module_name or 'clilabs.builtins'
    builtin_module = importlib.import_module(builtin_module_name)
    if callback in callables(builtin_module):
        return builtin_module_name, callback

    if ':' not in callback:
        print('Please use mod.name:func.name')
        return False, False
    else:
        modname, funcname = callback.split(':')
        if not modname:
            modname = 'builtins'

    if modname.startswith('~'):
        modname = modname[1:]
    else:
        default = f'clilabs.{modname}'
        try:
            __import__(default)
        except ImportError:
            pass
        else:
            modname = default

    return modname, funcname


def modfuncimp(modname, funcname):
    """Import a callback from a module."""
    ret = importlib.import_module(modname)
    for part in funcname.split('.'):
        if isinstance(ret, dict) and part in ret:
            ret = ret.get(part)
        elif isinstance(ret, list) and part.isnumeric():
            ret = ret[int(part)]
        else:
            ret = getattr(ret, part, None)

        if ret is None:
            raise ImportError(f'{part} is None')

    return ret


def funcimp(callback):
    """Import a callback."""
    modname, funcname = funcexpand(callback)
    if not modname or not funcname:
        return None
    return modfuncimp(modname, funcname)


def _modhelp(modname):
    """Return the help for a module."""
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
    """Return the documentation for a file."""
    co = compile(open(filepath).read(), filepath, 'exec')
    if co.co_consts and isinstance(co.co_consts[0], str):
        docstring = co.co_consts[0]
    else:
        docstring = None
    return docstring


def help(cb=None):
    """
    Get help for a callable, or list callables for a module.
    """
    cb = cb or 'clitool'

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


def main(*argv):
    '''Clitoo makes your python callbacks work on CLI too !

    This CLI can execute python callbacks with parameters.

    Clitoo recognizes 4 types of command line arguments:

    - lone arguments are passed as args
    - arguments with = are passed as kwargs
    - dashed arguments like -f arrive in context.args
    - dashed arguments like -foo=bar arrive in context.kwargs

    It doesn't matter how many dashes you put in the front, they are all
    removed.

    To use the context in your callback just import the clitoo context::

        from clitoo import context
        print(context.args, context.kwargs)

    Clitoo provides 2 builtin commands: help and debug. Any other first
    argument will be considered as the dotted path to the callback to import
    and execute.

    Examples:

    clitoo help your.mod:funcname
        Print out the function docstring.

    clitoo debug your.mod -a --b --something='to see' how it=parses
        Dry run of your.mod with arguments, dump out actual calls.

    clitoo your.mod:funcname with your=args
        Call your.mod.funcname('with', your='args').
    '''
    argv = argv if argv else sys.argv
    if len(argv) < 2:
        argv.append('help')

    cb = funcimp(argv[1])
    args, kwargs = expand(*argv[2:])
    return cb(*args, **kwargs)
