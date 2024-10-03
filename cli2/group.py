import inspect
import textwrap

from .colors import colors
from .command import Command
from .decorators import arg
from .entry_point import EntryPoint
from .node import Node


class Group(EntryPoint, dict):
    """Represents a group of named commands."""

    def __init__(self, name=None, doc=None, color=None, posix=False,
                 outfile=None, cmdclass=None, log=True):
        self.name = name
        if doc:
            self.doc = textwrap.dedent(doc).strip()
        else:
            self.doc = inspect.getdoc(self)
        self.color = color or colors.green
        self.posix = posix
        self.parent = None
        self.cmdclass = cmdclass or Command
        EntryPoint.__init__(self, outfile=outfile, log=log)

        # make help a group command
        self.cmd(self.help, cls=Command)

    def add(self, target, *args, **kwargs):
        """Add a new target as sub-command."""
        cmdclass = kwargs.pop('cls', self.cmdclass)
        cmd = cmdclass(target, *args, **kwargs)
        self[cmd.name] = cmd
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

    def group(self, name, **kwargs):
        """Return a new sub-group."""
        kwargs.setdefault('cmdclass', self.cmdclass)
        self[name] = Group(name, **kwargs)
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
                return self.doc.replace('\n', ' ').split('.')[0]
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

    def load(self, obj, parent=None, public=True):
        """Load a Python object callables into sub-commands."""
        if isinstance(obj, str):
            obj = Node.factory(obj).target

        objpackage = getattr(obj, '__package__', None)

        for name in dir(obj):
            if name == '__call__':
                target = obj
                name = type(obj).__name__
            elif name.startswith('__' if not public else '_'):
                continue
            else:
                target = getattr(obj, name)

            targetpackage = getattr(target, '__package__', None)
            if targetpackage and objpackage:
                # prevent recursively loading from other packages
                # and above obj level
                if not targetpackage.startswith(objpackage):
                    continue

            if target == parent:
                # detect and prevent recursive imports
                continue

            if callable(target):
                try:
                    inspect.signature(target)
                except ValueError:
                    pass
                else:
                    self.add(target, name=name)
                continue

            node = Node(name, target)
            if node.callables:
                self.group(name).load(target, parent=obj)
        return self

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
