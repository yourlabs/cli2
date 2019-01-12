'''cli2 makes your python callbacks work on CLI too !

cli2 provides sub-commands to introspect python modules or callables docstrings
or to execute callables or help working with cli2 itself.
'''

import collections
import importlib
import inspect
import pprint
import types
import sys

import colorama


GREEN = colorama.Fore.GREEN
RED = colorama.Fore.RED
YELLOW = colorama.Fore.YELLOW
RESET = colorama.Style.RESET_ALL


class Cli2Exception(Exception):
    pass


class Cli2ArgsException(Cli2Exception):
    def __init__(self, command, passed_args):
        msg = ['Got arguments:'] if len(passed_args) else []

        for arg, i in enumerate(passed_args, start=0):
            msg.append('='.join(command.required_args[i], arg))

        msg.append(
            'Missing arguments: ' + ', '.join([*map(
                lambda i: f'{RED}{i}{RESET}',
                command.required_args[len(passed_args):],
            )])
        )

        super().__init__('\n'.join(msg))


def help(*args):
    """
    Get help for a command.

    Example::

        $ cli2 help help
    """
    if not args:
        # show console script documentation
        yield console_script.doc
    else:
        # show command documentation
        yield console_script[' '.join(args)].doc


def docfile(filepath):
    """
    Docstring for a file path.
    
    Examples:

        cli2 docfile foo.py
    """
    co = compile(open(filepath).read(), filepath, 'exec')
    if co.co_consts and isinstance(co.co_consts[0], str):
        docstring = co.co_consts[0]
    else:
        docstring = None
    return docstring
docfile._cli2_color = RED


def docmod(module_name):
    import ipdb; ipdb.set_trace()
    return docfile(Importable.factory(module_name).module.__file__).strip()


class Parser:
    def __init__(self, argv):
        self.funcargs = []
        self.funckwargs = {}
        self.dashargs = []
        self.dashkwargs = {}

        for arg in argv:
            self.append(arg)

    def append(self, arg):
        if '=' in arg:
            if arg.startswith('-'):
                key, value = arg.lstrip('-').split('=')
                self.dashkwargs[key] = value
            else:
                key, value = arg.split('=', 1)
                self.funckwargs[key] = value

        else:
            if arg.startswith('-'):
                self.dashargs.append(arg.lstrip('-'))
            else:
                self.funcargs.append(arg)


class DocDescriptor:
    def __get__(self, obj, objtype):
        if 'value' in self.__dict__:
            return self.value

        if obj.is_module:
            return docfile(obj.module.__file__)
        else:
            return inspect.getdoc(obj.target)

    def __set__(self, obj, value):
        self.value = value


class Importable:
    doc = DocDescriptor()

    def __init__(self, name, target):
        self.name = name
        self.target = target

        if isinstance(target, types.ModuleType):
            self.module = target
        else:
            self.module = target.__module__

    def __str__(self):
        return self.name
    __repr__ = __str__

    def __eq__(self, other):
        return other.name == self.name and other.target == self.target

    @classmethod
    def factory(cls, name):
        module = None
        parts = name.split('.')
        for i, part in reversed(list(enumerate(parts))):
            modname = '.'.join(parts[:i + 1])

            if not modname:
                break

            try:
                module = importlib.import_module(modname)
            except ImportError:
                continue
            else:
                break

        if module:
            ret = module
            for part in parts[i + 1:]:
                if isinstance(ret, dict) and part in ret:
                    ret = ret.get(part)
                elif isinstance(ret, list) and part.isnumeric():
                    ret = ret[int(part)]
                else:
                    ret = getattr(ret, part, None)

        return cls(name, ret)

    def get_callables(self, whitelist=None, blacklist=None):
        for name, member in inspect.getmembers(self.target):
            if not callable(member):
                continue

            if isinstance(member, type):
                continue

            if whitelist and name not in whitelist:
                continue

            if blacklist and name in blacklist:
                continue

            if name.startswith('_'):
                continue

            if getattr(member, '_cli2_exclude', None):
                continue

            yield Callable(name, member)

    @property
    def is_module(self):
        return self.module == self.target


class Callable(Importable):
    pass


class Command(Callable):
    doc = DocDescriptor()

    def __call__(self, *args, **kwargs):
        if len(args) < len(self.required_args):
            raise Cli2ArgsException(self, args)
        return self.target(*args, **kwargs)

    @property
    def required_args(self):
        argspec = inspect.getfullargspec(self.target)
        return argspec.args[len(argspec.defaults or []):]


class GroupDocDescriptor:
    def __get__(self, obj, objtype):
        ret = []

        if 'value' in self.__dict__:
            ret.append(self.value)

        max_length = 0
        for line, cmd in obj.items():
            if line == obj.name:
                continue

            if len(line) > max_length:
                max_length = len(line)

        width = max_length + 2
        for line, cmd in obj.items():
            if line == 'main':
                continue

            color = getattr(cmd.target, '_cli2_color', YELLOW)
            line = '  ' + color + line + RESET + (width - len(line)) * ' '
            if cmd.target:
                doc = inspect.getdoc(cmd.target)

                if doc:
                    line += doc.split('\n')[0]
                else:
                    line += 'Docstring not found'
            else:
                line += 'Callback not found'

            ret.append(line)

        return '\n'.join(ret)

    def __set__(self, obj, value):
        self.value = value


class Group(collections.OrderedDict):
    doc = GroupDocDescriptor()

    def __init__(self, name, doc=None):
        self.name = name
        self.doc = doc or 'Documentation not set'
        self['help'] = Command('help', help)

    def add_module(self, module_name):
        importable = Importable.factory(module_name)

        if not importable.module:
            raise Exception('Module not found' + module)

        for cb in importable.get_callables():
            self[cb.name] = Command(cb.name, cb.target)

        return self


class ConsoleScript(Group):
    def __init__(self, argv=None, doc=None, default_command='help'):
        self.default_command = default_command
        argv = argv if argv is not None else sys.argv
        Group.__init__(self, argv[0].split('/')[-1], doc)
        self.argv = argv[1:]
        # self.args = []

    def __call__(self):
        # patch cli2.console_script
        # global console_script
        # console_script = self

        if len(self.argv):
            command = self[self.argv[0]]
        else:
            command = self[self.default_command]

        #if not self.command or not command.path.callable:
        #    return f'No callback found for command {self.command}'

        self.parser = Parser(self.argv[1:])

        colorama.init()

        # setup = getattr(self.command.path.module, '_cli2_setup', None)
        # if setup:
        #     setup()

        try:
            result = command(*self.parser.funcargs, **self.parser.funckwargs)
            if isinstance(result, (types.GeneratorType, list)):
                for r in result:
                    self.handle_result(r)
            else:
                self.handle_result(result)
        except Cli2Exception as e:
            print('\n'.join([str(e), '', self.command.path.docstring]))
        except Exception:
            raise
        finally:
            clean = False
            #clean = getattr(self.command.path.module, '_cli2_clean', None)
            if clean:
                clean()

        return result if isinstance(result, int) else 0

    def handle_result(self, result):
        if isinstance(result, str):
            print(result)
        else:
            pprint.PrettyPrinter(indent=4).pprint(result)


console_script = ConsoleScript(sys.argv, __doc__).add_module('cli2')
