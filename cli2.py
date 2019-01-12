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
    #console_script = guess_console_script()

    if not args:
        yield console_script.doc
    else:
        yield console_script.commands[' '.join(args)].path.docstring


def docfile(filepath):
    """Docstring for a file path."""
    co = compile(open(filepath).read(), filepath, 'exec')
    if co.co_consts and isinstance(co.co_consts[0], str):
        docstring = co.co_consts[0]
    else:
        docstring = None
    return docstring


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
            import ipdb; ipdb.set_trace()


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

            yield Callback(name, member)

    @property
    def is_module(self):
        return self.module == self.target


class Callback(Importable):
    pass


class Command(Callback):
    doc = DocDescriptor()

    def __init__(self, callback, name=None):
        self.callback = callback

        if name:
            self._name = name

    @property
    def name(self):
        if '_name' not in self.__dict__:
            self._name = 'name'
        return self._name


class Group:
    def __init__(self, name, doc=None):
        self.name = name
        self.children = collections.OrderedDict()
        self.children['help'] = Callback(help)

    def add_module(self, module_name):
        importable = Importable.factory(module_name)

        if not importable.module:
            raise Exception('Module not found' + module)

        for cb in importable.get_callables(whitelist, blacklist):
            self.children[cb.name] = Command(cb.name, cb.target)

        return self


class ConsoleScript(Group, Command):
    def __init__(self, argv=None, default_command='help'):
        self.default_command = default_command
        argv = argv if argv is not None else sys.argv

        Group.__init__(self, argv[0].split('/')[-1])

        Command.__init__(self, argv[0].split('/')[-1])
        self.argv = argv[1:]
        # self.args = []

    def __call__(self):
        # patch cli2.console_script
        # global console_script
        # console_script = self

        if len(self.argv):
            command = self.children[self.argv[1]]
        else:
            command = self.children[self.default_command]

        #if not self.command or not command.path.callable:
        #    return f'No callback found for command {self.command}'

        self.parser = Parser(self.argv)

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


console_script = ConsoleScript(sys.argv).add_module('cli2')
