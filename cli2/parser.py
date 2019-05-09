import inspect


class Parser:
    def __init__(self, argv_all, group=None):
        self.argv_all = argv_all
        self.root = group
        self.group = group
        self.command = None

        # this parse() will provision
        self.argv = []
        self.funcargs = []
        self.funckwargs = {}
        self.dashargs = []
        self.dashkwargs = {}
        self.extraargs = []
        self.options = {}

        self.immediate = True

    def parse(self):
        from .introspection import Callable
        from .console_script import BaseGroup

        for arg in self.argv_all:
            if not self.command and arg in self.group:
                item = self.group[arg]

                if isinstance(item, BaseGroup):
                    self.group = item
                elif isinstance(item, Callable):
                    self.command = item
            else:
                self.argv.append(arg)

        if not self.command:
            self.command = self.group[self.group.default_command]
        self.spec = inspect.getfullargspec(self.command.target)

        for arg in self.argv:
            self.append(arg)

    def get_option(self, name):
        name = name.lstrip('-')
        for option in self.command.options.values():
            if name == option.name or name == option.alias:
                return option
        return False

    @staticmethod
    def cast_val(value):
        """Attempt to cast CLI argument to int or float."""
        if value == 'None':
            return None
        try:
            return int(value)
        except ValueError:
            try:
                return float(value)
            except ValueError:
                return value

    def append(self, arg):
        filled = False
        if not self.spec.varargs and len(self.spec.args) == len(self.funcargs):
            filled = True

        if filled:
            self.extraargs.append(arg)

        if arg.count('=') == 1:
            if arg.startswith('-'):
                key, value = arg.lstrip('-').split('=')
                value = self.cast_val(value)
                option = self.get_option(key)
                if option and (not option.immediate or self.immediate):
                    self.options[option.name] = value
                else:
                    self.immediate = False
                    self.dashkwargs[key] = value
            else:
                self.immediate = False
                key, value = arg.split('=', 1)
                value = self.cast_val(value)
                self.funckwargs[key] = value

        else:
            if arg.startswith('-'):
                stripped = arg.lstrip('-')
                option = self.get_option(stripped)
                if option and (not option.immediate or self.immediate):
                    self.options[option.name] = True
                else:
                    self.immediate = False
                    self.dashargs.append(stripped)
            elif not filled:
                self.immediate = False
                self.funcargs.append(self.cast_val(arg))
