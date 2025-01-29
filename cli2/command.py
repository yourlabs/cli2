import asyncio
import inspect
import json
import sys

from docstring_parser import parse

try:
    from httpx import HTTPStatusError
except ImportError:
    class HTTPStatusError(Exception):
        pass

from . import display
from .argument import Argument
from .colors import colors
from .entry_point import EntryPoint
from .asyncio import async_resolve


class Command(EntryPoint, dict):
    """Represents a command bound to a target callable."""

    def __new__(cls, target, *args, **kwargs):
        overrides = getattr(target, 'cli2', {})
        cls = overrides.get('cls', cls)
        return super().__new__(cls, *args, **kwargs)

    def __init__(self, target, name=None, color=None, doc=None, posix=False,
                 help_hack=True, outfile=None, log=True):
        self.posix = posix
        self.parent = None
        self.help_hack = help_hack

        self.target = target
        self.sig = inspect.signature(target)
        if inspect.ismethod(target):
            # let's allow overwriting a bound method's __self__
            func_sig = inspect.signature(target.__func__)
            self_name = [*func_sig.parameters.keys()][0]
            overrides = getattr(self.target.__func__, f'cli2_{self_name}', {})
            if 'factory' in overrides:
                self.target = target.__func__
                self.sig = inspect.signature(target.__func__)

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
        EntryPoint.__init__(self, outfile=outfile, log=log)
        self.args_set = False
        self.args_setting = False

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
            return asyncio.run(self.async_call(*argv))

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
            if (
                inspect.isgenerator(result)
                or isinstance(result, (list, tuple))
            ):
                for _ in result:
                    display.print(_)
                result = None
        except KeyboardInterrupt:
            print('exiting')
            sys.exit(1)
        finally:
            self.post_result = self.post_call()
        return result

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

        factories = self.values(factories=True)
        if factories:
            results = await asyncio.gather(*[
                async_resolve(arg.factory_value())
                for arg in factories
            ])
            for _, arg in enumerate(factories):
                arg.value = results[_]

        try:
            result = self.call(*self.bound.args, **self.bound.kwargs)
            result = await async_resolve(result, output=True)
        except KeyboardInterrupt:
            print('exiting')
            sys.exit(1)
        except HTTPStatusError as exc:
            # we probably can have a generic exception handler registry
            # of some sort instead of this, but this will do for now
            self.http_exception_enhance(exc)
            raise
        finally:
            try:
                self.post_result = await async_resolve(self.post_call())
            except HTTPStatusError as exc:
                self.http_exception_enhance(exc)
                raise
        return result

    def http_exception_enhance(self, exc):
        """
        Enhance an httpx.HTTPStatusError

        Adds beatiful request/response data to the exception.

        :param exc: httpx.HTTPStatusError
        """
        try:
            request = display.yaml_dump(
                json.loads(exc.request.content.decode()),
            )
        except json.JSONDecodeError:
            request = exc.request.content

        try:
            response = display.yaml_dump(exc.response.json())
        except json.JSONDecodeError:
            response = exc.response.content

        exc.args = ('\n'.join([
            exc.args[0],
            'Request data:',
            request,
            'Response data:',
            response,
        ]),)

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
