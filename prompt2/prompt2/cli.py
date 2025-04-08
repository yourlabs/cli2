"""
Template based prompts on the CLI
"""

import cli2
import importlib
import inspect
import jinja2

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
                    configuration = prompt2.Model.configuration_get(
                        self['model'].value,
                        strict=True,
                    )
                    backend = prompt2.Model.backend_factory(configuration)
                    self['model'].value = prompt2.Model(backend)
                else:
                    self['model'].value = prompt2.Model()

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


@cli.cmd
async def ask(*args, parser=None, model=None):
    """
    Ask a question from the CLI

    Example:

        prompt2 ask write a hello world in python

    :param args: Question to ask
    :param parser: Parser name if any
    :param model: Model name to use, if any
    """
    return await model(prompt2.Prompt(content=' '.join(args)), parser)


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
    default_content = (
        'You are called by an automated process, you MUST'
        ' structure your reply or you will crash it!'
    )

    try:
        prompt = prompt2.Prompt(name)
    except prompt2.Prompt.NotFoundError:
        if local:
            path = prompt2.Prompt.local_path
        else:
            path = prompt2.Prompt.user_path
        path = path / f'{name}.txt'
        kwargs = dict(content=default_content)
    else:
        path = prompt.path
        kwargs = dict(content=prompt.path)

    content = cli2.editor(**kwargs)
    if not path.exists():
        path.parent.mkdir(exist_ok=True, parents=True)
        with path.open('w') as f:
            f.write(content)
        cli2.log.info('wrote', path=str(path), content=content)

    print(cli2.t.bold('SAVED PROMPT: ') + cli2.t.green(f'{path}'))


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
    print(prompt.content)


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
