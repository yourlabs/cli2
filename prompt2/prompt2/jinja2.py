"""
Functions that will be exposed in Jinja2.

Add yours over the prompt2_jinja2 entry point plugin!

Note that all prompt paths are added to the Jinja2 loader, so, you can already
include your prompts in your prompts::

    {% include('your_prompt.txt') %}
"""
import cli2
import prompt2


def read(path):
    """
    Read a file from the filesystem

    :param path: Path of the file to read.
    """
    with open(path, 'r') as f:
        content = f.read()
    return content


def shell(command):
    """
    Execute a command and return the full output.

    :param command: String or args list.
    """
    async def _(command):
        proc = await cli2.Proc(command, quiet=True).wait()
        return proc.out
    return cli2.async_run(_(command))
