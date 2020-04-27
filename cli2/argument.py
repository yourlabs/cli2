import re
import json


class Argument:
    def __init__(self, cmd, param):
        self.cmd = cmd
        self.param = param
        self.alias = param.name if self.iskw else None
        self.negate = None

    def __repr__(self):
        return self.param.name

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
        if self.iskw and self.param.annotation == bool and arg == self.alias:
            return True
        return self.alias and arg.startswith(self.alias + '=')

    def match(self, arg):
        if self.aliasmatch(arg):
            if self.param.annotation != bool or '=' in arg:
                return arg[len(self.alias) + 1:]
        return arg

    def take(self, arg):
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

        value = self.match(arg)
        if value is not None:
            self.value = self.cast(value)
            return True
