import subprocess
import sys

from .command import Command


def termsize():
    rows, columns = subprocess.check_output(['stty', 'size']).split()
    return int(rows), int(columns)


class Group(dict):
    def __init__(self, name=None, doc=None, color=None):
        self.name = name
        self.doc = doc
        self.color = color

    def cmd(self, target, name=None):
        cmd = Command(target, name)
        self[cmd.name] = cmd
        return self

    def help(self, error=None):
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
            output.append(
                '  ' + name + '  ' + command.help(short=True)[:descwidth]
            )
        return '\n'.join(output)

    def generate(self, obj):
        for name in dir(obj):
            if name == '__call__':
                target = obj
            elif name.startswith('__'):
                continue
            else:
                target = getattr(obj, name)

            if not callable(target):
                continue

            cmd = Command(target)
            self[cmd.name] = cmd

    def __call__(self, argv=None):
        argv = argv if argv is not None else sys.argv[1:]
        if not argv:
            return self.help('No command provided, showing help.')

        if argv[0] in self:
            result = self[argv[0]](argv[1:])
        else:
            return self.help(f'Command {argv[0]} not found, showing help.')

        return result

    def __repr__(self):
        return f'Group({self.name})'
