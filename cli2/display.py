"""
Generic pretty display utils.

This module defines a print function that's supposed to be able to pretty-print
anything, as well as a pretty diff printer.
"""
import os

from rich.console import Console
from rich.syntax import Syntax


console_kwargs = dict()
if os.getenv('CI'):
    console_kwargs['force_terminal'] = True
console = Console(**console_kwargs)


NO_COLOR = bool(os.getenv('NO_COLOR', ''))
_print = print


def highlight(string, lexer):
    if NO_COLOR:
        return string

    return Syntax(string, lexer)


def yaml_dump(data):
    import yaml
    if isinstance(data, dict):
        # ensure that objects inheriting from dict render nicely
        data = dict(data)
    return yaml.dump(data, indent=4, width=float('inf'))


def print(*args, **kwargs):
    """
    Try to print the args, pass the kwargs to actual print method.

    If any arg is parseable as JSON then it'l be parsed.

    Then, it'll be dumped as colored YAML.

    Set the env var `NO_COLORS` to anything to
    prevent `cli2.print` from printing colors.

    .. code-block:: python

        import cli2

        # pretty print some_object
        cli2.print(some_object)

    This outputs colors by default, set the env var `NO_COLORS` to anything to
    prevent printing colors.
    """
    try:
        import jsonlight as json
    except ImportError:
        import json

    for arg in args:
        try:  # deal with response objects
            arg = arg.json()
        except (TypeError, AttributeError):
            pass

        try:  # is this json?
            arg = json.loads(arg)
        except:  # noqa
            pass

        string = arg if isinstance(arg, str) else yaml_dump(arg)
        console.print(highlight(string.strip(), 'yaml'), **kwargs)


def diff(diff, **kwargs):
    """
    Pretty-print a diff generated by Python's standard difflib.unified_diff
    method.

    .. code-block:: python

        # pretty print a diff
        cli2.diff(difflib.unified_diff(old, new))
    """
    string = "\n".join([
        line.strip() for line in diff if line.strip()
    ])
    console.print(highlight(string, 'diff'), **kwargs)
