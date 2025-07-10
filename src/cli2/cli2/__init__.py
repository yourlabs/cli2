# flake8: noqa

from .configuration import Configuration, cfg
cfg.defaults['CLI2_TRACEBACK_DISABLE'] = ''

from .cli import (
    cmd,
    arg,
    hide,
    retrieve,
    Argument,
    Command,
    Group,
    EntryPoint,
    Cli2Error,
    Cli2ValueError,
)
from .asyncio import async_resolve, files_read
from .queue import Queue
from .colors import colors as c
from .theme import theme, t
from .display import diff, diff_data, render, print, highlight, yaml_highlight
from .interactive import confirm, choice, editor
try:
    import fcntl
except ImportError:
    """ windows """
else:
    from .lock import Lock

from .log import configure, log, parse
from .mask import Mask
from .notlevenshtein import closest, closest_path
from .proc import Proc
from .find import Find
from .table import Table


import os

if not bool(cfg['CLI2_TRACEBACK_DISABLE']):
    from .traceback import enable
    enable()


def which(cmd):
    """ Wrapper around shutil.which, and also check for ~/.local/bin. """
    import shutil
    path = shutil.which(cmd)
    if path:
        return path

    from pathlib import Path
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
