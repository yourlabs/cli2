import copy
import inspect
import json
import re
import subprocess
import sys

import cli2


def termsize():
    rows, columns = subprocess.check_output(['stty', 'size']).split()
    return int(rows), int(columns)


def cast(type, value):
    if issubclass(type, list):
        if value.startswith('[') and value.endswith(']'):
            try:
                return json.loads(value)
            except:
                return [i.strip() for i in value[1:-1].split(',')]
        else:
            return [value]

    if issubclass(type, dict):
        if value.startswith('{') and value.endswith('}'):
            try:
                return json.loads(value)
            except:
                ret = dict()
                for item in value[1:-1].split(','):
                    key, value = item.split(':')
                    ret[key.strip()] = value.strip()
                return ret
        else:
            raise Exception(f'Failed to convert {value} to dict')

    if issubclass(type, bool):
        return value.lower() not in ('', '0', 'no', 'false')

    if issubclass(type, int):
        return int(value)


def typeguess(spec, name):
    if name in spec.annotations:
        return spec.annotations[name]

    if spec.defaults:
        cnt = len(spec.args) - len(spec.defaults)
        has_defaults = spec.args[cnt:]
        if name in has_defaults:
            default = spec.defaults[has_defaults.index(name)]
            if default is not None:
                return type(default)


def getdoc(target):
    return inspect.getdoc(target)


class Command:
    def __init__(self, target, name=None, doc=None, color=None, options=None):
        self.target = target
        self.name = name or getattr(target, '__name__', None)
        self.spec = inspect.getfullargspec(target)
        self.doc = doc or getdoc(target)
        self.color = color
        self.options = options or []
        self.missing = []
        self.reminder = []
        self.args = []
        self.kwargs = dict()
        self.vars = dict()

        if self.spec.defaults:
            self.defaults = {
                self.spec.args[-i-1]: value
                for i, value in enumerate(self.spec.defaults)
            }
        else:
            self.defaults = dict()

        if self.spec.args:
            self.types = {
                name: typeguess(self.spec, name) for name in self.spec.args
            }
        else:
            self.types = dict()

    def cast(self, name, value):
        """Cast an named argument value based on its annotation if any"""
        guessed = typeguess(self.spec, name)
        if guessed:
            return cast(guessed, value)
        return value  # didn't find annotation nor default, leave parsed string

    def parse(self, *argv):
        """
        Return a kwargs dict, and sets self.reminder.

        The kwargs dict it returns is fit to be passed to the unparse method
        that returns args & kwargs that you can use to call
        command.target(*args, **kwargs).
        """
        self.reminder = []
        self.vars = dict()

        for arg in argv:
            # do we have any option matching that arg ?
            found = False
            for option in self.options:
                value = option.match(arg)
                if value is not None:
                    self.vars[option.name] = option.cast(self, value)
                    found = True
                    break
            if found:
                continue

            match = re.match('^(?P<left>[.a-zA-Z0-9]*)=(?P<value>.*)$', arg)
            if match:
                # pure foo=bar kind of arg, simple kwarg syntax if foo exists
                left = match.group('left')
                value = match.group('value')

                if '.' in left:
                    # dealing with a dict being set on the CLI
                    name, key = left.split('.')
                    value = dict(key=value)
                else:
                    name = left

                if name in self.spec.args or self.spec.varkw:
                    if isinstance(value, dict):
                        self.vars.setdefault(name, dict())
                        self.vars[name].update(value)
                    elif name in self.vars and isinstance(self.vars[name], list):
                        # multiple arg specified to provision a list annotation
                        self.vars[name] += self.cast(name, value)
                    else:
                        # otherwise apply standard arg casting
                        self.vars[name] = self.cast(name, value)
                    continue

            found = False
            for name in self.spec.args:
                # is there a callback arg that's left to provision ?
                # attribute the value to the first one
                if name not in self.vars:
                    self.vars[name] = self.cast(name, arg)
                    found = True
                    break
            if found:
                continue

            if self.spec.varargs:
                self.vars.setdefault(self.spec.varargs, [])
                self.vars[self.spec.varargs].append(arg)

            # otherwise just stick it with the extra args, you'll want that if
            # you're making a wrapper CLI for another CLI (bigsudo for example)
            self.reminder.append(arg)

        self.kwargs = copy.copy(self.vars)
        self.missing = [
            name
            for name in self.spec.args
            if name not in self.kwargs
            and name not in self.defaults
        ]
        self.args = []
        for name in self.spec.args:
            if name not in self.kwargs:
                break
            self.args.append(self.kwargs.pop(name))
        if self.spec.varargs and self.spec.varargs in self.kwargs:
            self.args += self.kwargs.pop(self.spec.varargs)

        return self  # nested group/command support

    def help(self, short=False):
        output = []

        if self.missing:
            output.append('Missing required args: ' + ' '.join(self.missing) + '\n')

        if self.reminder:
            output.append('Extra args: ' + ' '.join(self.reminder) + '\n')

        if self.doc:
            output.append(self.doc + '\n')

        if self.spec.args:
            output.append('Arguments doc:')
            for arg in self.spec.args:
                output.append(arg)

        return '\n'.join(output)

    def __call__(self, argv=None):
        """Parse, unparse argv, call target and await if returns coroutine."""
        argv = argv if argv is not None else sys.argv[1:]
        self.parse(*argv)

        if self.missing or self.reminder:
            return self.help()

        result = self.target(*self.args, **self.kwargs)

        if inspect.iscoroutine(result):
            import asyncio
            result = asyncio.run(result)

        return result

    def __repr__(self):
        return f'Command({self.name})'


class Group(dict):
    def __init__(self, name=None, doc=None, color=None):
        self.name = name
        self.doc = doc
        self.color = color

    def add_command(self, target, name=None, doc=None, color=None, options=None):
        if options and isinstance(options, dict):
            options = [
                Argument(key, **value) for key, value in options.items()
            ]
        cmd = Command(target, name, doc, color, options)
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


class Argument:
    def __init__(self, name, alias=None):
        self.name = name
        self.alias = alias

    def match(self, arg):
        name = self.alias or self.name
        if '=' in arg and arg.split('=')[0] == name:
            return arg[len(name + '='):]
        if arg == self.alias:
            return arg

    def cast(self, command, value):
        return command.cast(self.name, value)
