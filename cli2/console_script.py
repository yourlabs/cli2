import collections
import inspect
import colorama
import pprint
import os.path
import sys
import types

from .colors import RESET
from .parser import Parser
from .exceptions import Cli2ArgsException, Cli2Exception
from .introspection import Callable, Importable


class GroupDocDescriptor:
    def __get__(self, obj, objtype):
        ret = []

        if '_doc' in obj.__dict__:
            ret.append(obj._doc.strip() + '\n')

        width = len(max(obj.keys(), key=len, default=[''])) + 2
        for name, cmd in obj.items():
            line = '  ' + ''.join([
                cmd.color,
                name,
                RESET,
                (width - len(name)) * ' '
            ])

            if cmd.target:
                if isinstance(cmd, Group):
                    doc = cmd.doc.split('\n')[0]
                else:
                    doc = inspect.getdoc(cmd.target)

                if doc:
                    line += doc.split('\n')[0]
                else:
                    line += cmd.name + str(inspect.signature(cmd.target))
            else:
                line += 'Callback not found'

            ret.append(line)

        return '\n'.join(ret)

    def __set__(self, obj, value):
        obj._doc = value


class BaseGroup(collections.OrderedDict):
    doc = GroupDocDescriptor()

    def __init__(self, name, doc=None, default_command='help'):
        self.name = name
        if doc:
            self.doc = doc
        self.default_command = default_command

    def add_help(self):
        from .cli import help
        self.add_commands(help)
        return self

    def add_module(self, module_name):
        importable = Importable.factory(module_name)

        if not importable.module:
            raise Cli2Exception('Module not found')

        for cb in importable.get_callables():
            self[cb.name] = Callable.for_callback(cb.target)

        return self

    def add_commands(self, *callbacks):
        for cb in callbacks:
            _callable = Callable.for_callback(cb)
            self[_callable.name] = _callable
        return self

    def add_group(self, name, *args, **kwargs):
        self[name] = Group(name, *args, **kwargs)
        return self[name]

    @classmethod
    def factory(cls, module_name):
        doc = Importable.factory(module_name).doc
        return cls(module_name, doc).add_module(module_name)


class Group(Callable, BaseGroup):
    doc = GroupDocDescriptor()

    def __init__(self, name, doc=None, default_command='help', color=None,
                 options=None):

        from .cli import help
        BaseGroup.__init__(self, name, doc, default_command=default_command)
        Callable.__init__(self, name, help, color=color, options=options)
        self.add_help()
        if doc:
            self.doc = doc

    @classmethod
    def factory(cls, name, module_name):
        doc = Importable.factory(module_name).doc
        return cls(name, doc).add_module(module_name)


class ConsoleScript(BaseGroup):
    def __init__(self, doc=None, argv=None, default_command='help'):
        ConsoleScript.singleton = self
        argv = argv if argv is not None else sys.argv
        super().__init__(os.path.basename(argv[0]), doc, default_command)
        self.argv = argv
        self.exit_code = 0
        self.add_help()

    def __call__(self):
        ConsoleScript.singleton = self

        self.parser = Parser(self.argv[1:], self)
        self.parser.parse()

        colorama.init()

        result = None
        try:
            result = self.call(self.parser.command)
            if isinstance(result, (types.GeneratorType, list)):
                for r in result:
                    self.result_handler(r)
            else:
                self.result_handler(result)
        except Cli2ArgsException as e:
            self.exit_code = 1
            print('\n'.join([str(e), '', self.parser.command.doc]))
        except Cli2Exception as e:
            self.exit_code = 1
            print(str(e))
        except Exception:
            self.exit_code = 1
            raise

        return self.exit_code

    def call(self, command):
        return command(*self.parser.funcargs, **self.parser.funckwargs)

    def result_handler(self, result):
        if isinstance(result, str):
            print(result)
        elif result is None:
            pass
        else:
            pprint.PrettyPrinter(indent=4).pprint(result)

    def result_handler_set(self, result_handler):
        self.result_handler = result_handler.__get__(self, type(self))


ConsoleScript.singleton = ConsoleScript()
