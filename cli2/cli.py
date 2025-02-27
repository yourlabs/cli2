import asyncio
import importlib.metadata
import inspect
import json
import os
import re
import sys
import textwrap

from docstring_parser import parse

from . import display
from .asyncio import async_resolve
from .colors import colors


class Overrides(dict):
    """
    Lazy overrides dict
    """
    def __getitem__(self, key):
        if key not in self:
            self[key] = dict()
        return super().__getitem__(key)


def cmd(*args, **overrides):
    """Set the overrides for a command."""
    def wrap(cb):
        cb = cb.__func__ if inspect.ismethod(cb) else cb
        if 'doc' in overrides:
            overrides['doc'] = textwrap.dedent(overrides['doc']).strip()
        cb.cli2 = overrides
        return cb

    if args and not overrides:
        return wrap(args[0])

    return wrap


def arg(name, **kwargs):
    """Set the overrides for an argument."""
    def wrap(cb):
        cb = cb.__func__ if inspect.ismethod(cb) else cb
        overrides = getattr(cb, 'cli2_' + name, None)
        if overrides is None:
            try:
                setattr(cb, 'cli2_' + name, {})
            except AttributeError:
                setattr(cb.__func__, 'cli2_' + name, {})
        try:
            overrides = getattr(cb, 'cli2_' + name)
        except AttributeError:
            overrides = getattr(cb.__func__, 'cli2_' + name)
        overrides.update(kwargs)
        return cb
    return wrap


def hide(*names):
    def wrap(cb):
        for name in names:
            cb = arg(name, hide=True)(cb)
        return cb
    return wrap


def retrieve(path):
    # find all matching entrypoints
    name = path.split(" ")[0]
    matches = [
        entry_point
        for entry_point in importlib.metadata.entry_points()
        if entry_point.name == name
        and entry_point.group == 'console_scripts'
    ]

    if not matches:
        raise Exception(f'Entry point {path} not installed')

    # take the first entry point, navigate up to the target sub-command
    obj = matches[0].load().__self__
    obj.name = name
    obj.parent = None
    for arg in path.split(" ")[1:]:
        obj = obj[arg]
    return obj


class EntryPoint:
    def __init__(self, *args, outfile=None, log=True, **kwargs):
        self.outfile = outfile or sys.stdout
        self.exit_code = 0
        super().__init__(*args, **kwargs)

    def entry_point(self, *args):
        args = args or sys.argv
        self.name = os.path.basename(args[0])

        result = self(*args[1:])
        if result is not None:
            try:
                display.print(result)
            except:  # noqa
                print(result)
        sys.exit(self.exit_code)

    def print(self, *args, sep=' ', end='\n', file=None, color=None):
        if args and args[0].lower() in colors.__dict__ and not color:
            color = args[0]
            args = args[1:]
            if color.lower() != color:
                color = color.lower() + 'bold'
            color = getattr(colors, color)

        msg = sep.join(map(str, args))

        if color:
            msg = color + msg + colors.reset

        print(msg, end=end, file=file or self.outfile, flush=True)

    @property
    def path(self):
        """
        Return the CLI sub-command path.
        """
        current = self
        chain = []
        while current is not None:
            chain.insert(0, current.name)
            current = current.parent
        return " ".join(chain)

    @property
    def doc_short(self):
        """
        Return the first sentence of the documentation.
        """
        tokens = []
        for line in self.doc.strip().split('\n'):
            if not line.strip():
                break
            tokens.append(line)
        return ' '.join(tokens).rstrip('.') if tokens else ''


