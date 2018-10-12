import importlib
import sys


def cli(*argv):
    argv = argv if argv else sys.argv
    if len(argv) < 2:
        print('Dotted path to callable required.')
        sys.exit(1)

    cb = funcimp(argv[1])
    args, kwargs = expand(*argv[2:])
    return cb(*args, **kwargs)


def funcimp(callback):
    if ':' not in callback:
        funcname = 'main'
        modname = callback
    else:
        modname, funcname = callback.split(':')

    ret = importlib.import_module(modname)
    for part in funcname.split('.'):
        if isinstance(ret, dict) and part in ret:
            ret = ret.get(part)
        elif isinstance(ret, list) and part.isnumeric():
            ret = ret[int(part)]
        else:
            ret = getattr(ret, part)

    return ret


def expand(*argvs):
    args, kwargs = list(), dict()

    for argv in argvs:
        if argv == '-':
            args.append(sys.stdin.read())
            continue

        if argv.startswith('-'):
            continue

        if '=' in argv:
            name, value = argv.split('=')
            if value == '-':
                value = sys.stdin.read()
            kwargs[name] = value
        else:
            args.append(argv)

    return args, kwargs


class Context:
    def __init__(self, *args, **kwargs):
        self.args = list(args)
        self.kwargs = kwargs

    @classmethod
    def factory(cls, argvs):
        context = cls()

        for argv in argvs:
            if not argv.startswith('-'):
                continue

            if argv == '--':
                context.args.append(sys.stdin.read())
                continue

            argv = argv.lstrip('-')

            if '=' in argv:
                key, value = argv.split('=')
                if value == '-':
                    value = sys.stdin.read()
                context.kwargs[key] = value

            else:
                context.args.append(argv)

        return context


context = Context.factory(sys.argv)
