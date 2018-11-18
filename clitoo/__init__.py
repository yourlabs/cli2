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


class Callback:
    def __init__(self):
        self.path = None
        self.module = None
        self.modname = None
        self.funcname = None
        self.parts = None
        self.cb = None
        self.callables = None
        self.default_module = None

    @classmethod
    def factory(cls, path):
        self = cls()
        self.path = path
        self.parts = self.path.split('.')
        for i, part in enumerate(self.parts):
            self.modname = '.'.join(self.parts[:i + 1])
            if not self.modname:
                return self

            try:
                self.module = importlib.import_module(self.modname)
            except ImportError:
                break

        ret = self.module
        for part in self.parts[i:]:
            if isinstance(ret, dict) and part in ret:
                ret = ret.get(part)
            elif isinstance(ret, list) and part.isnumeric():
                ret = ret[int(part)]
            else:
                ret = getattr(ret, part, None)

        if ret != self.module:
            self.cb = ret

        self.callables = [
            i[0]
            for i in inspect.getmembers(self.module)
            if callable(getattr(self.module, i[0]))
            and not i[0].startswith('_')
        ]

        return self

    @classmethod
    def select_cb(cls, path, default_module=None):
        self = cls.factory(path)

        if not self.cb and default_module:
            self = cls.factory(f'{default_module}.{path}')
            self.default_module = default_module

        if not self.cb:
            self = cls.factory(f'clitoo.{path}')
            self.default_module = 'clitoo'

        return self

    @property
    def filename(self):
        if self.modname:
            return importlib.find_loader(self.modname).get_filename()
        return False


def expand(*argv):
    """
    Extract args/kwargs not starting with dash.

    This will return a tuple of args and kwargs, making an arg of every argv
    that is passed alone, and a kwarg of any argv that contains = sign.

    For example:

        args, kwargs = expand('a', 'b=2', '-c', '--d=1')
        assert args == ['a']
        assert kwargs == {'b': '2'}

    """
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
    cb = cb or 'clitoo.main'

    cb = Callback.select_cb(cb)

    def _modhelp():
        """Return the help fr a module."""
        if cb.filename:
            moddoc = filedoc(cb.filename)

        if moddoc:
            print('Module docstring:', moddoc)

        try:
            importlib.import_module(cb.modname)
        except ImportError:
            traceback.print_exc()
            print(f'Could not import module: {cb.modname}')
        else:
            if cb.callables:
                print(f'Callables found in: {cb.filename}')
                print("\n".join(cb.callables))
            else:
                print(f'No callable found in {cb.filename}')

        if not moddoc and not cb.callables:
            print('No help found')

    if cb.cb:
        funcdoc = inspect.getdoc(cb.cb)

        if funcdoc:
            print(funcdoc)
        else:
            print(f'No docstring found for {cb.path}')
            _modhelp()
    else:
        _modhelp()


def debug(*args, **kwargs):
    """Print debug output for a command line.

    The debug function is made to dump the result of the clilabs parser.
    It will show what callable and arguments it will use.
    You will see that the following are not the same, as stated in the
    tutorial::

        clitoo debug your.func -x 12
        clitoo debug your.func -x=12
    """
    if not args:
        return print('Argument argument required ie. clilabs debug your.func')

    cb = Callback.select_cb(args[0])
    if not cb.cb:
        print(f'Could not import {args[0]} nor {cb.path}')
    else:
        print(f'Callable: {cb.cb}')
        print(f'Callable path: {cb.cb.__code__.co_filename}')

    print(f'Args: {args[1:]}')
    print(f'Kwargs: {kwargs}')
    print(f'Context args: {context.args}')
    print(f'Context kwargs: {context.kwargs}')


def main(argv=None, default_module=None):
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

    clitoo help your.mod.funcname
        Print out the function docstring.

    clitoo debug your.func -a --b --something='to see' how it=parses
        Dry run of your.mod with arguments, dump out actual calls.

    clitoo your.mod.funcname with your=args
        Call your.mod.funcname('with', your='args').
    '''
    default_module = default_module or 'clitoo'

    argv = argv if argv else sys.argv
    path = argv[1] if len(argv) > 1 else 'help'

    context.callback = Callback.select_cb(path, default_module)
    args, kwargs = expand(*argv[2:])
    return context.callback.cb(*args, **kwargs)
