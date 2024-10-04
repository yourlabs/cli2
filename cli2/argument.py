import inspect
import re
import json

from .colors import colors


class Argument:
    """
    Class representing a bound parameter and command line argument.
    """
    # TODO: why not split this into a bunch of simpler sub-classes now that
    # it's pretty featureful ?
    def __init__(self, cmd, param, doc=None, color=None, factory=None,
                 **kwargs):
        self.cmd = cmd
        self.param = param
        self.color = color
        # Let default be set to None :)
        self.default = kwargs.pop('default', param.default)
        self.factory = factory

        self.doc = doc or ''
        if not doc:
            for _param in cmd.parsed.params:
                if _param.arg_name == self.param.name:
                    self.doc = _param.description.replace('\n', ' ')
                    break

        self.type = None
        if param.annotation != param.empty:
            self.type = param.annotation

        self.negate = None
        if self.iskw and self.param.annotation == bool:
            self.negate = 'no-' + param.name
            if cmd.posix:
                self.negate = self.negate.replace('_', '-')

        self.taking = False

    @property
    def alias(self):
        if 'aliases' not in self.__dict__:
            if self.iskw:
                if self.cmd.posix:
                    self.aliases = self.optlist(
                        self.param.name.replace('_', '-'),
                        lambda a: '-' + a.lstrip('-')[0],
                    )
                else:
                    self.aliases = [self.param.name]
            else:
                self.aliases = []
        return self.aliases

    @alias.setter
    def alias(self, value):
        if not isinstance(value, (list, tuple)):
            value = value,
        self.aliases = value

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
                    if 'aliases' not in arg.__dict__:
                        # aliases where not set
                        continue
                    if short in arg.alias:
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
            out = '[' + colors.orange + self.alias[-1]
            out += colors.reset

            if self.type != bool:
                out += '=' + colors.green + self.param.name.upper()
                out += colors.reset

            if self.negates:
                out += '|' + colors.orange + self.negates[-1]
                out += colors.reset

            out += ']'
            return out
        elif self.param.kind == self.param.VAR_POSITIONAL:
            return (
                '['
                + colors.green
                + self.param.name.upper()
                + colors.reset
                + ']...'
            )
        elif self.param.kind == self.param.VAR_KEYWORD:
            prefix = '--' if self.cmd.posix else ''
            return (
                '['
                + prefix
                + colors.green
                + self.param.name.upper()
                + colors.reset
                + '='
                + colors.green
                + 'VALUE'
                + colors.reset
                + ']...'
            )
        else:
            return colors.green + self.param.name.upper() + colors.reset

    def help(self):
        """Render help for this argument."""
        if self.alias:
            out = ''
            for alias in self.alias:
                out += colors.orange + alias + colors.reset
                if self.type != bool:
                    out += '='
                    out += colors.green
                    if self.type:
                        out += self.type.__name__
                    else:
                        out += self.param.name.upper()
                out += colors.reset
                out += ' '
            self.cmd.print(out)
        else:
            self.cmd.print(str(self) + colors.reset)

        if self.negates:
            out = ''
            for negate in self.negates:
                out += colors.orange + negate + colors.reset
                out += colors.reset
                out += ' '
            self.cmd.print(out)

        if (
            self.default != self.param.empty
            or self.param.default != self.param.empty
        ):
            self.cmd.print(
                'Default: '
                + colors.blue3
                + str(self.default or self.param.default)
                + colors.reset
            )

        if self.type == bool and not self.negates:
            self.cmd.print(
                'Accepted: '
                + colors.blue3
                + 'yes, 1, true, no, 0, false'
                + colors.reset
            )

        if self.param.kind == self.param.VAR_KEYWORD:
            self.cmd.print('Any number of named arguments, examples:')
            if self.cmd.posix:
                self.cmd.print(
                    '--'
                    + colors.green
                    + 'something'
                    + colors.reset
                    + '='
                    + colors.green
                    + 'somearg'
                )
            else:
                self.cmd.print('something=somearg')
        elif self.param.kind == self.param.VAR_POSITIONAL:
            self.cmd.print('Any number of un-named arguments')

        if self.doc:
            self.cmd.print(self.doc)

    @property
    def iskw(self):
        """Return True if this argument is not positional."""
        if self.param.kind == self.param.KEYWORD_ONLY:
            return True

        if self.param.POSITIONAL_OR_KEYWORD:
            return self.param.default != self.param.empty

    @property
    def accepts(self):
        """Return True if this argument still accepts values to bind."""
        return (
            self.param.name not in self.cmd.bound.arguments
            or self.param.kind in (
                self.param.VAR_POSITIONAL,
                self.param.VAR_KEYWORD,
            )
        )

    @property
    def value(self):
        """Return the value bound to this argument."""
        try:
            return self.cmd.bound.arguments[self.param.name]
        except KeyError as exc:
            if self.default != self.param.empty:
                return self.default
            msg = f'{self.param.name} has no CLI bound value nor default'
            raise ValueError(msg) from exc

    @value.setter
    def value(self, value):
        if value == self.param.empty:
            # the getter will return the default or raise
            return
        elif self.param.kind == self.param.VAR_POSITIONAL:
            self.cmd.bound.arguments.setdefault(self.param.name, [])
            self.cmd.bound.arguments[self.param.name].append(value)
        elif self.param.kind == self.param.VAR_KEYWORD:
            self.cmd.bound.arguments.setdefault(self.param.name, {})
            parts = value.split('=')
            name = parts[0]
            if self.cmd.posix:
                name = name.lstrip('-')
            value = '='.join(parts[1:])
            self.cmd.bound.arguments[self.param.name][name] = value
        else:
            self.cmd.bound.arguments[self.param.name] = value

    def cast(self, value):
        """Cast a string argument from the CLI into a Python object."""
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
        """Return True if the CLI arg matches an alias of this argument."""
        if arg in self.negates:
            return True
        if self.iskw and self.param.annotation == bool and arg in self.alias:
            return True
        for alias in self.alias:
            if arg.startswith(alias + '='):
                return True

    def match(self, arg):
        """Return the value extracted from a matching CLI argument."""
        if self.aliasmatch(arg):
            if self.param.annotation != bool or '=' in arg:
                for alias in self.alias:
                    if arg.startswith(alias):
                        arg = arg[len(alias):]
                        if arg.startswith('='):
                            arg = arg[1:]
                        return arg
        return arg

    def take(self, arg):
        """Return False if it doesn't accept this arg, otherwise bind it."""
        if not self.accepts:
            return

        if self.aliasmatch(arg):
            self.value = self.cast(self.match(arg))
            return True

        if self.param.kind == self.param.VAR_KEYWORD:
            if arg.startswith('**{') and arg.endswith('}'):
                self.cmd.bound.arguments[self.param.name] = json.loads(arg[2:])
                return True

        elif self.param.kind == self.param.VAR_POSITIONAL:
            if arg.startswith('*[') and arg.endswith(']'):
                self.cmd.bound.arguments[self.param.name] = json.loads(arg[1:])
                return True

        # look ahead for keyword arguments that would match this
        # so that you can skip arguments that are both keyword and positional
        # ie. `foo b=x` binds 'x' to 'b' in foo(a=None, b=None)
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
            if re.match('^-?-?[^=]+=', arg):
                return
            elif arg.startswith('**{') and arg.endswith('}'):
                return

        if (
            self.iskw
            and self.alias[0].startswith('-')
            and self.param.annotation != bool
            and '=' not in arg
            and arg in self.alias
        ):
            self.taking = True
            return True

        if self.taking:
            arg = self.alias[0] + '=' + arg

        value = self.match(arg)

        if value is not None:
            self.value = self.cast(value)
            return True

    def factory_value(self):
        """
        Run the factory function and return the value.

        If the factory function takes a `cmd` argument, it will pass the
        command object.

        If the factory function takes an `arg` argument, it will pass self.
        """
        kwargs = dict()
        sig = inspect.signature(self.factory)
        if 'cmd' in sig.parameters:
            kwargs['cmd'] = self.cmd
        if 'arg' in sig.parameters:
            kwargs['arg'] = self
        return self.factory(**kwargs)