class Group(EntryPoint, dict):
    """Represents a group of named commands."""

    def __init__(self, name=None, doc=None, color=None, posix=False,
                 overrides=None, outfile=None, cmdclass=None, log=True):
        self.name = name
        if doc:
            self.doc = textwrap.dedent(doc).strip()
        else:
            self.doc = inspect.getdoc(self)
        self.color = color or colors.green
        self.posix = posix
        self.parent = None
        self.cmdclass = cmdclass or Command
        self.overrides = overrides or dict()
        EntryPoint.__init__(self, outfile=outfile, log=log)

        # make help a group command
        self.cmd(self.help, cls=Command)

    @property
    def overrides(self):
        return self._overrides

    @overrides.setter
    def overrides(self, value):
        self._overrides = Overrides(value)

    def add(self, target, *args, **kwargs):
        """Add a new target as sub-command."""
        cmdclass = kwargs.pop('cls', self.cmdclass)
        cmd = cmdclass(target, *args, **kwargs)
        self[cmd.name] = cmd
        cmd.group = self
        return self

    def __setitem__(self, key, value):
        if isinstance(value, Group):
            value.name = key
        value.posix = self.posix
        value.parent = self
        value.outfile = self.outfile
        super().__setitem__(key, value)

    def cmd(self, *args, **kwargs):
        """Decorator to add a command with optionnal overrides."""
        if len(args) == 1:
            # simple @group.cmd syntax or direct call
            target = args[0]
            self.add(target, **kwargs)
            return target
        elif not args:
            def wrap(cb):
                self.add(cb, **kwargs)
                return cb
            return wrap

    def arg(self, name, **kwargs):
        return arg(name, **kwargs)

    def group(self, name, grpclass=None, **kwargs):
        """Return a new sub-group."""
        kwargs.setdefault('cmdclass', self.cmdclass)
        grpclass = grpclass or Group
        self[name] = grpclass(name, **kwargs)
        return self[name]

    def help(self, *args, error=None, short=False):
        """
        Get help for a command or group.

        :param args:  Command or sub-command chain to show help for.
        :param error: Error message to print out.
        :param short: Show short documentation.
        """
        if args:
            target = self
            for arg in args:
                if arg in target:
                    target = target[arg]
                elif isinstance(target, Command):
                    return target.help(error=error, short=short)
                else:
                    error = f'Command {arg} not found in {target}'
                    break
            return target.help(error=error, short=short)

        if short:
            if self.doc:
                return self.doc_short
            return ''

        if error:
            self.print('RED', 'ERROR: ' + colors.reset + error, end='\n\n')

        self.print('ORANGE', 'SYNOPSYS')
        chain = []
        current = self
        while current:
            chain.insert(0, current)
            current = current.parent
        self.print(' '.join(map(str, chain)) + ' SUB-COMMAND <...>')
        self.print(' '.join(map(str, chain)) + ' help SUB-COMMAND')
        if len(chain) > 1:
            chain.insert(1, 'help')
            self.print(' '.join(map(str, chain)) + ' SUB-COMMAND')
        self.print()

        if self.doc:
            self.print('ORANGE', 'DESCRIPTION')
            self.print(self.doc.strip())
            self.print()

        from .table import Table
        table = Table(*[
            (
                (
                    getattr(colors, command.color, command.color),
                    name,
                ),
                command.help(short=True),
            )
            for name, command in self.items()
        ])
        self.print('ORANGE', 'SUB-COMMANDS')
        table.print(self.print)
    help.cli2 = dict(color='green')

    def load(self, obj):
        if isinstance(obj, type):
            return self.load_cls(obj)
        return self.load_obj(obj)

    def load_cls(self, cls, leaf=None):
        """
        Load all methods which have been decorated with @cmd

        Note that you can define conditions, this is how we hide functions such
        as create/delete/get from models without url_list:

        .. code-block:: python

            @cli2.cmd(condition=lambda cls: cls.url_list)
        """
        final = leaf if leaf else cls
        for base in cls.__bases__:
            self.load_cls(base, leaf=final)

        for name, method in cls.__dict__.items():
            if name.startswith('_'):
                continue
            if leaf and getattr(final, name, '_') is None:
                continue
            self.load_method(final, method)

    def load_obj(self, obj):
        """
        Load all methods which have been decorated with @cmd
        """
        for name in dir(obj):
            if name.startswith('_'):
                continue
            if not callable(getattr(type(obj), name)):
                continue
            self.load_method(obj, getattr(obj, name))

    def load_method(self, obj, method):
        wrapped_method = getattr(method, '__func__', None)
        cfg = getattr(
            wrapped_method,
            'cli2',
            getattr(method, 'cli2', None),
        )
        if cfg is None:
            return
        condition = cfg.get('condition', None)
        if condition:
            if not condition(obj):
                return
        self.cmd(wrapped_method or method)

    def __call__(self, *argv):
        self.exit_code = 0
        if not argv:
            return self.help(error='No sub-command provided')

        if argv[0] in self:
            result = self[argv[0]](*argv[1:])
            # fetch exit code
            self.exit_code = self[argv[0]].exit_code
        else:
            return self.help(error=f'Command {argv[0]} not found')

        return result

    def __repr__(self):
        return f'Group({self.name})'

    def __str__(self):
        return self.name or ''


