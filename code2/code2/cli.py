"""
AI Coding
"""

import cli2
import functools
import importlib
import os
from pathlib import Path

from .context import Context
from code2 import project


class ContextCommands:
    """
    Manage LLM contexts
    """
    def __init__(self, project):
        self.project = project
        self.path = self.project.path / '.code2/contexts'

    @cli2.cmd(color='green')
    def show(self, name='default'):
        """
        Edit a context prompt, or the default one.

        :param name: Context name, avoid spaces, use . to namespace
        """
        if name in self.project.contexts:
            path = self.project.contexts[name].prompt_path
            with path.open('r') as f:
                return f.read()
        return cli2.t.red.bold(f'CONTEXT NOT FOUND {name}')

    @cli2.cmd(color='green')
    def edit(self, name='default'):
        """
        Edit a given context prompt, or the defaulst one.

        :param name: Context name, avoid spaces, use . to namespace
        """
        cli2.editor(path=Context(project, self.path / name).prompt_path)

    @cli2.cmd(color='green')
    def list(self):
        """ List project contexts """
        return {path.name: str(path) for path in self.path.iterdir()}

    @cli2.cmd
    def archive(self, name):
        """
        Archive a context

        It will still show in the list command, but won't show in the CLI until
        next time you switch to it.

        :param name: Context name
        """
        path = self.path / name / 'archived'
        path.touch()


class ConsoleScript(cli2.Group):
    def __call__(self, *argv):
        context_name = 'default'
        self.doc = __doc__

        # Load all commands in default context anyway
        self.load_context(self, project.contexts[context_name])

        # Add project management commands
        group = self.group('project', doc='Project management commands')

        # actually load the project management commands
        group.load(project)

        # Find contexts to lazy load from project configuration
        for name, context in project.contexts.items():
            if context.archived:
                continue

            if name in self:
                group = self[name]
            else:
                group = self.group(name, doc=f'Run in context: {name}')
            self.load_context(group, context)

        # And a group to manage contexts
        self.load(ContextCommands(project))

        return super().__call__(*argv)

    def load_context(self, group, context):
        for plugin in importlib.metadata.entry_points(group='code2_workflow'):
            try:
                obj = plugin.load()(project, context)
            except:
                cli2.log.exception(
                    f'Failed loading plugin',
                    name=plugin.name,
                    value=plugin.value,
                )
            else:
                group.add(
                    obj.run_plugin,
                    name=plugin.name,
                    doc=obj.run.__doc__,
                )

                # working around an evil spec
                cmd = group[plugin.name]

        # also load context commands
        group.load(context)


class DBCommand(cli2.Command):
    def async_mode(self):
        return True

    async def async_call(self, *argv):
        await project.db.session_open()
        return await super().async_call(*argv)

    async def post_call(self):
        await project.db.session_close()


cli = ConsoleScript(cmdclass=DBCommand)
