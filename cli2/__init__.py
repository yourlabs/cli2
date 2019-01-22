# flake8: noqa
"""cli2 is like click but as laxist as docopts."""
from .colors import *  # noqa
from .exceptions import Cli2Exception, Cli2ArgsException
from .parser import Parser
from .introspection import docfile, Callable, Importable, DocDescriptor
from .command import command, option, Option
from .console_script import ConsoleScript, BaseGroup, Group
from .test import autotest
from .cli import debug, docmod, help, run
