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
from .asyncio import async_resolve
from .colors import colors as c

from .configuration import Configuration, cfg
try:
    from .client import (
        ClientError,
        ResponseError,
        TokenGetError,
        RefusedResponseError,
        RetriesExceededError,
        FieldError,
        FieldValueError,
        FieldExternalizeError,
        Client,
        DateTimeField,
        Field,
        Handler,
        JSONStringField,
        Model,
        Paginator,
        Related,
    )
except ImportError:
    raise
    # httpx not installed
    pass
from .display import diff, diff_data, render, print, highlight
from .lock import Lock
from .log import configure, log, get_logger
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
