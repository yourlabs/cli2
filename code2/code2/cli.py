"""
AI Coding
"""

import cli2
import functools
import importlib
import os
from pathlib import Path

from .context import Context
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

        # Load all commands in default context anyway
        self.load_context(self, self.project.contexts[context_name])

        # Add project management commands
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
