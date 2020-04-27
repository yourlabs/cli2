import inspect
import os
import subprocess

from .colors import colors
from .command import Command
from .entry_point import EntryPoint


def termsize():
    if 'FORCE_TERMSIZE' in os.environ:
        return 180, 80

    try:
        rows, columns = subprocess.check_output(['stty', 'size']).split()
    except subprocess.CalledProcessError:
        return 180, 80
    return int(rows), int(columns)


class Group(EntryPoint, dict):
    def __init__(self, name=None, doc=None, color=None):
        self.name = name
        self.doc = doc or inspect.getdoc(self)
        self.color = color or colors.green

    def cmd(self, target, name=None):
        cmd = Command(target, name)
        self[cmd.name] = cmd
        return self

    def help(self, error=None, short=False):
        output = []
        if error:
            output.append(error + '\n')

        if self.doc:
            output.append(self.doc + '\n')

        if not len(self):
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
            output.append(''.join(map(str, line)))
        return '\n'.join(output)

    def load(self, obj):
        for name in dir(obj):
            if name == '__call__':
                target = obj
            elif name.startswith('__'):
                continue
            else:
                target = getattr(obj, name)

            if callable(target):
                cmd = Command(target)
                self[cmd.name] = cmd
                continue
            else:
                self[name] = Group(name)

    def __call__(self, *argv):
        self.exit_code = 0
        if not argv:
            return self.help('No command provided, showing help.')

        if argv[0] in self:
            result = self[argv[0]](*argv[1:])
            # fetch exit code
            self.exit_code = self[argv[0]].exit_code
        elif argv[0] == 'help':
            if len(argv) > 1:
                if argv[1] in self:
                    return self[argv[1]].help()
                else:
                    return self.help(
                        f'Command {argv[0]} not found, showing help.'
                    )
            else:
                return self.help()
        else:
            return self.help(f'Command {argv[0]} not found, showing help.')

        return result

    def __repr__(self):
        return f'Group({self.name})'
