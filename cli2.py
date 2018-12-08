'''cli2 makes your python callbacks work on CLI too !

cli2 provides sub-commands to introspect python modules or callables docstrings
or to execute callables or help working with cli2 itself.
'''

import collections
import inspect
import importlib
import pkg_resources
import pprint
import textwrap
import types
import shutil
import sys

import colorama


class Cli2Exception(Exception):
    pass


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

        if self.module:
            ret = self.module
            for part in self.parts[i + 1:]:
                if isinstance(ret, dict) and part in ret:
                    ret = ret.get(part)
                elif isinstance(ret, list) and part.isnumeric():
                    ret = ret[int(part)]
                else:
                    ret = getattr(ret, part, None)

                if ret.__class__.__name__ == 'module':
                    self.module = ret

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
        return filedoc(self.module.__file__)

    @property
    def callable_docstring(self):
        return inspect.getdoc(self.callable)

    @property
    def docstring(self):
        return (
            self.callable_docstring
            if self.callable
            else self.module_docstring
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
        return self.path.callable(*(self.args or args), **kwargs)

    @classmethod
    def factory(cls, entrypoint):
        line = entrypoint.name
        if '*' not in line:
            args = None
            target = entrypoint.module_name

            if entrypoint.attrs:
                try:
                    entrypoint.load()
                except ImportError:
                    args = entrypoint.attrs
                else:
                    target = '.'.join((
                        entrypoint.module_name,
                        " ".join(entrypoint.attrs),
                    ))
            yield cls(line, target, args)

        else:
            right = line[line.index('*') + 1:].strip()
            path = Path(entrypoint.module_name)
            for name in path.module_callables:
                yield cls(
                    ' '.join((name, right)).strip(),
                    f'{path.module_name}.{name}'
                )


class Group:
    def __init__(self, name, entrypoints=None):
        self.name = name.split('/')[-1]          # strip FS path details
        self.name = self.name.replace('-', '_')  # entry point name forbids

        self.commands = collections.OrderedDict()
        self.load_entrypoints(
            entrypoints
            or pkg_resources.iter_entry_points('cli2_' + self.name)
        )

    def load_entrypoints(self, entrypoints):
        for ep in entrypoints:
            for command in Command.factory(ep):
                if command.line not in self.commands:
                    self.commands[command.line] = command


def filedoc(filepath):
    """Docstring for a file path."""
    co = compile(open(filepath).read(), filepath, 'exec')
    if co.co_consts and isinstance(co.co_consts[0], str):
        docstring = co.co_consts[0]
    else:
        docstring = None
    return docstring


def moddoc(module_name, group_name=None):
    """Docstring for a module name."""
    path = Path(module_name)
    yield filedoc(path.module.__file__).strip() + '\n'

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

            line = '  ' + line + (width - len(line)) * ' '
            if cmd.path.callable:
                doc = inspect.getdoc(cmd.path.callable)

                if doc:
                    line += doc.split('\n')[0][:termwidth - len(line)]
                else:
                    line += 'Docstring not found'
            else:
                line += 'Callback not found'

            yield line


def help(*args, **kwargs):
    """
    Get help for a callable, or list callables for a module.

    Example::

        $ cli2 help foo.bar
    """
    if args:
        extra = ' '.join(args)
        try:
            path = console_script.group.commands[extra].path
        except KeyError:
            path = Path(args[0])

        if path.callable:
            yield f'Docstring for {path}'
            yield path.docstring
        elif path.module:
            yield f'Docstring for module {path.module_name}'
            yield path.module_docstring
        else:
            yield f'Command not found {console_script.command_name} {extra}'

    else:
        # fuzzy workaround for when you have not bount cli2.help:yourmodule but
        # only have cli2.help or cli2:help on the main ep for some reason.
        default_module_name = console_script.command_name.replace('-', '_')
        for line in moddoc(default_module_name, console_script.group.name):
            yield line


def main(callback=None, *args, **kwargs):
    if not callback:
        return help()
    return run(callback, *args, **kwargs)
main._cli2_exclude = True  # noqa


def debug(callback, *args, **kwargs):
    """Dump parsed variables"""
    colorama.init()
    cs = console_script
    parser = console_script.parser
    green = colorama.Fore.GREEN
    red = colorama.Fore.RED
    yellow = colorama.Fore.YELLOW
    reset = colorama.Style.RESET_ALL
    return textwrap.dedent(f'''
    Callable: {red}{callback}{reset}
    Args: {yellow}{args}{reset}
    Kwargs: {yellow}{kwargs}{reset}
    console_script.parser.dashargs: {green}{parser.dashargs}{reset}
    console_script.parser.dashkwargs: {green}{parser.dashkwargs}{reset}
    console_script.argv_extra: {green}{cs.argv_extra}{reset}
    ''').strip()


def run(callback, *args, **kwargs):
    """Execute a parameterized python callback."""
    path = Path(callback)

    if not path.callable:
        if path.module:
            doc = filedoc(path.module.__file__)
            if doc:
                return doc
            return f'Docstring not found in {path.module_name}'
        return f'Could not import argument: {callback}'
    return path.callable(*args, **kwargs)


class ConsoleScript:
    def __init__(self, argv):
        self.argv = argv
        self.group = Group(self.argv[0])
        self.argv_extra = []

        cmd = self.command_name = self.argv[0].split('/')[-1]
        args = ' '.join(self.argv[1:])

        self.command = None
        for line, command in self.group.commands.items():
            if args.startswith(command.line) or command.line == cmd:
                self.command = command
                break

        if not self.command:
            print(f'No command for {" ".join(self.argv)}')

        else:
            offset = 1
            if command.line != self.command_name:
                offset += 1
            self.argv_extra = self.argv[self.command.line.count(' ') + offset:]

    def get_result(self):
        if not self.command or not self.command.path.callable:
            return f'No callback found for command {self.command}'

        self.parser = Parser(self.argv_extra)
        return self.command(
            *self.parser.funcargs,
            **self.parser.funckwargs,
        )

    def handle_result(self, result):
        if isinstance(result, str):
            print(result)
        else:
            pprint.PrettyPrinter(indent=4).pprint(result)

    def __call__(self):
        result = self.get_result()

        if isinstance(result, (types.GeneratorType, list)):
            for r in result:
                self.handle_result(r)
        else:
            if isinstance(result, int):
                return result  # exit code ?

            self.handle_result(result)


console_script = ConsoleScript(sys.argv)
console_script._cli2_exclude = True
