# flake8: noqa
from .cli import (
    cmd,
    arg,
    hide,
    retrieve,
    Argument,
    Command,
    Group,
    EntryPoint,
)
from .asyncio import async_resolve, async_run, Queue
from .colors import colors as c

from .configuration import Configuration, cfg
from .display import diff, diff_data, render, print, highlight, yaml_highlight
try:
    import fcntl
except ImportError:
    """ windows """
else:
    from .lock import Lock
from .log import configure, log
from .mask import Mask
from .table import Table


def which(cmd):
    """ Wrapper around shutil.which, and also check for ~/.local/bin. """
    import shutil
    path = shutil.which(cmd)
    if path:
        return path

    path = Path(os.getenv('HOME')) / '.local/bin' / cmd
    if path.exists():
        return str(path)


def mutable(obj):
    types = (
        int,
        float,
        str,
        tuple,
        frozenset,
        bool,
        bytes,
    )
    return not isinstance(obj, types)
