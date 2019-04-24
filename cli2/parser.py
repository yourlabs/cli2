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

        for arg in self.argv:
            self.append(arg)

    def get_option(self, name):
        name = name.lstrip('-')
        for option in self.command.options.values():
            if name == option.name or name == option.alias:
                return option
        return False

    def append(self, arg):
        spec = inspect.getfullargspec(self.command.target)
        filled = False
        if not spec.varargs and len(spec.args) == len(self.funcargs):
            filled = True

        if filled:
            self.extraargs.append(arg)

        if arg.count('=') == 1:
            if arg.startswith('-'):
                key, value = arg.lstrip('-').split('=')
                option = self.get_option(key)
                if option and (not option.immediate or self.immediate):
                    self.options[option.name] = value
                else:
                    self.immediate = False
                    self.dashkwargs[key] = value
            else:
                self.immediate = False
                key, value = arg.split('=', 1)
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
                self.funcargs.append(arg)
