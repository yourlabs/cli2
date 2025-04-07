"""
Prompt management.
"""
import cli2
import functools
import importlib.metadata
from pathlib import Path
import os
import re

import jinja2

from .exception import NotFoundError
from .model import Model


class Prompt:
    """
    Build prompts from text files and context variables.
    """
    if 'PROMPT2_USER_PATH' in os.environ:
        USER_PATH = Path(os.getenv('PROMPT2_USER_PATH'))
    else:
        USER_PATH = Path(os.getenv('HOME')) / '.prompt2/prompts'

    if 'PROMPT2_LOCAL_PATH' in os.environ:
        LOCAL_PATH = Path(os.getenv('PROMPT2_LOCAL_PATH'))
    else:
        LOCAL_PATH = Path(os.getcwd()) / '.prompt2/prompts'

    entry_point = 'prompt2_paths'

    class NotFoundError(NotFoundError):
        pass

    def __init__(self, *prompts, **context):
        self.parts = []
        for prompt in prompts:
            self.read(prompt)
        self.context = context

    @classmethod
    def default_paths(cls, _cli2=None):
        paths = [cls.LOCAL_PATH]
        if cls.USER_PATH != cls.LOCAL_PATH:
            paths.append(cls.USER_PATH)
        if _cli2:
            return [str(p) for p in paths]
        return paths

    @classmethod
    def paths(cls):
        plugins = importlib.metadata.entry_points(
            group=cls.entry_point,
        )
        paths = []
        for plugin in plugins:
            paths += plugin.load()()
        return paths

    @classmethod
    def find(cls, name, paths=None):
        paths = paths or cls.paths()
        for path in paths:
            path = path / f'{name}.txt'
            if path.exists():
                return path
        raise cls.NotFoundError(name, paths)

    @classmethod
    def names(cls, paths=None):
        """ List prompt names """
        paths = paths or cls.default_paths()
        names = set()
        for path in self.paths():
            if not path.exists():
                continue
            for file in path.iterdir():
                names.add(file.name[:-4])
        return list(names)

    def read(self, name):
        """
        Read a prompt text file by name.

        :param name: Name of the prompt, as returned by names
        """
        path = self.find(name)
        with path.open('r') as f:
            content = f.read()
            cli2.log.debug(
                'prompt loaded',
                path=str(path),
                content=content,
            )
            self.parts.append(content)
            self.path = path
            return content

    def render(self):
        # collect all paths from path plugins ...
        plugins = importlib.metadata.entry_points(
            group='prompt2_paths',
        )
        paths = [
            plugin.load()() for plugin in plugins
        ]

        # ... to build a jinja2 environment ...
        env = jinja2.Environment(
            loader=jinja2.FileSystemLoader(
                [str(p) for p in paths],
            ),
            undefined=jinja2.StrictUndefined,
            autoescape=False,
        )

        # ... in which you can hook your plugins
        plugins = importlib.metadata.entry_points(
            group='prompt2_globals',
        )
        for plugin in plugins:
            env.globals[plugin.name] = plugin.load()

        # Render the template with the data
        template = env.from_string('\n'.join(self.parts))
        return template.render(**self.context)

    def messages(self):
        messages = [
            dict(
                role='user',
                content=self.render(),
            ),
        ]
        return messages
