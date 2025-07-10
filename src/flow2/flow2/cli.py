"""
YAML+Jinja based workflows on the CLI
"""

import cli2
import importlib.metadata

from flow2.flow import Flow
from cli2.file import FileCommand, FileCommands


class FlowCommand(FileCommand):
    file_cls = Flow
    file_arg = 'flow'


class FlowCommands(FileCommands):
    def __init__(self):
        super().__init__(Flow, lexer='YamlJinja')

    @cli2.cmd(cls=FlowCommand)
    def edit(self, name, local: bool = False):
        """
        Edit a flow.

        :param name: flow name.
        :param local: Enable this to store in $CWD/.flow2 instead of
                      $HOME/.flow2
        """
        return super().edit(name, local)

    @cli2.cmd(color='green', cls=FlowCommand)
    def show(self, flow, _cli2=None):
        """
        Show a flow

        :param flow: flow name
        """
        return super().show(flow, _cli2)

    @cli2.cmd(color='green', cls=FlowCommand)
    async def render(self, flow, **context):
        """
        Render a flow with a given template context.

        :param flow: flow name
        :param context: Context variables.
        """
        return super().render(flow, **context)

    @cli2.cmd(cls=FlowCommand)
    async def run(self, flow, **context):
        """
        Render a flow with a given template context.

        :param flow: flow name
        :param context: Context variables.
        """
        context = await flow.run(**context)
        return context[list(context.keys())[-1]]

    @cli2.cmd(color='gray', cls=FlowCommand)
    def plugins(self):
        """
        List registered plugins.
        """
        plugins = importlib.metadata.entry_points(
            group=Flow.entry_point,
        )
        return {plugin.name: plugin.value for plugin in plugins}


cli = cli2.Group(doc=__doc__)
cli.load(FlowCommands())
