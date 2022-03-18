import asyncio
import inspect

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
                 outfile=None, log=True):
        self.target = target
        self.posix = posix
        self.parent = None

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
                self.doc += self.parsed.long_description.replace('\n', ' ')

        if color:
            self.color = color
        elif 'color' not in overrides:
            self.color = 'orange'

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
        """"Parse arguments into BoundArguments."""
        self.setargs()
        self.bound = self.sig.bind_partial()
        extra = []
        for current in argv:
            taken = False
            for arg in self.values():
                if taken := arg.take(current):
                    break

            if not taken:
                extra.append(current)

        if extra:
            return 'No parameters for these arguments: ' + ', '.join(extra)

    def call(self, *args, **kwargs):
        """Execute command target with bound arguments."""
        return self.target(*args, **kwargs)

    def argskwargs(self):
        for name, arg in self.items():
            if not arg.default:
                continue
            if name in self.bound.arguments:
                continue
            arg.value = arg.default
        return self.bound.args, self.bound.kwargs

    def __call__(self, *argv):
        """Execute command with args from sysargs."""
        self.exit_code = 0
        error = self.parse(*argv)
        if error:
            return self.help(error=error)

        args, kwargs = self.argskwargs()

        try:
            result = self.call(*args, **kwargs)
        except TypeError as exc:
            self.exit_code = 1
            if hasattr(self.target, '__name__'):
                rep = getattr(self.target, '__name__')
            elif hasattr(self.target, '__call__'):
                rep = '__call__'
            error = str(exc)
            function = error.split(' ')[0].split('.')[-1]
            if function.startswith(rep + '('):
                return self.help(error=error.replace(rep + '()', self.name))
            raise

        if inspect.iscoroutine(result):
            try:
                result = asyncio.run(result)
            except KeyboardInterrupt:
                print('exiting')
                import sys
                sys.exit(1)
        return result
