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

        # Load all commands in default context anyway
        self.load_context(self.project.contexts['default'])

        # Add project management commands
        group = self.group('project')
        # actually load the project management commands
        group.load(self.project)
        for name, cmd in group.items():
            # TODO: should not have to do that ptach
            cmd.overrides['self']['factory'] = lambda: self.project

        # Find contexts to lazy load from project configuration
        for name, context in self.project.contexts.items():
            if name in self:
                self[name].load(context)
            else:
                self.group(name).load(context)

            for name, cmd in self[name].items():
                # TODO: should not have to do that ptach
                if 'self' not in cmd.overrides:
                    cmd.overrides['self']['factory'] = lambda: context

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
