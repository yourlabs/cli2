import inspect

from .colors import colors
from .command import Command
from .decorators import arg
from .entry_point import EntryPoint
from .node import Node
from .termsize import termsize


class Group(EntryPoint, dict):
    def __init__(self, name=None, doc=None, color=None, posix=False):
        self.name = name
        self.doc = doc or inspect.getdoc(self)
        self.color = color or colors.green
        self.posix = posix

        # make help a group command
        self.cmd(self.help)

    def add(self, target, *args, **kwargs):
        cmd = Command(target, *args, **kwargs)
        self[cmd.name] = cmd
        return self

    def __setitem__(self, key, value):
        value.posix = self.posix
        super().__setitem__(key, value)

    def cmd(self, *args, **kwargs):
        if len(args) == 1 and not kwargs:
            # simple @group.cmd syntax
            target = args[0]
            self.add(target)
            return target
        elif not args:
            def wrap(cb):
                self.add(cb, **kwargs)
                return cb
            return wrap
        else:
            raise Exception('Only kwargs are supported by Group.cmd')

    def arg(self, name, **kwargs):
        return arg(name, **kwargs)

    def group(self, name, **kwargs):
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
                    return target.help(error=error)
                else:
                    error = f'Command {arg} not found in {target}'
                    error += f'Showing help for {target}'
                    break
            return target.help(error=error)

        output = []

        if error:
            output.append(error + '\n')

        if self.doc:
            output.append(self.doc + '\n')

        if not len(self) or short:
            return '\n'.join(output)

        namewidth = 2 + max([len(key) for key in self]) + 2
        descwidth = termsize()[1] - namewidth

        for name, command in self.items():
            doc = command.help(short=True)
            out = ''
            for char in doc:
                if len(out) == descwidth and '\n' not in out:
                    out += '\n' + ' ' * (namewidth)
                out += char

            line = [
                '  ',
                command.color,
                name,
                colors.reset,
                ' ' * (namewidth - len(str(name)) - 4),
                '  ',
                out,
            ]
            output.append((''.join(map(str, line))).rstrip())
        return '\n'.join(output)
    help.cli2 = dict(color='green')

    def load(self, obj, parent=None):
        if isinstance(obj, str):
            obj = Node.factory(obj).target

        objpackage = getattr(obj, '__package__', None)

        for name in dir(obj):
            if name == '__call__':
                target = obj
            elif name.startswith('__'):
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
                    self.add(target)
                continue

            node = Node(name, target)
            if node.callables:
                self.group(name).load(target, parent=obj)

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
        return self.name
