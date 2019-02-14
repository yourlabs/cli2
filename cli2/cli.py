"""
cli2 makes your python callbacks work on CLI too !

cli2 provides sub-commands to introspect python modules or callables docstrings
or to execute callables or help working with cli2 itself.
"""

import textwrap
import types

from .console_script import ConsoleScript, BaseGroup
from .command import command, option
from .exceptions import Cli2ArgsException
from .colors import GREEN, RED, RESET, YELLOW
from .introspection import docfile, Callable, Importable


def docmod(module_name):
    """Docstring for a module in dotted path.

    Example: cli2 docmod cli2
    """
    return BaseGroup.factory(module_name).doc


@command(color=GREEN)
def help(*args):
    """
    Get help for a command.

    Example::

        $ cli2 help help
    """
    console_script = ConsoleScript.singleton

    if not args:
        # show documentation for parsed group
        yield console_script.parser.group.doc
    else:
        # show command documentation if possible
        if args[0] in console_script:
            yield console_script[args[0]].doc
        else:
            importable = Importable.factory(args[0])
            if importable.target and not importable.is_module:
                yield importable.doc
            elif importable.module:
                if not importable.target:
                    yield f'{RED}Cannot import {args[0]}{RESET}'
                    yield ' '.join([
                        YELLOW,
                        'Showing help for',
                        importable.module.__name__ + RESET
                    ])
                yield BaseGroup.factory(importable.module.__name__).doc


@command(color=GREEN)
def debug(callback, *args, **kwargs):
    """
    Dump parsed variables.

    Example usage::

        cli2 debug test to=see --how -it=parses
    """
    cs = console_script
    parser = cs.parser
    yield textwrap.dedent(f'''
    Callable: {RED}{callback}{RESET}
    Args: {YELLOW}{args}{RESET}
    Kwargs: {YELLOW}{kwargs}{RESET}
    console_script.parser.options: {GREEN}{parser.options}{RESET}
    console_script.parser.dashargs: {GREEN}{parser.dashargs}{RESET}
    console_script.parser.dashkwargs: {GREEN}{parser.dashkwargs}{RESET}
    console_script.parser.extraargs: {GREEN}{parser.extraargs}{RESET}
    ''').strip()


@option('debug', help='Also print debug output', color=GREEN, alias='d')
def run(callback, *args, **kwargs):
    """
    Execute a python callback on the command line.

    To call your.module.callback('arg1', 'argN', kwarg1='foo'):

        cli2 your.module.callback arg1 argN kwarg1=foo

    You can also prefix arguments with a dash, those that contain equal sign
    will end in dict console_script.parser.dashkwargs, those without equal
    sign will end up in a list in console_script.parser.dashargs.

    For examples, try `cli2 debug`.
    For other commands, try `cli2 help`.
    """
    if console_script.parser.options.get('debug', False):
        print('HELLO')

    cb = Callable.factory(callback)

    if cb.target and not cb.is_module:
        try:
            result = cb(*args, **kwargs)
        except Cli2ArgsException as e:
            print(e)
            print(cb.doc)
            result = None
            console_script.exit_code = 1
        except Exception as e:
            out = [f'{RED}Running {callback}(']
            if args and kwargs:
                out.append(f'*{args}, **{kwargs}')
            elif args:
                out.append(f'*{args}')
            elif kwargs:
                out.append(f'**{kwargs}')
            out.append(f') raised {type(e)}{RESET}')

            e.args = (e.args[0] + '\n' + cb.doc,) + e.args[1:]
            raise

        if isinstance(result, types.GeneratorType):
            yield from result
        else:
            yield result

    else:
        if '.' in callback:
            yield f'{RED}Could not import callback: {callback}{RESET}'
        else:
            yield f'{RED}Cannot run a module{RESET}: try {callback}.something'

        if cb.module:
            yield ' '.join([
                'However we could import module',
                f'{GREEN}{cb.module.__name__}{RESET}',
            ])

            doc = docmod(cb.module.__name__)
            if doc:
                yield f'Showing help for {GREEN}{cb.module.__name__}{RESET}:'
                yield doc
            else:
                return f'Docstring not found in {cb.module.__name__}'
        elif callback != callback.split('.')[0]:
            yield ' '.join([
                RED,
                'Could not import module:',
                callback.split('.')[0],
                RESET,
            ])


console_script = ConsoleScript(
    __doc__,
    default_command='run'
).add_commands(
    help,
    run,
    debug,
    command(color=GREEN)(docmod),
    command(color=GREEN)(docfile),
)
