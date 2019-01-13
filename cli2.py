'''cli2 makes your python callbacks work on CLI too !

cli2 provides sub-commands to introspect python modules or callables docstrings
or to execute callables or help working with cli2 itself.
'''

import copy
import collections
import importlib
import inspect
import io
import os
import pkg_resources
import pprint
import re
import shlex
import sys
import textwrap
import types
import subprocess
from unittest import mock

import colorama


GREEN = colorama.Fore.GREEN
RED = colorama.Fore.RED
YELLOW = colorama.Fore.YELLOW
RESET = colorama.Style.RESET_ALL


class Config(dict):
    defaults = dict(
        color=YELLOW,
    )

    def __init__(self, **options):
        cfg = copy.copy(self.defaults)
        cfg.update(options)
        super().__init__(cfg)

    def __get__(self, obj, objtype):
        config = getattr(obj.target, 'cli2', None)
        if isinstance(config, dict):
            return Config(**config)
        elif config is None:
            return self
        return config

    def __getattr__(self, name):
        return self[name]


def config(**config):
    def wrap(cb):
        cb.cli2 = Config(**config)
        return cb
    return wrap


# don't do this, use @cli2.config(options...) or a class instead
config.cli2 = dict(blacklist=True)


@config(blacklist=True)
def autotest(path, cmd, ignore=None):
    """
    The autowriting test pattern, minimal for testing cli2 scripts.

    Example:

        cli2.autotest(
            'tests/djcli_save_user.txt',
            'djcli',
            'save',
            'auth.User',
            'username="test"',
        )

        cli2.autotest(
            'tests/djcli_ls_user.txt',
            'djcli',
            'ls',
            'auth.User'
        )
    """
    name = cmd.split(' ')[0]
    for ep in pkg_resources.iter_entry_points('console_scripts'):
        if ep.name == name:
            break

    if ep.name != name:
        raise Exception('Could not find entrypoint {name}')

    console_script = ep.load()
    console_script.argv = shlex.split(cmd)[1:]

    @mock.patch('sys.stderr', new_callable=io.StringIO)
    @mock.patch('sys.stdout', new_callable=io.StringIO)
    def test(mock_stdout, mock_stderr):
        console_script()
        return mock_stdout, mock_stderr

    out, err = test()

    out.seek(0)
    test_out = out.read()

    err.seek(0)
    test_err = err.read()

    fixture = '\n'.join([
        'command: ' + cmd,
        'retcode: ' + str(console_script.exit_code),
        'stdout:',
        test_out,
    ])
    if test_err:
        fixture += '\n'.join([
            'stderr:',
            test_err,
        ])

    for r in ignore or []:
        fixture = re.compile(r).sub(f'redacted', fixture)

    if not os.path.exists(path):
        dirname = '/'.join(path.split('/')[:-1])
        if not os.path.exists(dirname):
            os.makedirs(dirname)

        with open(path, 'w+') as f:
            f.write(fixture)

        raise type('FixtureCreated', (Exception,), {})(
            f'''
{path} was not in workding and was created with:
{fixture}
            '''.strip(),
        )

    cmd = 'diff -U 1 - "%s" | sed "1,2 d"' % path
    proc = subprocess.Popen(
        cmd,
        stdout=subprocess.PIPE,
        stdin=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        shell=True
    )

    diff_out, diff_err = proc.communicate(input=fixture.encode('utf8'))
    if diff_out:
        raise type(f'''
DiffFound
- test output capture
+ {path}
        '''.strip(), (Exception,), {})('\n' + diff_out.decode('utf8'))


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


@config(color=GREEN)
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
        # show command documentation if possible
        if args[0] in console_script:
            yield console_script[args[0]].doc
        else:
            importable = Importable.factory(args[0])
            if importable.target and not importable.is_module:
                yield importable.doc
            elif importable.module:
                if not importable.target:
                    yield f'{RED}Cannot import {args[0]}{RESET}'
                    yield ' '.join([
                        YELLOW,
                        'Showing help for',
                        importable.module.__name__ + RESET
                    ])
                yield Group.factory(importable.module.__name__).doc


@config(color=GREEN)
def docfile(filepath):
    """
    Docstring for a file path.

    Examples:

        cli2 docfile cli2.py
    """
    if not os.path.exists(filepath):
        raise Cli2Exception(f'{RED}{filepath}{RESET} not found')
    try:
        co = compile(open(filepath).read(), filepath, 'exec')
    except SyntaxError:
        print(f'{RED}SyntaxError in {filepath}{RESET} shown below:')
        raise
    if co.co_consts and isinstance(co.co_consts[0], str):
        docstring = co.co_consts[0]
    else:
        docstring = None
    return docstring


@config(color=GREEN)
def docmod(module_name):
    """Docstring for a module in dotted path.

    Example: cli2 docmod cli2
    """
    return Group.factory(module_name).doc


