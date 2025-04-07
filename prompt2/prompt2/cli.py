"""
Template based prompts on the CLI
"""

import cli2
import functools
import importlib
import inspect
import jinja2
import os
from pathlib import Path

import prompt2


class PromptCommand(cli2.Command):
    def __init__(self, *args, **kwargs):
        self._model = None
        self._parser = None
        self._prompt = None
        self.not_found_error = None
        super().__init__(*args, **kwargs)

    def parse(self, *argv):
        super().parse(*argv)

        try:
            # auto cast variables dependending on each other ...
            if 'model' in self:
                if self['model'].value:
                    self['model'].value = prompt2.Model.get(
                        self['model'].value,
                        strict=True,
                    )
                else:
                    self['model'].value = prompt2.Model.get()

            if 'parser' in self and self['parser'].value:
                self['parser'].value = (
                    self['model'].value.parser(self['parser'].value)
                )

            if 'prompt' in self:
                context = dict()

                try:
                    context = self['context'].value
                except (cli2.Cli2ValueError, KeyError):
                    pass

                self['prompt'].value = prompt2.Prompt(
                    self['prompt'].value,
                    **context,
                )

        except prompt2.NotFoundError as exc:
            # we'll deal with that during actual call
            self.not_found_error = exc
        except cli2.Cli2ValueError:
            pass

    def call(self, *args, **kwargs):
        if self.not_found_error:
            exc = self.not_found_error
            print(cli2.t.red.bold(exc.title) + f': {exc.name}\n')
            if exc.available:
                print(cli2.t.green.bold('AVAILABLE') + ':')
                return exc.available
            elif exc.searched:
                print(cli2.t.green.bold('SEARCHED') + ':')
                return exc.searched
        return super().call(*args, **kwargs)

    def handle_exception(self, exc):
        if isinstance(exc, jinja2.UndefinedError):
            print(cli2.t.red.bold(f'MISSING CONTEXT VARIABLE'))
            print(exc.message)
        else:
            raise exc


cli = cli2.Group(
    doc=__doc__,
    cmdclass=PromptCommand,
)


@cli.cmd(color='green')
def paths():
    """
    Return prompt paths
    """
    return [str(p) for p in prompt2.Prompt.paths()]


@cli.cmd(color='green', name='list')
def prompts():
    """
    List available prompts
    """
    paths = dict()
    for path in prompt2.Prompt.paths():
        if not path.exists():
            continue
        paths.update({
            p.name[:-4]: str(p)
            for p in path.iterdir()
        })
    return paths


@cli.cmd
def edit(name, local: bool=False):
    """
    Edit a prompt.

    :param name: Prompt name.
    :param local: Enable this to store in $CWD/.prompt2 instead of
                  $HOME/.prompt2
    """
    local_path = prompt2.Prompt.LOCAL_PATH / f'{name}.txt'
    if local_path.exists() or local:
        path = local_path
    else:
        user_path = prompt2.Prompt.USER_PATH / f'{name}.txt'
        if user_path.exists():
            path = user_path
        else:
            path = local_path if local else user_path

    if path.exists():
        with path.open('r') as f:
            content = f.read()
    else:
        content = (
            'You are called by an automated process, you MUST'
            ' structure your reply or you will crash it!'
        )

    content = cli2.editor(content)
    if content:
        path.parent.mkdir(exist_ok=True, parents=True)
        with path.open('w') as f:
            f.write(content)
        cli2.log.info('wrote', path=str(path), content=content)

        print(cli2.t.bold('SAVED PROMPT:'))
        print(content + '\n')
        print(cli2.t.green(f'Saved to {path}'))


@cli.cmd(color='green')
def show(prompt):
    """
    Show a prompt

    :param prompt: Prompt name
    """
    print(cli2.t.y.bold('PATH'))
    print(cli2.t.orange(prompt.path))
    print()

    print(cli2.t.y.bold('CONTENT'))
    print(prompt.parts[0])


@cli.cmd
def render(prompt, **context):
    """
    Render a prompt with a given template context.

    :param prompt: Prompt name
    :param context: Context variables.
    """
    print(cli2.t.y.bold('PATH'))
    print(cli2.t.orange(prompt.path))
    print()

    print(cli2.t.y.bold('OUTPUT'))
    print(prompt.render())


@cli.cmd
def parser(name):
    """
    Show a parser

    :param name: Parser name to display
    """
    plugins = importlib.metadata.entry_points(
        name=name,
        group=prompt2.Parser.entry_point,
    )
    if not plugins:
        print(cli2.t.red.bold('PARSER NOT FOUND') + f': {name}\n')
        print(cli2.t.green.bold('AVAILABLE') + ':')
        return [*parsers().keys()]
    plugin = [*plugins][0]
    parser = plugin.load()

    path = inspect.getfile(parser)
    print(cli2.t.y.bold('PATH'))
    print(cli2.t.o(path))
    print()

    source = inspect.getsource(parser)
    print(cli2.highlight(source, 'Python'))


@cli.cmd
def parsers():
    """
    List registered parsers
    """
    return {
        plugin.name: plugin.value
        for plugin in importlib.metadata.entry_points(
            group=prompt2.Parser.entry_point,
        )
    }


@cli.cmd
def messages(prompt, parser=None, model=None, **context):
    """
    Render prompt messages with a given template context.

    :param name: Prompt name
    :param parser: Parser name if any
    :param model: Model name to use, if any
    :param context: Context variables.
    """
    messages = prompt.messages()
    if parser:
        messages = parser.messages(messages)

    print(cli2.t.y.bold('PATH'))
    print(cli2.t.orange(prompt.path))
    print()
    print(cli2.t.y.bold('OUTPUT'))
    return messages


@cli.cmd
async def send(prompt, parser=None, model=None, **context):
    """
    Send a prompt, rendered with a context, on a model with a parser.

    :param prompt: Prompt name
    :param parser: Parser name if any
    :param model: Model name to use, if any
    :param context: Context variables
    """
    return await model(prompt, parser)