class Command(EntryPoint, dict):
    """Represents a command bound to a target callable."""

    def __new__(cls, target, *args, **kwargs):
        overrides = getattr(target, 'cli2', {})
        cls = overrides.get('cls', cls)
        return super().__new__(cls, *args, **kwargs)

    def __init__(self, target, name=None, color=None, doc=None, posix=False,
                 help_hack=True, outfile=None, log=True, overrides=None):
        self.posix = posix
        self.parent = None
        self.help_hack = help_hack
        self._overrides = Overrides(overrides or dict())
        self._overrides['_cli2']['factory'] = lambda: self

        self.target = target

        overrides = getattr(target, 'cli2', {})
        for key, value in overrides.items():
            setattr(self, key, value)

        if name:
            self.name = name
        elif 'name' not in overrides:
            self.name = getattr(target, '__name__', type(target).__name__)

        self.parsed = parse(inspect.getdoc(self.target))
        if doc:
            self.doc = doc
        elif 'doc' not in overrides:
            if self.parsed.description:
                self.doc = self.parsed.description.strip()
            else:
                self.doc = ''

        if color:
            self.color = color
        elif 'color' not in overrides:
            self.color = 'orange'

        self.positions = dict()
        EntryPoint.__init__(self, outfile=outfile, log=log)
        self.args_set = False
        self.args_setting = False

    @property
    def overrides(self):
        return self._overrides

    @overrides.setter
    def overrides(self, value):
        self._overrides = Overrides(value)

    def get_overrides(self, name, target=None):
        target = target or self.target
        overrides = getattr(target, 'cli2_' + name, {})

        for key, value in self.overrides[name].items():
            overrides.setdefault(key, value)

        group = getattr(self, 'group', None)
        if group and name in group.overrides:
            for key, value in group.overrides[name].items():
                overrides.setdefault(key, value)

        return overrides

    @property
    def target(self):
        target = self._target

        if not inspect.ismethod(target):
            return target

        if self.name == 'help':
            return target

        # let's allow overwriting a bound method's __self__
        func_sig = inspect.signature(target.__func__)
        self_name = [*func_sig.parameters.keys()][0]
        if 'factory' in self.get_overrides(self_name, target):
            self.target = target = target.__func__

        return target

    @target.setter
    def target(self, value):
        self._target = value

    @property
    def sig(self):
        return inspect.signature(self.target)

    def __getitem__(self, key):
        self._setargs()
        return super().__getitem__(key)

    def _setargs(self):
        if self.args_set or self.args_setting:
            return
        self.args_setting = True
        self.setargs()
        self.args_set = True

    def setargs(self):
        """Reset arguments."""
        for name, param in self.sig.parameters.items():
            overrides = self.get_overrides(name)
            cls = overrides.get('cls', Argument)
            self[name] = cls(self, param)
            for key, value in overrides.items():
                setattr(self[name], key, value)

    @classmethod
    def cmd(cls, *args, **kwargs):
        def override(target):
            overrides = getattr(target, 'cli2', {})
            overrides.update(kwargs)
            overrides['cls'] = cls
            target.cli2 = overrides

        if len(args) == 1 and not kwargs:
            # simple @YourCommand.cmd syntax
            target = args[0]
            override(target)
            return target
        elif not args:
            def wrap(cb):
                override(cb)
                return cb
            return wrap
        else:
            raise Exception('Only kwargs are supported by Group.cmd')

    def help(self, error=None, short=False, missing=None):
        """Show help for a command."""
        self._setargs()
        if short:
            if self.doc:
                return self.doc_short
            return ''

        if missing:
            error = (
                f'missing {len(missing)} required argument'
                f'{"s" if len(missing) > 1 else ""}'
                f': {", ".join(missing)}'
            )

        if error:
            self.print('RED', 'ERROR: ' + colors.reset + error, end='\n\n')

        self.print('ORANGE', 'SYNOPSYS')
        chain = []
        current = self
        while current is not None:
            chain.insert(0, current.name)
            current = current.parent
        for arg in self.values():
            if not arg.hide:
                chain.append(str(arg))
        self.print(' '.join(map(str, chain)), end='\n\n')

        self.print('ORANGE', 'DESCRIPTION')
        self.print(self.doc)

        shown_posargs = False
        shown_kwargs = False
        for arg in self.values():
            if arg.hide:
                continue

            self.print()

            varkw = arg.param.kind == arg.param.VAR_KEYWORD

            if not arg.iskw and not varkw and not shown_posargs:
                self.print('ORANGE', 'POSITIONAL ARGUMENTS')
                shown_posargs = True

            if (arg.iskw or varkw) and not shown_kwargs:
                self.print('ORANGE', 'NAMED ARGUMENTS')
                shown_kwargs = True
            arg.help()

    def parse(self, *argv):
        """Parse arguments into BoundArguments."""
        self._setargs()
        self.bound = self.sig.bind_partial()
        extra = []
        for current in argv:
            taken = False
            for arg in self.values():
                taken = arg.take(current)
                if taken:
                    break

            if not taken:
                extra.append(current)

        if extra:
            return 'No parameters for these arguments: ' + ', '.join(extra)

        for name, arg in self.items(factories=None):
            if arg.factory:
                if self.async_function(arg.factory):
                    arg.value = 'to_be_computed'
                else:
                    arg.value = arg.factory_value()
                continue
            if not arg.default:
                continue
            if name in self.bound.arguments:
                continue
            arg.value = arg.default

    def async_function(self, function):
        """ Return True if function is async """
        return (
            inspect.iscoroutinefunction(function)
            or inspect.isasyncgenfunction(function)
        )

    def async_mode(self):
        """ Return True if any callable we'll deal with is async """
        for arg in self.values():
            if self.async_function(arg.factory):
                return True
        if (
            self.async_function(self.target)
            or self.async_function(self.post_call)
        ):
            return True

        for name, arg in self.items(factories=True):
            if arg.factory and self.async_function(arg.factory):
                return True
        return False

    def call(self, *args, **kwargs):
        """Execute command target with bound arguments."""
        return self.target(*args, **kwargs)

    def missing(self):
        return [
            name
            for name, arg in self.items()
            if name not in self.bound.arguments
            and name not in self.bound.kwargs
            and arg.param.default == arg.param.empty
            and arg.param.kind in (
                arg.param.POSITIONAL_ONLY,
                arg.param.POSITIONAL_OR_KEYWORD,
            )
        ]

    def __call__(self, *argv):
        """Execute command with args from sysargs."""
        self.exit_code = 0

        if self.help_hack and '--help' in argv:
            self.exit_code = 1
            return self.help()

        if self.async_mode():
            try:
                return asyncio.run(self.async_call(*argv))
            except KeyboardInterrupt:
                print('exiting cleanly...')
                self.exit_code = 1
                return
            finally:
                self.post_result = asyncio.run(async_resolve(self.post_call()))

        error = self.parse(*argv)
        if error:
            self.exit_code = 1
            return self.help(error=error)

        missing = self.missing()
        if missing:
            self.exit_code = 1
            return self.help(missing=missing)

        try:
            result = self.call(*self.bound.args, **self.bound.kwargs)
            if inspect.isgenerator(result):
                for _ in result:
                    display.print(_)
                result = None
            return result
        except KeyboardInterrupt:
            print('exiting cleanly...')
            self.exit_code = 1
        finally:
            self.post_result = self.post_call()

    async def async_call(self, *argv):
        """ Call with async stuff in single event loop """
        error = self.parse(*argv)
        if error:
            self.exit_code = 1
            return self.help(error=error)

        missing = self.missing()
        if missing:
            self.exit_code = 1
            return self.help(missing=missing)

        await self.factories_resolve()

        result = self.call(*self.bound.args, **self.bound.kwargs)
        return await async_resolve(result, output=True)

    async def factories_resolve(self):
        """ Resolve all factories values. """
        factories = self.values(factories=True)
        if factories:
            results = await asyncio.gather(*[
                async_resolve(arg.factory_value())
                for arg in factories
            ])
            for _, arg in enumerate(factories):
                arg.value = results[_]

    def ordered(self, factories=False):
        """
        Order the parameters by priority.

        :param factories: Show only arguments with factory.
        """
        return {key: self[key] for key in self.keys(factories=factories)}

    def values(self, factories=False):
        """
        Return ordered values.

        :param factories: Show only arguments with factory.
        """
        return self.ordered(factories=factories).values()

    def items(self, factories=False):
        """
        Return ordered items.

        :param factories: Show only arguments with factory.
        """
        return self.ordered(factories=factories).items()

    def keys(self, factories=False):
        """
        Return ordered keys.

        :param factories: Show only arguments with factory.
        """
        self._setargs()
        order = (
            inspect.Parameter.POSITIONAL_ONLY,
            inspect.Parameter.POSITIONAL_OR_KEYWORD,
            inspect.Parameter.VAR_POSITIONAL,
            inspect.Parameter.KEYWORD_ONLY,
            inspect.Parameter.VAR_KEYWORD,
        )
        keys = []
        for kind in order:
            for name, arg in super().items():
                if factories is False and arg.factory:
                    continue
                if factories is True and not arg.factory:
                    continue
                if name in self.positions:
                    continue
                if arg.param.kind == kind:
                    keys.append(name)
        for key, position in self.positions.items():
            if factories and not self[key].factory:
                continue
            keys.insert(position, key)
        return keys

    def __iter__(self):
        return self.ordered().__iter__()

    def arg(
        self,
        name,
        *,
        kind: str = None,
        position: int = None,
        doc=None,
        color=None,
        default=inspect.Parameter.empty,
        annotation=inspect.Parameter.empty,
    ):
        """
        Inject new :py:class:`~cli2.argument.Argument` into this command.

        The new argument will appear in documentation, but won't be bound to
        the callable: it will only be avalaible in `self`.

        For example, you are deleting an "http_client" argument in
        :py:meth:`setargs()` so that it doesn't appear to the CLI user, to whom
        you want to expose a couple of arguments such as "base_url" and
        "ssl_verify" that you are adding programatically with this method, so
        that you can use `self['base_url'].value` and
        `self['ssl_verify'].value` in to generate a "http_client" argument in
        :py:meth:`call()`.

        The tutorial has a more comprehensive example in the "CLI only
        arguments" section.

        :param name: Name of the argument to add
        :param kind: Name of the inspect parameter kind
        :param position: Position of the argument in the CLI
        :param doc: Documentation for the argument
        :param color: Color of the argument
        :param default: Default value for the argument
        :param annotation: Type of argument
        """
        self[name] = Argument(
            self,
            inspect.Parameter(
                name,
                kind=getattr(
                    inspect.Parameter,
                    kind or "POSITIONAL_OR_KEYWORD",
                ),
                default=default,
                annotation=annotation,
            ),
            doc=doc,
            color=color,
        )
        if position is not None:
            self.positions[name] = position

    def post_call(self):
        """
        Implement your cleaner here
        """
        pass


