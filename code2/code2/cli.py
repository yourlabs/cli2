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
        #system_prompt += f'\n\nAvailable files: {" ".join(self.project.files())}'

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
            temperature=.2,
        )

        full_content = ""
        for chunk in stream:
            if hasattr(chunk, 'choices') and chunk.choices:
                delta = chunk.choices[0].delta
                if hasattr(delta, 'content') and delta.content is not None:
                    print(delta.content)
                    full_content += delta.content

        cli2.log.debug('response', content=full_content)

        parsed_ops = Parser().parse(full_content)
        cli2.log.info('operations', json=parsed_ops)

        return parsed_ops


cli = cli2.Command(Engine().run)
