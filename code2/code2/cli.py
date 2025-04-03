"""
AI code assistant
"""

from litellm import completion
from pathlib import Path
import cli2
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
    SYSTEM_PROMPT=Path(__file__).parent / 'system_prompt.txt',
)


class Engine:
    def system_prompt(self):
        prompt_system = cli2.cfg['SYSTEM_PROMPT']
        prompt_system_path = Path(prompt_system)
        if prompt_system_path.exists():
            with prompt_system_path.open('r') as f:
                return f.read()

    async def run(self):
        self.project = Project(os.getcwd())
        self.project.scan()

        self.shell = Shell(self.project)
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

        response = completion(
            model=cli2.cfg['MODEL'],
            messages=messages,
        )

        content = response.choices[0].message.content
        cli2.log.debug('response', content=content)

        parsed_ops = Parser().parse(content)
        cli2.log.info('operations', json=parsed_ops)

        return parsed_ops


cli = cli2.Command(Engine().run)
