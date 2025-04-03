import cli2
from .base import WorkflowPlugin
from ..prompt.base import prompt_read, CreatePrompt


class CreateWorkflow(WorkflowPlugin):
    async def run(self, *purpose, _cli2=None):
        """
        Ask AI to create files from scratch.
        """
        if not purpose:
            return _cli2.help(error='purpose is required')

        result = await CreatePrompt().process(
            f'Description of the file to create: {" ".join(purpose)}'
        )
