import inspect
import importlib
import sys


def cli(*argv):
    '''clilabs automates python callables parametered calls.

    Things starting with - will arrive in clilabs.context.

    Examples:

        clilabs help your.mod:funcname to get its docstring.
        clilabs debug your.mod -a --b --something='to see' how it=parses
        clilabs your.mod:funcname with your=args
        clilabs help clilabs.django
        clilabs help django
        clilabs ~django.db.models:somefunc # to run actual django package func
    '''
    argv = argv if argv else sys.argv
    if len(argv) < 2:
        argv.append('help')

    cb = funcimp(argv[1])
    args, kwargs = expand(*argv[2:])
    return cb(*args, **kwargs)


def callables(mod):
    return [
        i[0]
        for i in inspect.getmembers(mod)
        if callable(getattr(mod, i[0]))
        and not i[0].startswith('_')
    ]


def funcexpand(callback, builtin_module_name=None):
    builtin_module_name = builtin_module_name or 'clilabs.builtins'
    builtin_module = importlib.import_module(builtin_module_name)
    if callback in callables(builtin_module):
        return builtin_module_name, callback

    if ':' not in callback:
        funcname = 'main'
        modname = callback
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
    return modfuncimp(*funcexpand(callback))


def expand(*argvs):
    args, kwargs = list(), dict()

    for argv in argvs:
        if argv == '-':
            args.append(sys.stdin.read().strip())
            continue

        if argv.startswith('-'):
            continue

        if '=' in argv:
            name, value = argv.split('=', 1)
            if value == '-':
                value = sys.stdin.read().strip()
            kwargs[name] = value
        else:
            args.append(argv)

    return args, kwargs


class Context:
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
