"""
Generic pretty display utils.

This module defines a print function that's supposed to be able to pretty-print
anything, as well as a pretty diff printer.
"""
import os
import sys

try:
    import jsonlight as json
except ImportError:
    import json


_print = print


def highlight(string, lexer):
    FORCE_COLOR = bool(os.getenv('FORCE_COLOR', ''))
    if not sys.stdout.isatty() and not FORCE_COLOR:
        return string

    try:
        import pygments
        import pygments.lexers
        import pygments.formatters
    except ImportError:
        return string

    formatter = pygments.formatters.TerminalFormatter()
    lexer = getattr(pygments.lexers, lexer + 'Lexer')()
    return pygments.highlight(string, lexer, formatter)


def yaml_dump(data):
    import yaml
    if isinstance(data, dict):
        # ensure that objects inheriting from dict render nicely
        data = dict(data)
    return yaml.dump(data, indent=4, width=float('inf'))


def yaml_highlight(yaml_string):
    return highlight(yaml_string, 'Yaml')


def render(arg, highlight=True):
    """
    Try to render arg as yaml.

    If the arg has a ``.json()`` method, it'll be called.
    If it is parseable as JSON then it'l be parsed as such.
    Then, it'll be dumped as colored YAML.

    Set the env var `FORCE_COLOR` to anything to force into printing colors
    even if terminal is non-interactive (ie. gitlab-ci)

    .. code-block:: python

        # pretty render some_object
        print(cli2.render(some_object))
    """
    try:  # deal with response objects
        arg = arg.json()
    except:  # noqa
        pass

    try:  # is this json?
        arg = json.loads(arg)
    except:  # noqa
        pass

    # does this wants to show specific data to cli2?
    try:
        arg = arg.cli2_display
    except AttributeError:
        pass

    string = arg if isinstance(arg, str) else yaml_dump(arg)
    if not highlight:
        return string
    return yaml_highlight(string)


def print(*args, **kwargs):
    """
    Try to print the :py:func:`render`'ed args, pass the kwargs to actual print
    method.

    .. code-block:: python

        # pretty print some_object
        cli2.print(some_object)
    """
    for arg in args:
        _print(render(arg), **kwargs)


def diff_highlight(diff):
    output = '\n'.join([line.rstrip() for line in diff if line.strip()])
    return highlight(output, 'Diff')


def diff(diff, **kwargs):
    """
    Pretty-print a diff generated by Python's standard difflib.unified_diff
    method.

    .. code-block:: python

        # pretty print a diff
        cli2.diff(difflib.unified_diff(old, new))
    """
    _print(diff_highlight(diff), **kwargs)
