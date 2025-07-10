"""
Prompt management in text files.
"""

import os

from pathlib import Path
import jinja2
import template2
import yaml

from cli2.file import File


class Template2(template2.Template2):
    def __init__(self, plugins, paths=None, **options):
        paths = paths or []
        paths += Prompt.paths()
        super().__init__(plugins, paths, **options)


class Prompt(File):
    extension = 'txt'
    PATH = '.cli2/prompts'
    USER_PATH_ENV = 'PROMPT2_USER_PATH'
    LOCAL_PATH_ENV = 'PROMPT2_LOCAL_PATH'
    paths_ep = os.getenv('PROMPT2_PATHS_EP', 'prompt2_paths')
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
                except:  # noqa
                    continue
        return dict()

    async def render(self):
        return await Template2.factory().render(
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
