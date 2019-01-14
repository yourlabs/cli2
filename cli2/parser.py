

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
        self.options = {}

    def parse(self):
        from .introspection import Callable
        from .console_script import Group

        for arg in self.argv_all:
            if not self.command and arg in self.group:
                item = self.group[arg]

                if isinstance(item, Group):
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
        if '=' in arg:
            if arg.startswith('-'):
                key, value = arg.lstrip('-').split('=')
                option = self.get_option(key)
                if option:
                    self.options[option.name] = value
                else:
                    self.dashkwargs[key] = value
            else:
                key, value = arg.split('=', 1)
                self.funckwargs[key] = value

        else:
            if arg.startswith('-'):
                stripped = arg.lstrip('-')
                option = self.get_option(stripped)
                if option:
                    self.options[option.name] = True
                else:
                    self.dashargs.append(stripped)
            else:
                self.funcargs.append(arg)
