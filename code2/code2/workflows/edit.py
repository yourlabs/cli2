import cli2
import difflib
import os
import re
import subprocess
import sys
from pathlib import Path

from code2 import orm

from code2.markdown import mdprint
from code2.prompt import Prompt
from code2.workflow import WorkflowPlugin


FILE_HELP = '''
It is not clear
'''


class EditWorkflow(WorkflowPlugin):
    async def run(self, path, *request, _cli2=None):
        """
        Edit a file with AI.

        :param path: Path to the file to edit
        :param request: Your request to the AI
        """
        if not request:
            return _cli2.help(error='request is required')

        self.file = orm.File.select().where(
            orm.File.path.in_(request),
        )

        if not self.file:
            return FILE_HELP

        self.done = False
        while not self.done:
            self.do(request)
