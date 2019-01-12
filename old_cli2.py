'''cli2 makes your python callbacks work on CLI too !

cli2 provides sub-commands to introspect python modules or callables docstrings
or to execute callables or help working with cli2 itself.
'''

import collections
import inspect
import importlib
import os
import pkg_resources
import pprint
import textwrap
import types
import shutil
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


class Path:
    def __init__(self, path):
        self.path = None
        self.parts = None
        self.module = None
        self.callable = None

        self.path = path
        self.parts = self.path.split('.')

        for i, part in reversed(list(enumerate(self.parts))):
            modname = '.'.join(self.parts[:i + 1])

            if not modname:
                break

            try:
                self.module = importlib.import_module(modname)
            except ImportError:
                continue
            else:
                break

        if self.module:
            ret = self.module
            for part in self.parts[i + 1:]:
                if isinstance(ret, dict) and part in ret:
                    ret = ret.get(part)
                elif isinstance(ret, list) and part.isnumeric():
                    ret = ret[int(part)]
                else:
                    ret = getattr(ret, part, None)

            if ret != self.module:
                self.callable = ret

    @property
    def module_name(self):
        return self.module.__name__

    @property
    def module_callables(self):
        return [
            i[0]
            for i in inspect.getmembers(self.module)
            if callable(getattr(self.module, i[0]))
            and not isinstance(getattr(self.module, i[0]), type)
            and not i[0].startswith('_')
            and not getattr(getattr(self.module, i[0]), '_cli2_exclude', None)
        ]

    @property
    def module_docstring(self):
        return docfile(self.module.__file__)

    @property
    def callable_docstring(self):
        docstring = inspect.getdoc(self.callable)
        return docstring

    @property
    def docstring(self):
        return str(
            self.callable_docstring if self.callable else self.module_docstring
        )

    def __str__(self):
        return '.'.join(self.parts)


class Command:
    def __init__(self, line, target, args=None):
        self.line = line
        self.target = target
        self.args = args
        self.path = Path(self.target)

    def __repr__(self):
        return self.target

    def __call__(self, *args, **kwargs):
        args = self.args or args
        if len(args) < len(self.required_args):
            raise Cli2ArgsException(self, args)
        return self.path.callable(*args, **kwargs)

    @property
    def required_args(self):
        argspec = inspect.getfullargspec(self.path.callable)
        return argspec.args[len(argspec.defaults or []):]

    @classmethod
    def factory(cls, entrypoint):
        line = entrypoint.name
        if '*' in line:
            right = line[line.index('*') + 1:].strip()
            path = Path(entrypoint.module_name)
            for name in path.module_callables:
                yield cls(
                    ' '.join((name, right)).strip(),
                    f'{path.module_name}.{name}'
                )
        else:
            args = None
            target = entrypoint.module_name

            if entrypoint.attrs:
                try:
                    entrypoint.load()
                except ImportError:
                    args = entrypoint.attrs
                else:
                    target = '.'.join(
                        (entrypoint.module_name, ' '.join(entrypoint.attrs))
                    )
            yield cls(line, target, args)


class Group:
    def __init__(self, name, entrypoints=None):
        self.name = name.split('/')[-1]          # strip FS path details
        self.name = self.name.replace('-', '_')  # entry point name forbids

        self.commands = collections.OrderedDict()
        self.load_entrypoints(
            entrypoints or pkg_resources.iter_entry_points('cli2_' + self.name)
        )

        self.default = 'main' if 'main' in self.commands else 'help'

    def load_entrypoints(self, entrypoints):
        for ep in entrypoints:
            for command in Command.factory(ep):
                if command.line not in self.commands:
                    self.commands[command.line] = command

        if 'help' not in self.commands:
            self.commands['help'] = Command('help', 'cli2.help')

    def find_command(self, argv):
        args = ' '.join(argv[1:])

        for line, command in self.commands.items():
            if args.startswith(command.line):
                return command, argv[2 + line.count(' '):]

        return self.commands[self.default], argv[1:]

    @property
    def doc(self):
        if self.default == 'help':
            yield [*self.commands.values()][0].path.module_docstring
        else:
            yield self.commands[self.default].path.callable_docstring

        max_length = 0
        for line, cmd in self.commands.items():
            if line == self.name:
                continue

            if len(line) > max_length:
                max_length = len(line)

        width = max_length + 2
        for line, cmd in self.commands.items():
            if line == 'main':
                continue

            color = getattr(cmd.path.callable, '_cli2_color', YELLOW)
            line = '  ' + color + line + RESET + (width - len(line)) * ' '
            if cmd.path.callable:
                doc = inspect.getdoc(cmd.path.callable)

                if doc:
                    line += doc.split('\n')[0]
                else:
                    line += 'Docstring not found'
            else:
                line += 'Callback not found'

            yield line


