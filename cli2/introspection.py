import collections
import inspect
import importlib
import types
import os

from .colors import GREEN, RED, RESET, YELLOW
from .exceptions import Cli2Exception, Cli2ArgsException


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


class DocDescriptor:
    def __get__(self, obj, objtype):
        if obj.is_module:
            if 'value' in self.__dict__:
                return self.value

            # Only show module docstring
            if obj.module:
                from .cli import docfile
                return docfile(obj.module.__file__)
            else:
                return f'No docstring found for {obj}'

        elif obj.target:
            # Show callable docstring + signature
            ret = []
            if callable(obj.target):
                # TODO: enhance output of the signature help
                sig = ''
                try:
                    sig = inspect.signature(obj.target)
                except ValueError:
                    pass
                ret.append(''.join([
                    f'Signature: {GREEN}{obj.name}{RESET}',
                    f'{sig}'
                ]))

            if 'value' in self.__dict__:
                ret.append(self.value)
            else:
                ret.append(inspect.getdoc(obj.target) or 'No docstring found')

            if obj.options:
                ret += ['', 'Extra CLI options:', '']
                width = len(max(obj.options.keys(), key=len)) + 4

                for name, option in obj.options.items():
                    ret.append('  ' + ''.join([
                        option.color,
                        f'--{name},-{option.alias}'
                        if option.alias else f'--{name}',
                        RESET,
                        (width - len(name) + 2) * ' ',
                        option.help,
                    ]))

            return '\n'.join(ret)

    def __set__(self, obj, value):
        self.value = value


class Importable:
    doc = DocDescriptor()

    def __init__(self, name, target, module=None):
        self.name = name
        self.target = target

        if module:
            self.module = module
        elif isinstance(target, types.ModuleType):
            self.module = target
        elif target:
            self.module = target.__module__
        else:
            self.module = None

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

            candidate = getattr(ret, 'cli2', None)
            if isinstance(candidate, Callable):
                return ret.cli2

            if module != ret:
                cls = Callable
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

            if not hasattr(member, '__name__'):
                continue

            yield Callable(name, member)

    @property
    def is_module(self):
        return self.module == self.target


class Callable(Importable):
    doc = DocDescriptor()

    def __init__(self, name, target, module=None, color=None, options=None,
                 doc=None):

        super().__init__(name, target, module=module)
        self.color = color or YELLOW
        self.options = options or collections.OrderedDict()

    @classmethod
    def for_callback(cls, cb):
        return getattr(cb, 'cli2', cls(cb.__name__, cb))

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
