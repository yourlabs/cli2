import cli2
import difflib
import os
import prompt2
import re
import subprocess
import sys
from pathlib import Path

from code2.markdown import mdprint
from code2.workflow import WorkflowPlugin


class CmdWorkflow(WorkflowPlugin):
    async def run(self, *command, _cli2=None):
        """
        Ask AI to fix a command based on its output.

        :param command: The command line to run
        """
        if not command:
            return _cli2.help(error='command is required')

        self.done = False
        while not self.done:
            await self.do(*command)

    async def do(self, *command):
        full_output, rc = await self.run_command(*command)

        if rc == 0:
            question = 'Command exited successfully, continue anyway?'
            if cli2.choice(question) != 'y':
                return

        architect = prompt2.Model('architect')
        prompt = prompt2.Prompt(
            'fix_files_for_output',
            output=full_output,
        )
        result = await architect(prompt)

        path = Path(result)
        if path.is_relative_to(self.project.path):
            path = path.relative_to(self.project.path)
            self.context.files(path)
        else:
            raise Exception('Not implemented yet')

        with path.open('r') as f:
            content = f.read()

        prompt = self.project.prompt(
            'fix_file_output',
            content=content,
            path=path,
            output=full_output,
        )
        instructions = await architect.process(prompt)
        mdprint(instructions)

        q = 'Do you want to edit the plan prior to getting the fixed code?'
        while cli2.choice(q, default='n') == 'y':
            instructions = cli2.editor(instructions)
            mdprint(instructions)
            q = 'Edit again?'

        prompt = self.project.prompt(
            'fix_file',
            path=path,
            content=content,
            instructions=instructions,
            output=full_output,
        )
        new_content = await architect.process(prompt, 'wholefile')
        cli2.diff(
            difflib.unified_diff(
                content.splitlines(),
                new_content.splitlines(),
                str(path),
                str(path),
            )
        )

        if cli2.choice('Apply patch?', default='y') == 'y':
            with path.open('w') as f:
                f.write(new_content)

        if cli2.choice('Run the command again?') != 'y':
            self.done = True
