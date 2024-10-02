import asyncio
import inspect
import sys

from docstring_parser import parse

from .argument import Argument
from .colors import colors
from .entry_point import EntryPoint


class Command(EntryPoint, dict):
    """Represents a command bound to a target callable."""

    def __new__(cls, target, *args, **kwargs):
        overrides = getattr(target, 'cli2', {})
        cls = overrides.get('cls', cls)
        return super().__new__(cls, *args, **kwargs)

    def __init__(self, target, name=None, color=None, doc=None, posix=False,
                 help_hack=True, outfile=None, log=True):
        self.target = target
        self.posix = posix
        self.parent = None
        self.help_hack = help_hack

        overrides = getattr(target, 'cli2', {})
        for key, value in overrides.items():
            setattr(self, key, value)

        if name:
            self.name = name
        elif 'name' not in overrides:
            self.name = getattr(target, '__name__', type(target).__name__)

        self.parsed = parse(inspect.getdoc(target))
        if doc:
            self.doc = doc
        elif 'doc' not in overrides:
            self.doc = ''
            if self.parsed.short_description:
                self.doc += self.parsed.short_description.replace('\n', ' ')
            if self.parsed.long_description:
                if self.doc:
                    self.doc += '\n'
                self.doc += self.parsed.long_description

        if color:
            self.color = color
        elif 'color' not in overrides:
            self.color = 'orange'

        self.positions = dict()
        self.sig = inspect.signature(target)
        self.setargs()
        EntryPoint.__init__(self, outfile=outfile, log=log)

    def setargs(self):
        """Reset arguments."""
        for name, param in self.sig.parameters.items():
            overrides = getattr(self.target, 'cli2_' + name, {})
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

    def help(self, error=None, short=False):
        """Show help for a command."""
        if short:
            if self.doc:
                return self.doc.replace('\n', ' ').split('.')[0]
            return ''

        if error:
            self.print('RED', 'ERROR: ' + colors.reset + error, end='\n\n')

        self.print('ORANGE', 'SYNOPSYS')
        chain = []
        current = self
        while current is not None:
            chain.insert(0, current.name)
            current = current.parent
        for arg in self.values():
            chain.append(str(arg))
        self.print(' '.join(map(str, chain)), end='\n\n')

        self.print('ORANGE', 'DESCRIPTION')
        self.print(self.doc)

        shown_posargs = False
        shown_kwargs = False
        for arg in self.values():
            self.print()

            if not arg.iskw and not shown_posargs:
                self.print('ORANGE', 'POSITIONAL ARGUMENTS')
                shown_posargs = True

            varkw = arg.param.kind == arg.param.VAR_KEYWORD
            if (arg.iskw or varkw) and not shown_kwargs:
                self.print('ORANGE', 'NAMED ARGUMENTS')
                shown_kwargs = True
            arg.help()

    def parse(self, *argv):
        """Parse arguments into BoundArguments."""
        self.setargs()
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

        for name, arg in self.items():
            if not arg.default:
                continue
            if name in self.bound.arguments:
                continue
            arg.value = arg.default

    def call(self, *args, **kwargs):
        """Execute command target with bound arguments."""
        return self.target(*args, **kwargs)

    def __call__(self, *argv):
        """Execute command with args from sysargs."""
        if self.help_hack and '--help' in argv:
            self.exit_code = 1
            return self.help()

        self.exit_code = 0
        error = self.parse(*argv)
        if error:
            self.exit_code = 1
            return self.help(error=error)

        missing = [
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
        if missing:
            error = (
                f'missing {len(missing)} required argument'
                f'{"s" if len(missing) > 1 else ""}'
                f': {", ".join(missing)}'
            )
            self.exit_code = 1
            return self.help(error=error)

        try:
            result = self.call(*self.bound.args, **self.bound.kwargs)
            if inspect.iscoroutine(result):
                result = asyncio.run(result)
        except KeyboardInterrupt:
            print('exiting')
            sys.exit(1)
        return result

    @property
    def ordered(self):
        """
        Order the parameters by priority.
        """
        return {key: self[key] for key in self.keys()}

    def values(self):
        """ Return ordered values """
        return self.ordered.values()

    def items(self):
        """ Return ordered items """
        return self.ordered.items()

    def keys(self):
        """ Return ordered keys """
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
                if name in self.positions:
                    continue
                if arg.param.kind == kind:
                    keys.append(name)
        for key, position in self.positions.items():
            keys.insert(position, key)
        return keys

    def __iter__(self):
        return self.ordered.__iter__()

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