class Argument:
    """
    Class representing a bound parameter and command line argument.
    """
    # TODO: why not split this into a bunch of simpler sub-classes now that
    # it's pretty featureful ?
    def __init__(self, cmd, param, doc=None, color=None, factory=None,
                 hide=False, **kwargs):
        self.cmd = cmd
        self.hide = hide
        self.param = param
        self.color = color
        # Let default be set to None :)
        self.default = kwargs.pop('default', param.default)
        self.factory = factory

        self.doc = doc or ''
        if not doc:
            for _param in cmd.parsed.params:
                if _param.arg_name == self.param.name:
                    self.doc = _param.description.replace('\n', ' ')
                    break

        self.type = None
        if param.annotation != param.empty:
            self.type = param.annotation

        self.negate = None
        if self.iskw and self.param.annotation == bool:
            self.negate = 'no-' + param.name
            if cmd.posix:
                self.negate = self.negate.replace('_', '-')

        self.taking = False

    @property
    def alias(self):
        if 'aliases' not in self.__dict__:
            if self.iskw:
                if self.cmd.posix:
                    self.aliases = self.optlist(
                        self.param.name.replace('_', '-'),
                        lambda a: '-' + a.lstrip('-')[0],
                    )
                else:
                    self.aliases = [self.param.name]
            else:
                self.aliases = []
        return self.aliases

    @alias.setter
    def alias(self, value):
        if not isinstance(value, (list, tuple)):
            value = value,
        self.aliases = value

    @property
    def negates(self):
        return self.optlist(self.negate, lambda a: '-n' + a.lstrip('-')[3])

    def optlist(self, opt, shortgen):
        if not opt:
            return []

        if isinstance(opt, (list, tuple)):
            opts = opt
        else:
            opts = [opt]

        if self.cmd.posix:
            if len(opts) == 1 and len(opts[0].lstrip('-')) > 1:
                short = shortgen(opts[0])
                conflicts = False
                for arg in self.cmd.values():
                    if arg is self:
                        continue
                    if 'aliases' not in arg.__dict__:
                        # aliases where not set
                        continue
                    if short in arg.alias:
                        conflicts = True
                        break
                if not conflicts:
                    opts = [short] + opts

            for i, alias in enumerate(opts):
                if alias.startswith('-'):
                    continue

                if len(alias) == 1:
                    opts[i] = '-' + alias
                elif not alias.startswith('-'):
                    if not alias.startswith('--'):
                        opts[i] = '--' + alias

        return opts

    def __repr__(self):
        return self.param.name

    def __str__(self):
        if self.alias:
            out = '[' + colors.orange + self.alias[-1]
            out += colors.reset

            if self.type != bool:
                out += '=' + colors.green + self.param.name.upper()
                out += colors.reset

            if self.negates:
                out += '|' + colors.orange + self.negates[-1]
                out += colors.reset

            out += ']'
            return out
        elif self.param.kind == self.param.VAR_POSITIONAL:
            return (
                '['
                + colors.green
                + self.param.name.upper()
                + colors.reset
                + ']...'
            )
        elif self.param.kind == self.param.VAR_KEYWORD:
            prefix = '--' if self.cmd.posix else ''
            return (
                '['
                + prefix
                + colors.green
                + self.param.name.upper()
                + colors.reset
                + '='
                + colors.green
                + 'VALUE'
                + colors.reset
                + ']...'
            )
        else:
            return colors.green + self.param.name.upper() + colors.reset

    def help(self):
        """Render help for this argument."""
        if self.alias:
            out = ''
            for alias in self.alias:
                out += colors.orange + alias + colors.reset
                if self.type != bool:
                    out += '='
                    out += colors.green
                    if self.type:
                        if isinstance(self.type, str):
                            out += self.type
                        else:
                            out += self.type.__name__
                    else:
                        out += self.param.name.upper()
                out += colors.reset
                out += ' '
            self.cmd.print(out)
        else:
            self.cmd.print(str(self) + colors.reset)

        if self.negates:
            out = ''
            for negate in self.negates:
                out += colors.orange + negate + colors.reset
                out += colors.reset
                out += ' '
            self.cmd.print(out)

        if (
            self.default != self.param.empty
            or self.param.default != self.param.empty
        ):
            self.cmd.print(
                'Default: '
                + colors.blue3
                + str(self.default or self.param.default)
                + colors.reset
            )

        if self.type == bool and not self.negates:
            self.cmd.print(
                'Accepted: '
                + colors.blue3
                + 'yes, 1, true, no, 0, false'
                + colors.reset
            )

        if self.param.kind == self.param.VAR_KEYWORD:
            self.cmd.print('Any number of named arguments, examples:')
            if self.cmd.posix:
                self.cmd.print(
                    '--'
                    + colors.green
                    + 'something'
                    + colors.reset
                    + '='
                    + colors.green
                    + 'somearg'
                )
            else:
                self.cmd.print('something=somearg')
        elif self.param.kind == self.param.VAR_POSITIONAL:
            self.cmd.print('Any number of un-named arguments')

        if self.doc:
            self.cmd.print(self.doc)

    @property
    def iskw(self):
        """Return True if this argument is not positional."""
        if self.param.kind == self.param.KEYWORD_ONLY:
            return True

        if self.param.POSITIONAL_OR_KEYWORD:
            return self.param.default != self.param.empty

    @property
    def accepts(self):
        """Return True if this argument still accepts values to bind."""
        return (
            self.param.name not in self.cmd.bound.arguments
            or self.param.kind in (
                self.param.VAR_POSITIONAL,
                self.param.VAR_KEYWORD,
            )
        )

    @property
    def value(self):
        """Return the value bound to this argument."""
        try:
            return self.cmd.bound.arguments[self.param.name]
        except KeyError as exc:
            if self.default != self.param.empty:
                return self.default
            msg = f'{self.param.name} has no CLI bound value nor default'
            raise ValueError(msg) from exc

    @value.setter
    def value(self, value):
        if value == self.param.empty:
            # the getter will return the default or raise
            return
        elif self.param.kind == self.param.VAR_POSITIONAL:
            self.cmd.bound.arguments.setdefault(self.param.name, [])
            self.cmd.bound.arguments[self.param.name].append(value)
        elif self.param.kind == self.param.VAR_KEYWORD:
            self.cmd.bound.arguments.setdefault(self.param.name, {})
            parts = value.split('=')
            name = parts[0]
            if self.cmd.posix:
                name = name.lstrip('-')
            value = '='.join(parts[1:])
            self.cmd.bound.arguments[self.param.name][name] = value
        else:
            self.cmd.bound.arguments[self.param.name] = value

    def cast(self, value):
        """Cast a string argument from the CLI into a Python object."""
        if self.param.annotation == int:
            return int(value)
        if self.param.annotation == float:
            return float(value)
        if value in self.negates:
            return False
        if self.param.annotation == bool:
            return value.lower() not in ('', '0', 'no', 'false', self.negate)
        if self.param.annotation == list:
            try:
                return json.loads(value)
            except json.JSONDecodeError:
                return [i.strip() for i in value.split(',')]
        if self.param.annotation == dict:
            try:
                return json.loads(value)
            except json.JSONDecodeError:
                results = dict()
                for token in value.split(','):
                    parts = token.split(':')
                    results[parts[0].strip()] = ':'.join(parts[1:]).strip()
                return results
        return value

    def aliasmatch(self, arg):
        """Return True if the CLI arg matches an alias of this argument."""
        if arg in self.negates:
            return True
        if self.iskw and self.param.annotation == bool and arg in self.alias:
            return True
        for alias in self.alias:
            if arg.startswith(alias + '='):
                return True

    def match(self, arg):
        """Return the value extracted from a matching CLI argument."""
        if self.aliasmatch(arg):
            if self.param.annotation != bool or '=' in arg:
                for alias in self.alias:
                    if arg.startswith(alias):
                        arg = arg[len(alias):]
                        if arg.startswith('='):
                            arg = arg[1:]
                        return arg
        return arg

    def take(self, arg):
        """Return False if it doesn't accept this arg, otherwise bind it."""
        if not self.accepts:
            return

        if self.aliasmatch(arg):
            self.value = self.cast(self.match(arg))
            return True

        if self.param.kind == self.param.VAR_KEYWORD:
            if arg.startswith('**{') and arg.endswith('}'):
                self.cmd.bound.arguments[self.param.name] = json.loads(arg[2:])
                return True

        elif self.param.kind == self.param.VAR_POSITIONAL:
            if arg.startswith('*[') and arg.endswith(']'):
                self.cmd.bound.arguments[self.param.name] = json.loads(arg[1:])
                return True

        # look ahead for keyword arguments that would match this
        # so that you can skip arguments that are both keyword and positional
        # ie. `foo b=x` binds 'x' to 'b' in foo(a=None, b=None)
        for name, argument in self.cmd.items():
            if not argument.accepts:
                continue
            if argument == self:
                continue
            if argument.aliasmatch(arg):
                return

        # edge case varkwargs
        # priority to varkwargs for word= and **{}
        last = self.cmd[[*self.cmd.keys()][-1]]
        if last is not self and last.param.kind == self.param.VAR_KEYWORD:
            if re.match('^-?-?[\\w]+=', arg):
                return
            elif arg.startswith('**{') and arg.endswith('}'):
                return

        if (
            self.iskw
            and self.alias[0].startswith('-')
            and self.param.annotation != bool
            and '=' not in arg
            and arg in self.alias
        ):
            self.taking = True
            return True

        if self.taking:
            arg = self.alias[0] + '=' + arg

        value = self.match(arg)

        if value is not None:
            self.value = self.cast(value)
            return True

    def factory_value(self, cmd=None):
        """
        Run the factory function and return the value.

        If the factory function takes a `cmd` argument, it will pass the
        command object.

        If the factory function takes an `arg` argument, it will pass self.

        It will forward any argument to the factory function if detected in
        it's signature, except for ``*args`` and ``**kwargs``.

        :param cmd: Override for :py:attr:`cmd`, useful for getting the factory
                    value of an argument from another class (advanced).
        """
        kwargs = dict()
        cmd = cmd or self.cmd
        sig = inspect.signature(self.factory)
        if 'cmd' in sig.parameters:
            kwargs['cmd'] = cmd
        if 'arg' in sig.parameters:
            kwargs['arg'] = self

        excluded = (
            inspect.Parameter.VAR_KEYWORD,
            inspect.Parameter.VAR_POSITIONAL,
        )
        for key, arg in cmd.items():
            if arg.param.kind in excluded:
                continue
            if key in sig.parameters:
                kwargs[key] = arg.value
        return self.factory(**kwargs)
