# flake8: noqa
from .argument import Argument
from .colors import colors as c
import importlib.metadata

from .command import Command
from .decorators import arg, cmd
from .display import diff, print
from .group import Group
from .node import Node
from .table import Table


def retrieve(path):
    # find all matching entrypoints
    name = path.split(" ")[0]
    matches = [
        entry_point
        for entry_point in importlib.metadata.entry_points()
        if entry_point.name == name
        and entry_point.group == 'console_scripts'
    ]

    if not matches:
        raise Exception(f'Entry point {path} not installed')

    # take the first entry point, navigate up to the target sub-command
    obj = matches[0].load().__self__
    obj.name = name
    for arg in path.split(" ")[1:]:
        obj = obj[arg]
    return obj
