import collections

from .introspection import Callable
from .colors import YELLOW


class Command(Callable):
    def __init__(self, name, target, color=None, options=None, doc=None):
        super().__init__(name, target)
        self.color = color or YELLOW
        self.options = options or collections.OrderedDict()


def command(**config):
    def wrap(cb):
        if 'cli2' not in cb.__dict__:
            cb.cli2 = Command(cb.__name__, cb, **config)
        else:
            cb.cli2.__dict__.update(config)
        return cb
    return wrap


class Option:
    def __init__(self, name, help=None, color=None, alias=None):
        self.name = name
        self.help = help or 'Undocumented option'
        self.color = color or ''
        self.alias = alias


def option(name, **cfg):
    def wrap(cb):
        if 'cli2' not in cb.__dict__:
            cb = command()(cb)
        cb.cli2.options[name] = Option(name, **cfg)
        return cb
    return wrap
