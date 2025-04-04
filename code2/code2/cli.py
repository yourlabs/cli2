"""
AI code assistant
"""

import cli2
import importlib
import os

from .context import Context
from .project import Project
from .engine import Engine


class ContextCommands:
    """
    Manage LLM contexts

    You are in the default context by default and don't need to worry about
    contexts until you want to work on several topics at the same time.
    """
    @cli2.cmd(color='green')
    def list(self):
        """ List project contexts """

    @cli2.cmd
    def add(self, name, *description):
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
        - files to add automatically to the chat

        Example to add a context with a description:

            # add a context named python412 to upgrade your project to Python 4.12
            code2 context add python412

            # add a context named djupgrade with a description:
            code2 context add djupgrade Upgrade Django to 8.12

        :param name: One word name for the context
        :param description: Any subsequent word will be added to description
        """

    @cli2.cmd
    def archive(self, name):
        """
        Archive a context

        It won't show in the CLI anymore until next time you switch to it.

        :param name: Context name
        """

    @cli2.cmd
    def switch(self, name, local: bool=False):
        """
        Switch to a context.

        :param name: Context name
        :param local: Enable to switch to this context locally only, based on
                      the parent shell PID. By default, it switches the context
                      globally, for all your shells open in your repository
                      which are not in a local context.
        """


class ConsoleScript(cli2.Group):
    def __call__(self, *argv):
        self.project = Project(os.getcwd())

        # Find contexts to lazy load from project configuration
        #for name, context in self.project.contexts.items():
        #    self.group(name).load(context)

        # Load all commands in default context anyway
        self.load_context(self.project.contexts['default'])

        # Add project management commands
        group = self.group('project')
        # TODO: should not have to do that ptach
        group.overrides['self']['factory'] = lambda: self.project
        # actually load the project management commands
        group.load(self.project)

        # And a group to manage contexts
        self.group(
            'context',
            doc=ContextCommands.__doc__,
        ).load(ContextCommands())

        return super().__call__(*argv)

    def load_context(self, context):
        for plugin in importlib.metadata.entry_points(group='code2_assist'):
            obj = plugin.load()

            cmd = self.add(
                obj.run_plugin,
                name=plugin.name,
                doc=obj.run.__doc__,
            )
            cmd.overrides['project']['factory'] = lambda: self.project
            cmd.overrides['context']['factory'] = lambda: context
            cmd.overrides['context']['name'] = lambda: plugin.name

        # also load context commands
        self.load(context)


cli = ConsoleScript()


#cli = cli2.Command(Engine.factory().run())

'''
from litellm import completion
from pathlib import Path
import os

from rich.console import Console
from rich.syntax import Syntax
from rich.markdown import Markdown

from .project import Project
from .parser import Parser
from .shell import Shell

console = Console()

cli2.cfg.defaults.update(
    MODEL='openrouter/deepseek/deepseek-chat',
    SYSTEM_PROMPT_EDITOR=Path(__file__).parent / 'system_prompt_editor.txt',
    SYSTEM_PROMPT_ARCHITECT=Path(__file__).parent / 'system_prompt_architect.txt',
)


class Engine:
    def system_prompt(self):
        prompt_system = cli2.cfg['SYSTEM_PROMPT']
        prompt_system_path = Path(prompt_system)
        if prompt_system_path.exists():
            with prompt_system_path.open('r') as f:
                return f.read()

    def __init__(self):
        self.project = Project(os.getcwd())
        self.shell = Shell(self.project)

    async def run(self):
        self.project.scan()
        await self.shell.run(self.request)

    async def request(self, user_input):
        system_prompt = self.system_prompt().format(path=os.getcwd())
        system_prompt += f'\n\nAvailable files: {" ".join(self.project.files())}'

        messages = [
            dict(
                role='system',
                content=system_prompt,
            ),
            dict(
                role='user',
                content=user_input,
            ),
        ]
        cli2.log.debug('messages', json=messages)

        stream = completion(
            model=cli2.cfg['MODEL'],
            messages=messages,
            max_tokens=16384,
            stream=True,
            temperature=.7,
            top_p=0.9,
        )

        full_content = ""
        for chunk in stream:
            if hasattr(chunk, 'choices') and chunk.choices:
                delta = chunk.choices[0].delta
                if hasattr(delta, 'content') and delta.content is not None:
                    full_content += delta.content

        await self.handle_response(full_content)

    async def handle_response(self, full_content):
        cli2.log.debug('response', content=full_content)
        md = Markdown(full_content)

        tokens = []

        def print_tokens():
            nonlocal tokens
            _md = Markdown('')
            _md.parsed = tokens
            console.print(_md)
            tokens = []

        for token in md.parsed:
            tokens.append(token)
            if token.tag == 'code':
                if token.info == 'bash':
                    print_tokens()
                    await self.shell.run_command(token.content.strip())
                if token.info == 'diff':
                    print_tokens()
                    await self.shell.diff_apply(token.content)
                else:
                    continue
        if tokens:
            print_tokens()

'''

