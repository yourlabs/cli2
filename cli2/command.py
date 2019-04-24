from .introspection import Callable


def command(**config):
    def wrap(cb):
        if 'cli2' not in cb.__dict__:
            name = config.pop('name', cb.__name__)
            cb.cli2 = Callable(name, cb, **config)
        else:
            cb.cli2.__dict__.update(config)
        return cb
    return wrap


class Option:
    def __init__(self, name, help=None, color=None, alias=None,
                 immediate=False):
        self.name = name
        self.help = help or 'Undocumented option'
        self.color = color or ''
        self.alias = alias
        self.immediate = immediate


def option(name, **cfg):
    def wrap(cb):
        if 'cli2' not in cb.__dict__:
            cb = command()(cb)
        cb.cli2.options[name] = Option(name, **cfg)
        return cb
    return wrap