def docfile(filepath):
    """Docstring for a file path."""
    co = compile(open(filepath).read(), filepath, 'exec')
    if co.co_consts and isinstance(co.co_consts[0], str):
        docstring = co.co_consts[0]
    else:
        docstring = None
    return docstring


def docmod(module_name, group_name=None):
    """Docstring for a module name."""
    path = Path(module_name)
    yield docfile(path.module.__file__).strip() + '\n'

    if group_name:
        group = Group(group_name)

        try:
            termwidth = shutil.get_terminal_size().columns
        except Exception:
            termwidth = 80

        max_length = 0
        for line, cmd in group.commands.items():
            if line == group.name:
                continue

            if len(line) > max_length:
                max_length = len(line)

        width = max_length + 2
        for line, cmd in group.commands.items():
            if line == console_script.command_name:
                continue

            color = getattr(cmd.path.callable, '_cli2_color', YELLOW)
            line = '  ' + color + line + RESET + (width - len(line)) * ' '
            if cmd.path.callable:
                doc = inspect.getdoc(cmd.path.callable)

                if doc:
                    line += doc.split('\n')[0][:termwidth - len(line)]
                else:
                    line += 'Docstring not found'
            else:
                line += 'Callback not found'

            yield line


def doc(*args):
    """
    Return documentation for a file, module or callback.

    Example::

        $ cli2 doc foo.py
        $ cli2 doc foo.bar
        $ cli2 doc foo
    """

    if len(args) == 1 and os.path.exists(args[0]):
        yield docfile(args[0])

    elif args:
        extra = ' '.join(args)
        try:
            path = console_script.group.commands[extra].path
        except KeyError:
            path = Path(args[0])

        if path.callable:
            yield f'Docstring for {path}'
            yield path.docstring
        elif path.module:
            yield from docmod(path.module_name, console_script.group.name)
        else:
            yield f'Command not found {console_script.command_name} {extra}'

    else:
        # fuzzy workaround for when you have not bount cli2.help:yourmodule but
        # only have cli2.help or cli2:help on the main ep for some reason.
        default_module_name = console_script.command_name.replace('-', '_')
        for line in docmod(default_module_name, console_script.group.name):
            yield line


def guess_console_script():
    """Guess the ConsoleScript instance from stack introspection."""
    for frame_info in inspect.stack():
        if 'self' not in frame_info.frame.f_locals:
            continue

        if isinstance(frame_info.frame.f_locals['self'], ConsoleScript):
            break

    if 'self' not in frame_info.frame.f_locals:
        return console_script

    return frame_info.frame.f_locals['self']


def help(*args):
    """
    Get help for a command.

    Example::

        $ cli2 help help
    """
    console_script = guess_console_script()

    if not args:
        yield from console_script.group.doc
    else:
        yield console_script.group.commands[' '.join(args)].path.docstring


def main(callback=None, *args, **kwargs):
    """
    Execute a python callback on the command line.

    If no callback is given, display help. For this reason, you should prefer
    cli2 run instead of cli2 alone in automated scripts, as well as cli2 help
    run for details about parameterized execution. However, using cli2 directly
    on the command line for interactive use is fine.
    """
    if callback:
        try:
            yield from run(callback, *args, **kwargs)
        except Exception:
            yield from debug(callback, *args, **kwargs)
            raise
    else:
        yield from help()