@config(color=GREEN)
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
    ''').strip()


def run(callback, *args, **kwargs):
    """
    Execute a python callback on the command line.

    To call your.module.callback('arg1', 'argN', kwarg1='foo'):

        cli2 your.module.callback arg1 argN kwarg1=foo

    You can also prefix arguments with a dash, those that contain equal sign
    will end in dict console_script.parser.dashkwargs, those without equal
    sign will end up in a list in console_script.parser.dashargs.

    For examples, try `cli2 debug`.
    For other commands, try `cli2 help`.
    """
    cb = Callable.factory(callback)

    if cb.target and not cb.is_module:
        try:
            result = cb(*args, **kwargs)
        except Cli2ArgsException as e:
            print(e)
            print(cb.doc)
            result = None
            console_script.exit_code = 1
        except Exception as e:
            out = [f'{RED}Running {callback}(']
            if args and kwargs:
                out.append(f'*{args}, **{kwargs}')
            elif args:
                out.append(f'*{args}')
            elif kwargs:
                out.append(f'**{kwargs}')
            out.append(f') raised {type(e)}{RESET}')

            e.args = (e.args[0] + '\n' + cb.doc,) + e.args[1:]
            raise

        if isinstance(result, types.GeneratorType):
            yield from result
        else:
            yield result

    else:
        if '.' in callback:
            yield f'{RED}Could not import callback: {callback}{RESET}'
        else:
            yield f'{RED}Cannot run a module{RESET}: try {callback}.something'

        if cb.module:
            yield ' '.join([
                'However we could import module',
                f'{GREEN}{cb.module.__name__}{RESET}',
            ])

            doc = docmod(cb.module.__name__)
            if doc:
                yield f'Showing help for {GREEN}{cb.module.__name__}{RESET}:'
                yield doc
            else:
                return f'Docstring not found in {cb.module.__name__}'
        elif callback != callback.split('.')[0]:
            yield ' '.join([
                RED,
                'Could not import module:',
                callback.split('.')[0],
                RESET,
            ])


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
            # Only show module docstring
            return docfile(obj.module.__file__)
        elif obj.target:
            # Show callable docstring + signature
            ret = []
            if callable(obj.target):
                # TODO: enhance output of the signature help
                ret.append(''.join([
                    f'Signature: {GREEN}{obj.name}{RESET}',
                    f'{inspect.signature(obj.target)}'
                ]))
            ret.append(inspect.getdoc(obj.target) or 'No docstring found')
            return '\n'.join(ret)

    def __set__(self, obj, value):
        self.value = value


class Importable:
    doc = DocDescriptor()

    def __init__(self, name, target, module=None):
        self.name = name
        self.target = target

        if isinstance(target, types.ModuleType):
            self.module = target
        elif target:
            self.module = target.__module__
        else:
            self.module = module

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
        else:
            ret = None

        return cls(name, ret, module)

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

            cfg = getattr(member, 'cli2', {})
            if cfg.get('blacklist', False):
                continue

            yield Callable(name, member)

    @property
    def is_module(self):
        return self.module == self.target


class Callable(Importable):
    doc = DocDescriptor()

    def __call__(self, *args, **kwargs):
        if len(args) < len(self.required_args):
            raise Cli2ArgsException(self, args)
        return self.target(*args, **kwargs)

    @property
    def required_args(self):
        if self.is_module:
            return []
        argspec = inspect.getfullargspec(self.target)
        if argspec.defaults:
            return argspec.args[:-len(argspec.defaults)]
        else:
            return argspec.args


class Command(Callable):
    cli2 = Config()


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
            line = '  ' + ''.join([
                cmd.cli2.color,
                line,
                RESET,
                (width - len(line)) * ' '
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
        self.doc = doc or 'Documentation not set'
        self['help'] = Command('help', help)

    def add_module(self, module_name):
        importable = Importable.factory(module_name)

        if not importable.module:
            raise Cli2Exception('Module not found' + importable.module)

        for cb in importable.get_callables():
            self[cb.name] = Command(cb.name, cb.target)

        return self

    @classmethod
    def factory(cls, module_name):
        doc = Importable.factory(module_name).doc
        return cls(module_name, doc).add_module(module_name)


class ConsoleScript(Group):
    cli2 = dict(blacklist=True)

    def __init__(self, doc=None, argv=None, default_command='help'):
        # update cli2.console_script the singl370n in __1n17__ so it works
        # in tests too :D for runtime only it can be in __call__
        global console_script
        console_script = self

        self.default_command = default_command
        argv = argv if argv is not None else sys.argv
        Group.__init__(self, argv[0].split('/')[-1], doc)
        self.argv = argv[1:]
        self.exit_code = 0

    def parse(self):
        if len(self.argv) and self.argv[0] in self:
            command = self[self.argv[0]]
            parse_argv = self.argv[1:]
        else:
            command = self[self.default_command]
            parse_argv = self.argv

        # if not self.command or not command.path.callable:
        #    return f'No callback found for command {self.command}'

        self.parser = Parser(parse_argv)
        return command

    def __call__(self):
        colorama.init()
        command = self.parse()

        result = None
        try:
            result = self.call(command)
            if isinstance(result, (types.GeneratorType, list)):
                for r in result:
                    self.result_handler(r)
            else:
                self.result_handler(result)
        except Cli2ArgsException as e:
            self.exit_code = 1
            print('\n'.join([str(e), '', command.doc]))
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


console_script = ConsoleScript(
    __doc__,
    default_command='run'
).add_module('cli2')
