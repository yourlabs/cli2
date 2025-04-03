"""
AI powered coding assistant CLI with context and plugin based morphing.
"""

import cli2
import functools
import importlib
import os
from pathlib import Path

from .context import Context
from .prompt import Prompt
from .project import Project


class ContextCommands:
    """
    Manage LLM contexts
    """
    def __init__(self, project):
        self.project = project
        self.path = self.project.path / '.code2/contexts'

    @cli2.cmd(color='green')
    def list(self):
        """ List project contexts """
        return {path.name: str(path) for path in self.path.iterdir()}

    @cli2.cmd
    def new(self, name, *description):
        """
        Create a new context to work in.

        While you don't need to create a context to work with code2, it'll be
        very helpful to work on different topics in your repository, pickup
        back where you left.

        While a context represents a context for the LLM session, think of it
        as a topic: your project has many topics which include features.

        A context is going to include:

        - chat and session history
        - relevant symbols in code
        - files to new automatically to the chat

        Example to new a context with a description:

            # new a context named python412 to upgrade your project to Python 4.12
            code2 context new python412

            # new a context named djupgrade with a description:
            code2 context new djupgrade Upgrade Django to 8.12

            # run a command in a context
            code2 djupgrade analyze how am I going to upgrade this to django 8.12?

        :param name: One word name for the context
        :param description: Any subsequent word will be newed to description
        """
        path = self.path / name
        path.mkdir(exist_ok=True, parents=True)
        if description:
            description = ' '.join(description)
            with (path / 'description').open('w') as f:
                f.write(description)

    @cli2.cmd
    def archive(self, name):
        """
        Archive a context

        It won't show in the CLI anymore until next time you switch to it.

        :param name: Context name
        """
        path = self.path / name / 'archived'
        path.touch()


class PromptsGroup(cli2.Group):
    def __init__(self, project, *args, **kwargs):
        self.project = project
        super().__init__(*args, **kwargs)

    def __call__(self, *argv):
        self.load(self)
        self.load(self.project.prompt())

        for name in self.project.prompt().names():
            self[name] = PromptGroup(
                self.project,
                name,
                doc=f'Commands for {name} prompt',
            )

        return super().__call__(*argv)

    @cli2.cmd
    def new(self, name, user: bool=False):
        """
        Open $EDITOR to create a new prompt.

        :param name: Name of the new prompt
        :param user: Enable this to write in ~/.code2/prompts instead of
                     ./.code2/prompts
        """
        if user:
            path = Path(os.getenv('HOME'))
        else:
            path = Path(self.project.path)
        path = path / f'.code2/prompts/{name}.txt'
        content = cli2.editor(
            'You are called by an automated process '
            'as such, you MUST structure your reply or you will crash it'
        )
        if content:
            path.parent.mkdir(exist_ok=True, parents=True)
            with path.open('w') as f:
                f.write(content)
            cli2.log.info('wrote', path=str(path), content=content)


class PromptGroup(cli2.Group):
    def __init__(self, project, name, *args, **kwargs):
        self.project = project
        self.name = name
        super().__init__(*args, **kwargs)

    def __call__(self, *argv):
        self.doc = '\n'.join([
            cli2.t.bold('SOURCE'),
            cli2.t.b(self.prompt.find(self.name)),
            '',
            cli2.t.bold('CONTENT'),
            self.prompt.parts[0],
        ])
        self.load(self)
        return super().__call__(*argv)

    @functools.cached_property
    def prompt(self):
        return self.project.prompt(self.name)

    @cli2.cmd
    def edit(self, user: bool=False):
        """
        Edit the prompt text in your $EDITOR

        This will edit the prompt for the project by default. Examples::

            # edit some_prompt for this project, in .code2/prompts/some_prompt.txt
            code2 prompt some_prompt edit

            # edit some_prompt for your user, in ~/.code2/prompts/some_prompt.txt
            code2 prompt some_prompt edit user

        :param user: Edit globally for your user
        """
        if user:
            path = Path(os.getenv('HOME'))
        else:
            path = Path(self.project.path)
        path = path / f'.code2/prompts/{self.name}.txt'
        result = cli2.editor(self.prompt.parts[0])
        if result:
            path.parent.mkdir(exist_ok=True, parents=True)
            with path.open('w') as f:
                f.write(result)

    @cli2.cmd
    def messages(self, **context):
        """
        Render a prompt's messages with a context.

        :param context: Context variables to render the prompt.
        """
        try:
            return self.prompt.messages(**context)
        except KeyError as exc:
            return f'Value required for: "{exc.args[0]}"'

    @cli2.cmd
    def render(self, **context):
        """
        Render a prompt with a context.

        :param context: Context variables to render the prompt.
        """
        try:
            return self.prompt.render(**context)
        except KeyError as exc:
            return f'Value required for: "{exc.args[0]}"'

    @cli2.cmd
    async def send(self, parser=None, model=None, **context):
        """
        Send the prompt and return the reply.

        :param parser: Parser name, list them with code2 parsers
        :param model: Model name, ie. architect, editor, whatever you have in
                      $MODEL_modelname.
        """
        model = self.project.model(model)
        self.prompt.context.update(context)
        try:
            return await model.process(self.prompt, parser)
        except KeyError as exc:
            return f'Value required for: "{exc.args[0]}"'


class DBCommand(cli2.Command):
    def __call__(self, *argv):
        from . import orm
        orm.db.connect()
        orm.init()
        return super().__call__(*argv)

    def post_call(self):
        from . import orm
        orm.db.close()
        cli2.log.debug('Closed DB connection')


class ConsoleScript(cli2.Group):
    def __call__(self, *argv):
        context_name = 'default'
        self.cmdclass = DBCommand
        self.doc = __doc__

        self.project = Project(os.getcwd())
        cli2.cfg.defaults.update(dict(
            CODE2_DB=f'sqlite:///{self.project.path}/.code2/db.sqlite3',
        ))

        # Command group to manage prompts
        self['prompt'] = PromptsGroup(
            self.project,
            doc='Prompt management',
        )

        # Load all commands in default context anyway
        self.load_context(self, self.project.contexts[context_name])

        # Add project management commands
        if os.getenv('CODE2_ALPHA'):
            group = self.group('project', doc='Project management commands')

            # actually load the project management commands
            group.load(self.project)

            # Find contexts to lazy load from project configuration
            for name, context in self.project.contexts.items():
                if context.archived:
                    continue

                if name in self:
                    group = self[name]
                else:
                    group = self.group(name, doc=f'Run in context: {name}')
                self.load_context(group, context)

            # And a group to manage contexts
            self.group(
                'context',
                doc=ContextCommands.__doc__,
            ).load(ContextCommands(self.project))

        return super().__call__(*argv)

    def load_context(self, group, context):
        for plugin in importlib.metadata.entry_points(group='code2_workflow'):
            obj = plugin.load()(self.project, context)

            group.add(
                obj.run,
                name=plugin.name,
                doc=obj.run.__doc__,
            )

            # working around an evil spec
            cmd = group[plugin.name]

        # also load context commands
        group.load(context)


cli = ConsoleScript()