def debug(callback, *args, **kwargs):
    """
    Dump parsed variables.

    Example usage::

        cli2 debug test to=see --how -it=parses
    """
    cs = console_script
    parser = cs.parser
    yield textwrap.dedent(f'''
    Callable: {RED}{callback}{RESET}
    Args: {YELLOW}{args}{RESET}
    Kwargs: {YELLOW}{kwargs}{RESET}
    console_script.parser.dashargs: {GREEN}{parser.dashargs}{RESET}
    console_script.parser.dashkwargs: {GREEN}{parser.dashkwargs}{RESET}
    console_script.argv_extra: {GREEN}{cs.argv_extra}{RESET}
    ''').strip()


def run(callback, *args, **kwargs):
    """
    Execute a python callback on the command line.

    To call your.module.callback('arg1', 'argN', kwarg1='foo'):

        cli2 your.module.callback arg1 argN kwarg1=foo

    You can also prefix arguments with a dash, those that contain equal sign
    will end in dict your_console_script.parser.dashkwargs, those without equal
    sign will end up in a list in your_console_script.parser.dashargs.

    If you're using the default cli2.console_script then you can import it. If
    you don't know what console_script instance, use
    cli2.guess_console_script() which will inspect the call stack and return
    what it believes is the ConsoleScript instance currently in use.

    For examples, try `cli2 debug`.
    For other commands, try `cli2 help`.
    """
    path = Path(callback)

    if path.callable:
        result = path.callable(*args, **kwargs)
        if isinstance(result, types.GeneratorType):
            yield from result
        else:
            return result
    else:
        if '.' in callback:
            yield f'{RED}Could not import callback: {callback}{RESET}'
        else:
            yield f'{RED}Cannot run a module{RESET}: try {callback}.something'

        if path.module:
            yield ' '.join([
                'However we could import module',
                f'{GREEN}{path.module_name}{RESET}',
                'Listing callables in module below:',
            ])

            doc = docfile(path.module.__file__)
            if doc:
                yield from doc
            return f'Docstring not found in {path.module_name}'
        elif callback != callback.split('.')[0]:
            yield ' '.join([
                f'{RED}Could not import module:',
                f'{callback.split(".")[0]}{RESET}'
            ])


class ConsoleScript:
    _cli2_exclude = True

    def __init__(self, argv):
        self.argv = argv
        self.group = Group(self.argv[0])
        self.argv_extra = []

    @property
    def command(self):
        if '_command' not in self.__dict__:
            self._command, self.argv_extra = self.group.find_command(self.argv)
        return self._command

    def get_result(self):
        if not self.command or not self.command.path.callable:
            return f'No callback found for command {self.command}'

        setup = getattr(self.command.path.module, '_cli2_setup', None)
        if setup:
            setup()

        self.parser = Parser(self.argv_extra)

        try:
            result = self.command(
                *self.parser.funcargs,
                **self.parser.funckwargs
            )
        except Cli2Exception as e:
            result = '\n'.join([str(e), '', self.command.path.docstring])
        except Exception:
            raise
        finally:
            clean = getattr(self.command.path.module, '_cli2_clean', None)
            if clean:
                clean()

        return result

    def handle_result(self, result):
        if isinstance(result, str):
            print(result)
        else:
            pprint.PrettyPrinter(indent=4).pprint(result)

    def __call__(self):
        # patch cli2.console_script
        global console_script
        console_script = self

        if not self.command or not self.command.path.callable:
            return f'No callback found for command {self.command}'

        self.parser = Parser(self.argv_extra)

        colorama.init()

        setup = getattr(self.command.path.module, '_cli2_setup', None)
        if setup:
            setup()

        try:
            result = self.command(
                *self.parser.funcargs,
                **self.parser.funckwargs
            )
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
            clean = getattr(self.command.path.module, '_cli2_clean', None)
            if clean:
                clean()

        return result if isinstance(result, int) else 0


console_script = ConsoleScript(sys.argv)
