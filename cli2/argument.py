import re
import json

from .colors import colors


class Argument:
    def __init__(self, cmd, param, doc=None, color=None):
        self.cmd = cmd
        self.param = param
        self.color = color

        self.doc = doc or ''
        if not doc:
            for _param in cmd.parsed.params:
                if _param.arg_name == self.param.name:
                    self.doc = _param.description.replace('\n', ' ')
                    break

        self.type = None
        if param.annotation != param.empty:
            self.type = param.annotation

        self.alias = None
        if self.iskw:
            self.alias = param.name
            if cmd.posix:
                self.alias = self.alias.replace('_', '-')

        self.negate = None
        if self.iskw and self.param.annotation == bool:
            self.negate = 'no-' + param.name
            if cmd.posix:
                self.negate = self.negate.replace('_', '-')

    @property
    def aliases(self):
        return self.optlist(self.alias, lambda a: '-' + a.lstrip('-')[0])

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
                    if short in arg.aliases:
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
            return self.alias + '=...'
        elif self.param.kind == self.param.VAR_POSITIONAL:
            return '*' + self.param.name
        elif self.param.kind == self.param.VAR_KEYWORD:
            return '**' + self.param.name
        else:
            return '<' + self.param.name + '>'

    def help(self):
        out = colors.greenbold + str(self) + colors.reset
        if self.type:
            out += colors.orange + str(self.type) + colors.reset
        self.cmd.print(out)

        if self.param.kind == self.param.VAR_KEYWORD:
            self.cmd.print('Any number of named arguments')
        elif self.param.kind == self.param.VAR_POSITIONAL:
            self.cmd.print('Any number of un-named arguments')

        if self.doc:
            self.cmd.print(self.doc)

    @property
    def iskw(self):
        if self.param.kind == self.param.KEYWORD_ONLY:
            return True

        if self.param.POSITIONAL_OR_KEYWORD:
            return self.param.default != self.param.empty

    @property
    def accepts(self):
        return (
            self.param.name not in self.cmd.bound.arguments
            or self.param.kind in (
                self.param.VAR_POSITIONAL,
                self.param.VAR_KEYWORD,
            )
        )

    @property
    def value(self):
        return self.cmd.bound.arguments[self.param.name]

    @value.setter
    def value(self, value):
        if self.param.kind == self.param.VAR_POSITIONAL:
            self.cmd.bound.arguments.setdefault(self.param.name, [])
            self.cmd.bound.arguments[self.param.name].append(value)
        elif self.param.kind == self.param.VAR_KEYWORD:
            self.cmd.bound.arguments.setdefault(self.param.name, {})
            parts = value.split('=')
            value = '='.join(parts[1:])
            self.cmd.bound.arguments[self.param.name][parts[0]] = value
        else:
            self.cmd.bound.arguments[self.param.name] = value

    def cast(self, value):
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
        if arg == self.negate:
            return True
        if self.iskw and self.param.annotation == bool and arg in self.aliases:
            return True
        for alias in self.aliases:
            if arg.startswith(alias + '='):
                return True

    def match(self, arg):
        if self.aliasmatch(arg):
            if self.param.annotation != bool or '=' in arg:
                for alias in self.aliases:
                    if arg.startswith(alias):
                        arg = arg[len(alias):]
                        if arg.startswith('='):
                            arg = arg[1:]
                        return arg
        return arg

    def take(self, arg, next_arg):
        if not self.accepts:
            return

        if self.param.kind == self.param.VAR_KEYWORD:
            if arg.startswith('**{') and arg.endswith('}'):
                self.cmd.bound.arguments[self.param.name] = json.loads(arg[2:])
                return True

        elif self.param.kind == self.param.VAR_POSITIONAL:
            if arg.startswith('*[') and arg.endswith(']'):
                self.cmd.bound.arguments[self.param.name] = json.loads(arg[1:])
                return True

        # look ahead for keyword arguments that would match this
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
            if re.match('^\\w+=', arg):
                return
            elif arg.startswith('**{') and arg.endswith('}'):
                return

        next_take = False
        if (
            self.iskw
            and self.aliases[0].startswith('-')
            and self.param.annotation != bool
            and '=' not in arg
            and next_arg
        ):
            arg = arg + '=' + next_arg
            next_take = True

        value = self.match(arg)

        if value is not None:
            self.value = self.cast(value)
            return 'next' if next_take else True
