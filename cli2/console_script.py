import collections
import inspect
import colorama
import pprint
import sys
import types

from .colors import RESET
from .parser import Parser
from .exceptions import Cli2ArgsException, Cli2Exception
from .introspection import Callable, Importable


class GroupDocDescriptor:
    def __get__(self, obj, objtype):
        ret = []

        if 'value' in self.__dict__:
            ret.append(self.value.strip() + '\n')

        width = len(max(obj.keys(), key=len)) + 2
        for name, cmd in obj.items():
            line = '  ' + ''.join([
                cmd.color,
                name,
                RESET,
                (width - len(name)) * ' '
            ])

            if cmd.target:
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
        self.value = value


class Group(collections.OrderedDict):
    doc = GroupDocDescriptor()

    def __init__(self, name, doc=None):
        self.name = name
        if doc:
            self.doc = doc

    def add_help(self):
        from .cli import help
        self.add_commands(help)
        return self

    def add_module(self, module_name):
        importable = Importable.factory(module_name)

        if not importable.module:
            raise Cli2Exception('Module not found' + importable.module)

        for cb in importable.get_callables():
            self[cb.name] = Callable.for_callback(cb.target)

        return self

    def add_commands(self, *callbacks):
        for cb in callbacks:
            self[cb.__name__] = Callable.for_callback(cb)
        return self

    @classmethod
    def factory(cls, module_name):
        doc = Importable.factory(module_name).doc
        return cls(module_name, doc).add_module(module_name)


class ConsoleScript(Group):
    def __init__(self, doc=None, argv=None, default_command='help'):
        ConsoleScript.singleton = self
        self.default_command = default_command
        argv = argv if argv is not None else sys.argv
        Group.__init__(self, argv[0].split('/')[-1], doc)
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
