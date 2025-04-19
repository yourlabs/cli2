"""
Prompt management in text files.
"""

import cli2

from pathlib import Path
import jinja2
from prompt2 import template2
import yaml

from cli2.file import File


class Prompt(File):
    extension = 'txt'
    PATH = '.cli2/prompts'
    USER_PATH_ENV = 'PROMPT2_USER_PATH'
    LOCAL_PATH_ENV = 'PROMPT2_LOCAL_PATH'
    package_path = Path(__file__).parent / 'templates'

    def __init__(self, path=None, content=None, **context):
        self.context = context
        super().__init__(path, content)

    @property
    def metadata(self):
        env = jinja2.Environment()
        tokens = env.lex(self.content)
        for lineno, token_type, value in tokens:
            if token_type == 'comment':
                try:
                    return yaml.safe_load(value)
                except:
                    continue
        return dict()

    async def render(self):
        return await template2.Template2.factory().render(
            self.content,
            **self.context,
        )

    async def messages(self):
        messages = [
            dict(
                role='user',
                content=await self.render(),
            ),
        ]
        return messages
