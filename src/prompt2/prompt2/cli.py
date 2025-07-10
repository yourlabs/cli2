"""
Template based prompts on CLI
"""


from cli2.file import FileCommand, FileCommands
import cli2
import importlib.metadata
import inspect
import jinja2
import prompt2


class ModelParserCommand(cli2.Command):
    def __init__(self, *args, **kwargs):
        self._model = None
        self._parser = None
        self.not_found_error = None
        super().__init__(*args, **kwargs)

    def model_parse(self):
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

    def parse(self, *argv):
        error = super().parse(*argv)
        if error:
            return error
        self.model_parse()

    def call(self, *args, **kwargs):
        if self.not_found_error:
            return self.handle_not_found(self.not_found_error)

        try:
            return super().call(*args, **kwargs)
        except prompt2.NotFoundError as exc:
            return self.handle_not_found(exc)


cli = cli2.Group('prompt2')


@cli.cmd(color='yellow', cls=ModelParserCommand)
async def ask(*args, parser=None, model=None, _cli2=None):
    """
    Ask a question from the CLI

    Example:

        prompt2 ask write a hello world in python

    :param args: Question to ask
    :param parser: Parser name if any
    :param model: Model name to use, if any
    """
    if not args:
        return _cli2.help(error='Ask a question please I am begging you!')
    await model(
        prompt2.Prompt(
            content=' '.join(args)
        ),
        parser,
    )


class PromptCommand(FileCommand, ModelParserCommand):
    file_cls = prompt2.Prompt
    file_arg = 'prompt'

    def parser_parse(self):
        if 'parser' in self:
            if self['parser'].value:
                self['parser'].value = (
                    self['model'].value.parser(self['parser'].value)
                )
            elif 'prompt' in self and self['prompt'].value:
                name = self['prompt'].value.metadata.get('parser', None)
                if name:
                    self['parser'].value = (
                        self['model'].value.parser(name)
                    )

    def parse(self, *argv):
        error = super().parse(*argv)
        if error:
            return error
        self.parser_parse()

    def handle_exception(self, exc):
        if isinstance(exc, jinja2.UndefinedError):
            prompt = self['prompt'].value
            print(
                cli2.t.bold('USED PROMPT: ')
                + cli2.t.green(f'{prompt.path}')
                + '\n'
            )
            print(cli2.t.bold('CONTENT:'))
            print(cli2.highlight(prompt.content, 'SqlJinja'))
            print()
            print(cli2.t.red.bold('MISSING CONTEXT VARIABLE'))
            print(exc.message)
        else:
            super().handle_exception(exc)


class PromptCommands(FileCommands):
    def __init__(self):
        super().__init__(prompt2.Prompt, lexer='SqlJinja')

    @cli2.cmd(cls=PromptCommand)
    def edit(self, name, local: bool = False):
        """
        Edit a prompt.

        :param name: prompt name.
        :param local: Enable this to store in $CWD/.prompt2 instead of
                      $HOME/.prompt2
        """
        return super().edit(name, local)

    @cli2.cmd(color='green', cls=PromptCommand)
    def show(self, prompt):
        """
        Show a prompt

        :param prompt: Prompt name
        """
        print(cli2.t.y.bold('PATH'))
        print(cli2.t.orange(prompt.path))
        print()

        if prompt.metadata:
            print(cli2.t.y.bold('METADATA'))
            cli2.print(prompt.metadata)
            print()

        print(cli2.t.y.bold('CONTENT'))
        print(prompt.content)

    @cli2.cmd(color='green', cls=PromptCommand)
    async def render(self, prompt, **context):
        """
        Render a prompt with a given template context.

        :param prompt: prompt name
        :param context: Context variables.
        """
        return super().render(prompt, **context)

    @cli2.cmd(color='green', cls=PromptCommand)
    async def messages(self, prompt, parser=None, model=None, **context):
        """
        Render prompt messages with a given template context.

        :param name: Prompt name
        :param parser: Parser name if any
        :param model: Model name to use, if any
        :param context: Context variables.
        """
        messages = await prompt.messages()
        if parser:
            messages = parser.messages(messages)

        print(cli2.t.y.bold('PATH'))
        print(cli2.t.orange(prompt.path))
        print()
        print(cli2.t.y.bold('OUTPUT'))
        return messages

    @cli2.cmd(cls=PromptCommand, color='yellow')
    async def send(self, prompt, parser=None, model=None, **context):
        """
        Send a prompt, rendered with a context, on a model with a parser.

        :param prompt: Prompt name
        :param parser: Parser name if any
        :param model: Model name to use, if any
        :param context: Context variables
        """
        return await model(prompt, parser)


cli.load(PromptCommands())


class ParserCommands:
    @cli2.cmd(color='gray', cls=ModelParserCommand)
    def parser(self, name):
        """
        Show a parser

        :param name: Parser name to display
        """
        parser = prompt2.Parser.get(name)

        path = inspect.getfile(parser)
        print(cli2.t.y.bold('PATH'))
        print(cli2.t.o(path))
        print()

        source = inspect.getsource(parser)
        print(cli2.highlight(source, 'Python'))

    @cli2.cmd(color='gray')
    def parsers(self):
        """
        List registered parsers
        """
        return {
            plugin.name: plugin.value
            for plugin in importlib.metadata.entry_points(
                group=prompt2.Parser.entry_point,
            )
        }


cli.load(ParserCommands())


@cli.cmd(color='gray')
def plugins():
    """
    List registered backend plugins
    """
    return {
        plugin.name: plugin.value
        for plugin in importlib.metadata.entry_points(
            group=prompt2.Plugin.entry_point,
        )
    }
