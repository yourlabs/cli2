"""
Functions that will be exposed in Jinja2.

Add yours over the prompt2_jinja2 entry point plugin!

Note that all prompt paths are added to the Jinja2 loader, so, you can already
include your prompts in your prompts::

    {% include('your_prompt.txt') %}

Or even go crazy with ``{% extend %}`` and ``{% macro %}``!
"""
import cli2
import os


def file(path):
    """
    Show a file path content with context markers.

    It will render::

        path/to/file source code:
        ```
        <source code here>
        ```

    :param path: File path
    """
    return f'\n\n{path} source code:\n```\n{read(path)}\n```\n\n\n'


def read(path):
    """
    Read a file from the filesystem

    :param path: Path of the file to read.
    """
    with open(path, 'r') as f:
        content = f.read()
    return content


def shell(*command, **env):
    """
    Show a command output with context markers.

    It will render::


        Output of `command line`:
        ```
        <output here>
        ```

    :param command: Command
    :param env: Environment variables
    """
    proc = cli2.Proc(*command, quiet=True, **env).wait()
    return f'\n\nOutput of `{proc.cmd}`:\n```\n{proc.out}\n```\n\n\n'


def exec(*command, **env):
    """
    Execute a command and return the full output.

    :param command: String or args list.
    """
    return cli2.Proc(*command, quiet=True, **env).wait().out


def dir_list(*paths):
    """
    Show the list of directories within a path.

    Renders::

        Directories:
        - path/to/directory1
        - path/to/directory2

    :param path: Path to walk
    """
    result = ['Directory list:']
    if not paths:
        paths = [os.getcwd()]
    for path in paths:
        result += cli2.Find(path, flags='-type d').run()
    return '\n'.join(result)


def file_list(*paths):
    """
    Show the list of files within a path.

    Renders::

        Files:
        - path/to/file1
        - path/to/file2

    :param path: Path to walk
    """
    result = ['File list:']
    if not paths:
        paths = [os.getcwd()]
    for path in paths:
        result += cli2.Find(path, flags='-type f').run()
    return '\n'.join(result)


async def files_read(*paths):
    """
    Show the sources of files of given paths.

    Renders::

        path/to/file1 source code:
        ```
        ... code here ...
        ```

        path/to/file2 source code:
        ```
        ... code here ...
        ```
        - path/to/file2
    """
    if not paths:
        raise Exception('At least one path is required')

    result = []
    for name, content in await cli2.files_read(*paths):
        path = Path(name).relative_to(os.getcwd())
        result += [
            'Source for {path}:',
            '```',
            content,
            '```',
        ]
    return '\n\n' + '\n\n'.join(result)
